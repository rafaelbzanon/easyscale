"""Agregado operação/pesagem (spec 014 §7.1; spec 006).

Nada aqui faz `commit`: quem abriu a transação decide (spec 014 §7).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import Connection, RowMapping, text

from pesagem.dominio.operacao.maquina_estados import (
    AcaoManual,
    EventoOperacao,
    EventoRegistrado,
    MotivoIntervencao,
    Operacao,
    PesoAceito,
    SituacaoOperacao,
    TransicaoRejeitada,
)
from pesagem.dominio.pesagem.calculo_peso import (
    ClassificacaoPesoLiquido,
    TipoOperacao,
)
from pesagem.persistencia.erros import (
    ErroConflitoVersao,
    ErroLeituraJaUsada,
    ErroLiberacaoIndisponivel,
    ErroNaoEncontrado,
    ErroStatusAgendamento,
)


@dataclass(frozen=True)
class LiberacaoCaminhao:
    pesagem_id: int
    etapa: str
    motivo_falha: str | None
    pedido_por: int | None
    motivo: str | None
    pedida_em: datetime | None
    atualizada_em: datetime


@dataclass(frozen=True)
class OperacaoRegistrada:
    pesagem_id: int
    agendamento_id: int
    ponto_controle_id: int
    veiculo_id: int
    situacao_desde: datetime
    aguarda_liberacao_balanca: bool
    operacao: Operacao


_COLUNAS = """
id, agendamento_id, ponto_controle_id, veiculo_id, situacao_desde,
aguarda_liberacao_balanca, tipo_operacao, situacao, versao, situacao_anterior,
motivo_intervencao, peso_inicial_kg, peso_inicial_em, peso_final_kg,
peso_final_em, peso_liquido_kg, classificacao, liberacao_manual
"""
_ABERTAS = "situacao NOT IN ('FINALIZADA', 'CANCELADA')"
# Objeto Pesagem das specs 009 §5.1 e 010 §5.1: placa e tipo do momento da
# criação; nomes do cadastro atual (spec 010 P-1).
_RESUMO = """
SELECT p.id, p.versao, p.situacao, p.situacao_anterior, p.motivo_intervencao,
  p.aguarda_liberacao_balanca, p.liberacao_manual, p.agendamento_id,
  CASE WHEN a.status = 'AGENDADO' AND a.data_prevista < :hoje THEN 'EXPIRADO'
       ELSE a.status END AS agendamento_status,
  p.tipo_operacao, p.placa, m.nome AS motorista_nome,
  t.razao_social AS transportadora_razao_social, pr.descricao AS produto_descricao,
  a.data_prevista, f.hora_inicio AS faixa_hora_inicio, f.hora_fim AS faixa_hora_fim,
  p.peso_inicial_kg, p.peso_inicial_em, p.peso_final_kg, p.peso_final_em,
  p.peso_liquido_kg, p.classificacao, p.criado_em, p.situacao_desde AS atualizado_em
FROM pesagem p
JOIN agendamento a ON a.id = p.agendamento_id
JOIN motorista m ON m.id = p.motorista_id
LEFT JOIN transportadora t ON t.id = a.transportadora_id
JOIN produto pr ON pr.id = a.produto_id
JOIN faixa_horario f ON f.id = a.faixa_horario_id
"""
_FILTROS_HISTORICO = {
    "data_inicio": "(p.criado_em AT TIME ZONE :fuso)::date >= :data_inicio",
    "data_fim": "(p.criado_em AT TIME ZONE :fuso)::date <= :data_fim",
    "aberta": "(p.situacao NOT IN ('FINALIZADA', 'CANCELADA')) = :aberta",
    "situacao": "p.situacao = :situacao",
    "tipo_operacao": "p.tipo_operacao = :tipo_operacao",
    "classificacao": "p.classificacao = :classificacao",
    "liberacao_manual": "p.liberacao_manual = :liberacao_manual",
    "chave_comparacao": "p.chave_comparacao = :chave_comparacao",
    "agendamento_id": "p.agendamento_id = :agendamento_id",
}


class RepositorioPesagem:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def criar_operacao(
        self,
        agendamento_id: int,
        ponto_controle_id: int,
        em: datetime,
        leitura_placa_id: int | None = None,
        liberacao_manual: bool = False,
        responsavel_id: int | None = None,
        motivo: str | None = None,
        *,
        veiculo_id: int,
    ) -> OperacaoRegistrada:
        """Cria a operação e muda o agendamento para `EM_ANDAMENTO` (spec 006 §6.2).

        `veiculo_id` é o da decisão: se o agendamento mudou de veículo nesse meio
        tempo, nada é criado (ErroStatusAgendamento).
        """
        # A condição do UPDATE resolve a corrida com o cancelamento (spec 008 §6.9)
        # e com um PATCH que troque o veículo depois da decisão.
        agendamento = self._conexao.execute(
            text(
                "UPDATE agendamento SET status = 'EM_ANDAMENTO' "
                "WHERE id = :id AND status = 'AGENDADO' AND veiculo_id = :veiculo_id "
                "RETURNING veiculo_id, motorista_id, tipo_operacao"
            ),
            {"id": agendamento_id, "veiculo_id": veiculo_id},
        ).one_or_none()
        if agendamento is None:
            raise ErroStatusAgendamento(str(agendamento_id))
        pesagem_id = self._conexao.execute(
            text(
                "INSERT INTO pesagem (agendamento_id, ponto_controle_id, veiculo_id, "
                "motorista_id, placa, chave_comparacao, tipo_operacao, situacao, "
                "versao, liberacao_manual, situacao_desde) "
                "SELECT :agendamento_id, :ponto_controle_id, v.id, :motorista_id, "
                "v.placa, v.chave_comparacao, :tipo_operacao, "
                "'AGUARDANDO_BALANCA_INICIAL', 1, :liberacao_manual, :em "
                "FROM veiculo v WHERE v.id = :veiculo_id RETURNING id"
            ),
            {
                "agendamento_id": agendamento_id,
                "ponto_controle_id": ponto_controle_id,
                "veiculo_id": agendamento.veiculo_id,
                "motorista_id": agendamento.motorista_id,
                "tipo_operacao": agendamento.tipo_operacao,
                "liberacao_manual": liberacao_manual,
                "em": em,
            },
        ).scalar_one()
        self._ligar_leitura(leitura_placa_id, pesagem_id)
        self._inserir_evento(
            pesagem_id,
            em,
            tipo_registro="TRANSICAO",
            evento="CRIACAO",
            situacao_destino=SituacaoOperacao.AGUARDANDO_BALANCA_INICIAL,
            leitura_placa_id=leitura_placa_id,
            responsavel_id=responsavel_id,
            motivo=motivo,
        )
        return self.obter_operacao(pesagem_id)

    def obter_operacao(self, pesagem_id: int) -> OperacaoRegistrada:
        linha = (
            self._conexao.execute(
                text(f"SELECT {_COLUNAS} FROM pesagem WHERE id = :id"),
                {"id": pesagem_id},
            )
            .mappings()
            .one_or_none()
        )
        if linha is None:
            raise ErroNaoEncontrado(str(pesagem_id))
        return _converter(linha)

    def listar_operacoes_abertas(self) -> list[OperacaoRegistrada]:
        """Retomada e fila da balança, por ordem de chegada (spec 006 §6.3, §7.2)."""
        return self._listar(f"{_ABERTAS} ORDER BY situacao_desde, id", {})

    def buscar_operacao_aberta_por_veiculo(
        self, veiculo_id: int
    ) -> OperacaoRegistrada | None:
        encontradas = self._listar(f"{_ABERTAS} AND veiculo_id = :v", {"v": veiculo_id})
        return encontradas[0] if encontradas else None

    def listar_aguardando_liberacao_balanca(self) -> list[OperacaoRegistrada]:
        return self._listar("aguarda_liberacao_balanca ORDER BY situacao_desde, id", {})

    def buscar_liberacao_caminhao(self, pesagem_id: int) -> LiberacaoCaminhao | None:
        linha = self._conexao.execute(
            text(
                "SELECT pesagem_id, etapa, motivo_falha, pedido_por, motivo, pedida_em, "
                "atualizada_em FROM liberacao_caminhao WHERE pesagem_id = :id"
            ),
            {"id": pesagem_id},
        ).one_or_none()
        return None if linha is None else LiberacaoCaminhao(*linha)

    def listar_liberacoes_pendentes(self) -> list[RowMapping]:
        """Liberações de caminhão com a balança ainda presa (spec 009 §5.5, §5.6)."""
        return list(
            self._conexao.execute(
                text(
                    "SELECT l.pesagem_id, l.etapa, l.motivo_falha, l.pedido_por, "
                    "u.nome AS pedido_por_nome, l.motivo, l.pedida_em, l.atualizada_em "
                    "FROM liberacao_caminhao l JOIN pesagem p ON p.id = l.pesagem_id "
                    "LEFT JOIN usuario u ON u.id = l.pedido_por "
                    "WHERE p.aguarda_liberacao_balanca ORDER BY l.pesagem_id"
                )
            )
            .mappings()
            .all()
        )

    def pedir_liberacao_caminhao(
        self, pesagem_id: int, pedido_por: int, motivo: str, em: datetime
    ) -> None:
        """RN-020: só de `PENDENTE` ou `FALHOU`; outro pedido em curso dá erro."""
        alterada = self._conexao.execute(
            text(
                "UPDATE liberacao_caminhao SET etapa = 'ABRINDO_SAIDA', "
                "motivo_falha = NULL, pedido_por = :u, motivo = :m, pedida_em = :em, "
                "atualizada_em = :em WHERE pesagem_id = :id "
                "AND etapa IN ('PENDENTE', 'FALHOU') RETURNING pesagem_id"
            ),
            {"id": pesagem_id, "u": pedido_por, "m": motivo, "em": em},
        ).one_or_none()
        if alterada is None:
            raise ErroLiberacaoIndisponivel(str(pesagem_id))

    def atualizar_liberacao_caminhao(
        self,
        pesagem_id: int,
        etapa: str,
        em: datetime,
        motivo_falha: str | None = None,
    ) -> None:
        """Em `CONCLUIDA`, a balança deixa de estar presa pela pesagem cancelada."""
        self._conexao.execute(
            text(
                "UPDATE liberacao_caminhao SET etapa = :e, motivo_falha = :f, "
                "atualizada_em = :em WHERE pesagem_id = :id"
            ),
            {"id": pesagem_id, "e": etapa, "f": motivo_falha, "em": em},
        )
        if etapa == "CONCLUIDA":
            self._conexao.execute(
                text(
                    "UPDATE pesagem SET aguarda_liberacao_balanca = FALSE WHERE id = :id"
                ),
                {"id": pesagem_id},
            )

    def gravar_transicao(
        self,
        pesagem_id: int,
        versao_lida: int,
        operacao_nova: Operacao,
        evento: EventoOperacao,
        responsavel_id: int | None,
        hoje: date,
        em: datetime,
        aguarda_liberacao_balanca: bool = False,
        leitura_placa_id: int | None = None,
        imagem_id: int | None = None,
    ) -> None:
        """Grava a operação nova se a `versao` não mudou (spec 006 §7.3).

        `hoje` é a data no fuso do pátio: decide entre `AGENDADO` e `EXPIRADO`
        quando a operação é cancelada (spec 008 §6.6).
        """
        # FOR UPDATE com a versão na condição: quem perdeu a corrida não acha a linha.
        antiga = self._conexao.execute(
            text(
                "SELECT situacao, agendamento_id, peso_final_kg, peso_liquido_kg, "
                "classificacao FROM pesagem WHERE id = :id AND versao = :v FOR UPDATE"
            ),
            {"id": pesagem_id, "v": versao_lida},
        ).one_or_none()
        if antiga is None:
            raise ErroConflitoVersao(str(pesagem_id))
        o = operacao_nova
        self._conexao.execute(
            text(
                "UPDATE pesagem SET situacao = :situacao, "
                "situacao_anterior = :situacao_anterior, "
                "motivo_intervencao = :motivo_intervencao, versao = :v + 1, "
                "peso_inicial_kg = :peso_inicial_kg, peso_inicial_em = :peso_inicial_em, "
                "peso_final_kg = :peso_final_kg, peso_final_em = :peso_final_em, "
                "peso_liquido_kg = :peso_liquido_kg, classificacao = :classificacao, "
                "liberacao_manual = :liberacao_manual, situacao_desde = :em, "
                "aguarda_liberacao_balanca = :aguarda WHERE id = :id"
            ),
            {
                "id": pesagem_id,
                "v": versao_lida,
                "situacao": o.situacao,
                "situacao_anterior": o.situacao_anterior,
                "motivo_intervencao": o.motivo_intervencao,
                "peso_inicial_kg": o.peso_inicial_kg,
                "peso_inicial_em": o.peso_inicial_em,
                "peso_final_kg": o.peso_final_kg,
                "peso_final_em": o.peso_final_em,
                "peso_liquido_kg": o.peso_liquido_kg,
                "classificacao": o.classificacao,
                "liberacao_manual": o.liberacao_manual,
                "em": em,
                "aguarda": aguarda_liberacao_balanca,
            },
        )
        if aguarda_liberacao_balanca:
            self._conexao.execute(
                text(
                    "INSERT INTO liberacao_caminhao (pesagem_id, etapa, atualizada_em) "
                    "VALUES (:id, 'PENDENTE', :em)"
                ),
                {"id": pesagem_id, "em": em},
            )
        self._ligar_leitura(leitura_placa_id, pesagem_id)
        if o.situacao is SituacaoOperacao.FINALIZADA:
            self._mudar_agendamento(antiga.agendamento_id, "'CONCLUIDO'", hoje)
        elif o.situacao is SituacaoOperacao.CANCELADA:
            self._mudar_agendamento(
                antiga.agendamento_id,
                "CASE WHEN data_prevista >= :hoje THEN 'AGENDADO' ELSE 'EXPIRADO' END",
                hoje,
            )
        # O histórico guarda o líquido descartado por TENTAR_NOVAMENTE (spec 006 §6.1).
        if antiga.peso_liquido_kg is not None and o.peso_liquido_kg is None:
            pesos = (antiga.peso_final_kg, antiga.peso_liquido_kg, antiga.classificacao)
        elif isinstance(evento, PesoAceito):
            pesos = (evento.peso_kg, o.peso_liquido_kg, o.classificacao)
        else:
            pesos = (None, None, None)
        self._inserir_evento(
            pesagem_id,
            em,
            tipo_registro="TRANSICAO",
            evento=_nome_evento(evento),
            situacao_origem=antiga.situacao,
            situacao_destino=o.situacao,
            motivo_intervencao=o.motivo_intervencao,
            peso_kg=pesos[0],
            peso_liquido_kg=pesos[1],
            classificacao=pesos[2],
            leitura_placa_id=leitura_placa_id,
            imagem_id=imagem_id,
            **_responsavel(evento, responsavel_id),
        )

    def registrar_evento(
        self,
        pesagem_id: int,
        resultado: TransicaoRejeitada | EventoRegistrado,
        responsavel_id: int | None,
        em: datetime,
        motivo_dispositivo: str | None = None,
        leitura_placa_id: int | None = None,
        imagem_id: int | None = None,
    ) -> None:
        """Rejeições e eventos "registra" (RN-010; spec 006 §6)."""
        if isinstance(resultado, TransicaoRejeitada):
            tipo, situacao = "TRANSICAO_REJEITADA", resultado.situacao
            motivo_rejeicao: str | None = resultado.motivo_rejeicao
        else:
            tipo, situacao = "EVENTO_REGISTRADO", resultado.operacao.situacao
            motivo_rejeicao = None
        evento = resultado.evento
        self._inserir_evento(
            pesagem_id,
            em,
            tipo_registro=tipo,
            evento=_nome_evento(evento),
            situacao_origem=situacao,
            motivo_rejeicao=motivo_rejeicao,
            motivo_dispositivo=motivo_dispositivo,
            peso_kg=evento.peso_kg if isinstance(evento, PesoAceito) else None,
            leitura_placa_id=leitura_placa_id,
            imagem_id=imagem_id,
            **_responsavel(evento, responsavel_id),
        )

    def registrar_comando_cancela(
        self,
        pesagem_id: int,
        cancela: str,
        comando: str,
        resultado: str,
        tentativas: int,
        em: datetime,
        responsavel_id: int | None = None,
        motivo: str | None = None,
    ) -> None:
        """Comando e resultado (spec 004); responsável na liberação da RN-020."""
        situacao = self._conexao.execute(
            text("SELECT situacao FROM pesagem WHERE id = :id"), {"id": pesagem_id}
        ).scalar_one()
        self._inserir_evento(
            pesagem_id,
            em,
            tipo_registro="COMANDO_CANCELA",
            evento=f"{comando}_{cancela}",
            situacao_origem=situacao,
            cancela=cancela,
            comando=comando,
            resultado=resultado,
            tentativas=tentativas,
            responsavel_id=responsavel_id,
            motivo=motivo,
        )

    def listar_historico(
        self,
        filtros: dict[str, Any],
        fuso: str,
        hoje: date,
        pagina: int,
        tamanho_pagina: int,
    ) -> tuple[list[RowMapping], int]:
        """Lista da spec 010 §5.1, do mais recente ao mais antigo."""
        onde = " AND ".join(_FILTROS_HISTORICO[nome] for nome in filtros) or "TRUE"
        parametros = {**filtros, "fuso": fuso, "hoje": hoje}
        linhas = (
            self._conexao.execute(
                text(
                    f"{_RESUMO} WHERE {onde} ORDER BY p.criado_em DESC, p.id DESC "
                    "LIMIT :limite OFFSET :deslocamento"
                ),
                {
                    **parametros,
                    "limite": tamanho_pagina,
                    "deslocamento": (pagina - 1) * tamanho_pagina,
                },
            )
            .mappings()
            .all()
        )
        total = self._conexao.execute(
            text(f"SELECT count(*) FROM pesagem p WHERE {onde}"), parametros
        ).scalar_one()
        return list(linhas), int(total)

    def obter_resumo(self, pesagem_id: int, hoje: date) -> RowMapping:
        linha = (
            self._conexao.execute(
                text(f"{_RESUMO} WHERE p.id = :id"), {"id": pesagem_id, "hoje": hoje}
            )
            .mappings()
            .one_or_none()
        )
        if linha is None:
            raise ErroNaoEncontrado(str(pesagem_id))
        return linha

    def listar_eventos(
        self, pesagem_id: int, pagina: int, tamanho_pagina: int
    ) -> tuple[list[RowMapping], int]:
        """Histórico da operação na ordem em que aconteceu (spec 010 §5.2)."""
        self.obter_operacao(pesagem_id)
        linhas = (
            self._conexao.execute(
                text(
                    "SELECT e.id, e.tipo_registro AS tipo, e.ocorrido_em, e.evento, "
                    "e.situacao_origem, e.situacao_destino, e.motivo_rejeicao, "
                    "e.motivo_intervencao, e.motivo_dispositivo, e.peso_kg, "
                    "e.peso_liquido_kg, e.classificacao, e.cancela, e.comando, "
                    "e.resultado, e.tentativas, e.responsavel_id, "
                    "u.nome AS responsavel_nome, e.motivo, e.imagem_id, "
                    "e.leitura_placa_id FROM evento_operacao e "
                    "LEFT JOIN usuario u ON u.id = e.responsavel_id "
                    "WHERE e.pesagem_id = :p ORDER BY e.ocorrido_em, e.id "
                    "LIMIT :limite OFFSET :deslocamento"
                ),
                {
                    "p": pesagem_id,
                    "limite": tamanho_pagina,
                    "deslocamento": (pagina - 1) * tamanho_pagina,
                },
            )
            .mappings()
            .all()
        )
        total = self._conexao.execute(
            text("SELECT count(*) FROM evento_operacao WHERE pesagem_id = :p"),
            {"p": pesagem_id},
        ).scalar_one()
        return list(linhas), int(total)

    def _listar(
        self, condicao: str, parametros: dict[str, Any]
    ) -> list[OperacaoRegistrada]:
        linhas = self._conexao.execute(
            text(f"SELECT {_COLUNAS} FROM pesagem WHERE {condicao}"), parametros
        ).mappings()
        return [_converter(linha) for linha in linhas]

    def _ligar_leitura(self, leitura_placa_id: int | None, pesagem_id: int) -> None:
        """Uma leitura gera no máximo uma pesagem (spec 009 §6.5): o segundo
        pedido espera o bloqueio da linha e não a acha mais livre."""
        if leitura_placa_id is None:
            return
        ligada = self._conexao.execute(
            text(
                "UPDATE leitura_placa SET pesagem_id = :p WHERE id = :id "
                "AND pesagem_id IS NULL RETURNING id"
            ),
            {"p": pesagem_id, "id": leitura_placa_id},
        ).one_or_none()
        if ligada is None:
            raise ErroLeituraJaUsada(str(leitura_placa_id))

    def _mudar_agendamento(self, agendamento_id: int, status: str, hoje: date) -> None:
        self._conexao.execute(
            text(
                f"UPDATE agendamento SET status = {status} "
                "WHERE id = :id AND status = 'EM_ANDAMENTO'"
            ),
            {"id": agendamento_id, "hoje": hoje},
        )

    def _inserir_evento(
        self,
        pesagem_id: int,
        em: datetime,
        **campos: object,
    ) -> None:
        # Os nomes das colunas vêm só deste módulo, nunca de fora.
        nomes = ", ".join(campos)
        valores = ", ".join(f":{n}" for n in campos)
        self._conexao.execute(
            text(
                f"INSERT INTO evento_operacao (pesagem_id, ocorrido_em, {nomes}) "
                f"VALUES (:pesagem_id, :em, {valores})"
            ),
            {"pesagem_id": pesagem_id, "em": em, **campos},
        )


def _nome_evento(evento: EventoOperacao) -> str:
    if isinstance(evento, PesoAceito):
        return "PESO_ACEITO"
    return evento.tipo.value


def _responsavel(
    evento: EventoOperacao, responsavel_id: int | None
) -> dict[str, object]:
    motivo = evento.motivo if isinstance(evento, AcaoManual) else None
    return {"responsavel_id": responsavel_id, "motivo": motivo}


def _converter(linha: RowMapping) -> OperacaoRegistrada:
    def opcional[T](valor: str | None, tipo: Callable[[str], T]) -> T | None:
        return None if valor is None else tipo(valor)

    return OperacaoRegistrada(
        pesagem_id=linha["id"],
        agendamento_id=linha["agendamento_id"],
        ponto_controle_id=linha["ponto_controle_id"],
        veiculo_id=linha["veiculo_id"],
        situacao_desde=linha["situacao_desde"],
        aguarda_liberacao_balanca=linha["aguarda_liberacao_balanca"],
        operacao=Operacao(
            tipo_operacao=TipoOperacao(linha["tipo_operacao"]),
            situacao=SituacaoOperacao(linha["situacao"]),
            versao=linha["versao"],
            situacao_anterior=opcional(linha["situacao_anterior"], SituacaoOperacao),
            motivo_intervencao=opcional(linha["motivo_intervencao"], MotivoIntervencao),
            peso_inicial_kg=linha["peso_inicial_kg"],
            peso_inicial_em=linha["peso_inicial_em"],
            peso_final_kg=linha["peso_final_kg"],
            peso_final_em=linha["peso_final_em"],
            peso_liquido_kg=linha["peso_liquido_kg"],
            classificacao=opcional(linha["classificacao"], ClassificacaoPesoLiquido),
            liberacao_manual=linha["liberacao_manual"],
        ),
    )
