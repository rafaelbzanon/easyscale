"""Agregado agendamento: só o que depende de concorrência (spec 014 §7.2, §6).

As referências e os campos são validados pela API antes (spec 008 §6.8).
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import Connection, RowMapping, text

from pesagem.persistencia.erros import (
    ErroCodigoNotaNaoPermitido,
    ErroFaixaEncerrada,
    ErroFaixaSemVaga,
    ErroNaoEncontrado,
    ErroSemFaixaDisponivel,
    ErroStatusAgendamento,
)


@dataclass(frozen=True)
class NovoAgendamento:
    veiculo_id: int
    motorista_id: int
    transportadora_id: int | None
    produto_id: int
    tipo_operacao: str
    data_prevista: date
    faixa_horario_id: int | None
    codigo_nota: str | None
    observacao: str | None
    origem: str
    criado_por: int | None


@dataclass(frozen=True)
class AgendamentoCriado:
    agendamento_id: int
    faixa_horario_id: int


# Status como a API mostra: `AGENDADO` de dia passado é `EXPIRADO` (spec 008 §6.6),
# sem depender de tarefa agendada.
_STATUS = (
    "CASE WHEN a.status = 'AGENDADO' AND a.data_prevista < :hoje THEN 'EXPIRADO' "
    "ELSE a.status END"
)
_LEITURA = f"""
SELECT a.id, a.veiculo_id, a.motorista_id, a.transportadora_id, a.produto_id,
  a.tipo_operacao, a.data_prevista, a.faixa_horario_id, a.codigo_nota, a.observacao,
  {_STATUS} AS status, a.origem, a.criado_por, a.criado_em, a.cancelado_por,
  a.cancelado_em, a.motivo_cancelamento, v.placa, m.nome AS motorista_nome,
  t.razao_social AS transportadora_razao_social, p.descricao AS produto_descricao,
  f.hora_inicio AS faixa_hora_inicio, f.hora_fim AS faixa_hora_fim
FROM agendamento a
JOIN veiculo v ON v.id = a.veiculo_id
JOIN motorista m ON m.id = a.motorista_id
LEFT JOIN transportadora t ON t.id = a.transportadora_id
JOIN produto p ON p.id = a.produto_id
JOIN faixa_horario f ON f.id = a.faixa_horario_id
"""
_ALTERAVEIS = frozenset(
    {
        "veiculo_id",
        "motorista_id",
        "transportadora_id",
        "produto_id",
        "tipo_operacao",
        "data_prevista",
        "faixa_horario_id",
        "codigo_nota",
        "observacao",
    }
)


class RepositorioAgendamento:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def criar_agendamento(
        self, dados: NovoAgendamento, hoje: date, hora_atual: time
    ) -> AgendamentoCriado:
        """`hoje` e `hora_atual` no fuso do pátio (spec 008 §6.1)."""
        # Expira antes de testar a unicidade por veículo (spec 008 §9, RN-023).
        self._conexao.execute(
            text(
                "UPDATE agendamento SET status = 'EXPIRADO' WHERE veiculo_id = :v "
                "AND status = 'AGENDADO' AND data_prevista < :hoje"
            ),
            {"v": dados.veiculo_id, "hoje": hoje},
        )
        # FOR UPDATE em ordem fixa: pedidos pela mesma faixa entram em fila, sem impasse.
        condicao = "id = :f" if dados.faixa_horario_id is not None else "ativo"
        faixas = self._conexao.execute(
            text(
                f"SELECT id, hora_fim, capacidade FROM faixa_horario WHERE {condicao} "
                "ORDER BY hora_inicio, id FOR UPDATE"
            ),
            {"f": dados.faixa_horario_id},
        ).all()
        escolhida: int | None = None
        for faixa in faixas:
            encerrada = dados.data_prevista == hoje and hora_atual >= faixa.hora_fim
            ocupadas = self._ocupadas(faixa.id, dados.data_prevista)
            if dados.faixa_horario_id is not None:
                if encerrada:
                    raise ErroFaixaEncerrada(str(faixa.id))
                if ocupadas >= faixa.capacidade:
                    raise ErroFaixaSemVaga(str(faixa.id))
            if not encerrada and ocupadas < faixa.capacidade:
                escolhida = faixa.id
                break
        if escolhida is None:
            # Faixa pedida inexistente cai aqui também; a API já validou o id.
            raise ErroSemFaixaDisponivel(str(dados.data_prevista))
        agendamento_id = self._conexao.execute(
            text(
                "INSERT INTO agendamento (veiculo_id, motorista_id, transportadora_id, "
                "produto_id, tipo_operacao, data_prevista, faixa_horario_id, "
                "codigo_nota, observacao, origem, criado_por) VALUES (:veiculo_id, "
                ":motorista_id, :transportadora_id, :produto_id, :tipo_operacao, "
                ":data_prevista, :faixa, :codigo_nota, :observacao, :origem, "
                ":criado_por) RETURNING id"
            ),
            {**dados.__dict__, "faixa": escolhida},
        ).scalar_one()
        return AgendamentoCriado(agendamento_id, escolhida)

    def _ocupadas(self, faixa_id: int, data: date, exceto: int | None = None) -> int:
        """Só o cancelamento libera a vaga (spec 008 §6.2)."""
        return int(
            self._conexao.execute(
                text(
                    "SELECT count(*) FROM agendamento WHERE faixa_horario_id = :f "
                    "AND data_prevista = :d AND id IS DISTINCT FROM :exceto "
                    "AND status IN ('AGENDADO', 'EM_ANDAMENTO', 'CONCLUIDO')"
                ),
                {"f": faixa_id, "d": data, "exceto": exceto},
            ).scalar_one()
        )

    def obter_agendamento(self, agendamento_id: int, hoje: date) -> RowMapping:
        linha = (
            self._conexao.execute(
                text(f"{_LEITURA} WHERE a.id = :id"),
                {"id": agendamento_id, "hoje": hoje},
            )
            .mappings()
            .one_or_none()
        )
        if linha is None:
            raise ErroNaoEncontrado(str(agendamento_id))
        return linha

    def listar_agendamentos(
        self,
        filtros: dict[str, Any],
        hoje: date,
        pagina: int,
        tamanho_pagina: int,
    ) -> tuple[list[RowMapping], int]:
        """Filtros da spec 008 §5.1; `status` segue o mesmo cálculo da resposta."""
        condicoes = {
            "data_inicio": "a.data_prevista >= :data_inicio",
            "data_fim": "a.data_prevista <= :data_fim",
            "status": f"{_STATUS} = :status",
            "tipo_operacao": "a.tipo_operacao = :tipo_operacao",
            "origem": "a.origem = :origem",
            "chave_comparacao": "v.chave_comparacao = :chave_comparacao",
        }
        onde = " AND ".join(condicoes[nome] for nome in filtros) or "TRUE"
        parametros = {**filtros, "hoje": hoje}
        linhas = (
            self._conexao.execute(
                text(
                    f"{_LEITURA} WHERE {onde} ORDER BY a.data_prevista, f.hora_inicio, a.id "
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
            text(
                "SELECT count(*) FROM agendamento a JOIN veiculo v ON v.id = a.veiculo_id "
                f"JOIN faixa_horario f ON f.id = a.faixa_horario_id WHERE {onde}"
            ),
            parametros,
        ).scalar_one()
        return list(linhas), int(total)

    def alterar_agendamento(
        self,
        agendamento_id: int,
        campos: dict[str, Any],
        hoje: date,
        hora_atual: time,
        responsavel_id: int,
        em: datetime,
    ) -> None:
        """Só `AGENDADO` ainda no dia (spec 008 §6.5); refaz as regras do que mudou."""
        assert set(campos) <= _ALTERAVEIS
        atual = (
            self._conexao.execute(
                text("SELECT * FROM agendamento WHERE id = :id FOR UPDATE"),
                {"id": agendamento_id},
            )
            .mappings()
            .one_or_none()
        )
        if atual is None:
            raise ErroNaoEncontrado(str(agendamento_id))
        if atual["status"] != "AGENDADO" or atual["data_prevista"] < hoje:
            raise ErroStatusAgendamento(str(agendamento_id))
        novo = {**atual, **campos}
        if novo["tipo_operacao"] == "CARGA" and novo["codigo_nota"] is not None:
            raise ErroCodigoNotaNaoPermitido(str(agendamento_id))
        if {"data_prevista", "faixa_horario_id"} & set(campos):
            faixa = self._conexao.execute(
                text(
                    "SELECT hora_fim, capacidade FROM faixa_horario WHERE id = :f FOR UPDATE"
                ),
                {"f": novo["faixa_horario_id"]},
            ).one()
            if novo["data_prevista"] == hoje and hora_atual >= faixa.hora_fim:
                raise ErroFaixaEncerrada(str(novo["faixa_horario_id"]))
            ocupadas = self._ocupadas(
                novo["faixa_horario_id"], novo["data_prevista"], agendamento_id
            )
            if ocupadas >= faixa.capacidade:
                raise ErroFaixaSemVaga(str(novo["faixa_horario_id"]))
        if "veiculo_id" in campos:
            self._conexao.execute(
                text(
                    "UPDATE agendamento SET status = 'EXPIRADO' WHERE veiculo_id = :v "
                    "AND status = 'AGENDADO' AND data_prevista < :hoje"
                ),
                {"v": campos["veiculo_id"], "hoje": hoje},
            )
        if campos:
            atribuicoes = ", ".join(f"{nome} = :{nome}" for nome in campos)
            self._conexao.execute(
                text(f"UPDATE agendamento SET {atribuicoes} WHERE id = :id"),
                {**campos, "id": agendamento_id},
            )
        self._conexao.execute(
            text(
                "INSERT INTO registro_auditoria (tipo, responsavel_id, agendamento_id, "
                "ocorrido_em) VALUES ('AGENDAMENTO_EDITADO', :r, :id, :em)"
            ),
            {"r": responsavel_id, "id": agendamento_id, "em": em},
        )

    def cancelar_agendamento(
        self,
        agendamento_id: int,
        responsavel_id: int,
        motivo: str,
        hoje: date,
        em: datetime,
    ) -> None:
        """Só de `AGENDADO` ainda válido (spec 008 §6.5); a corrida com a entrada
        fica resolvida pela condição do UPDATE (§6.9)."""
        alterado = self._conexao.execute(
            text(
                "UPDATE agendamento SET status = 'CANCELADO', cancelado_por = :r, "
                "cancelado_em = :em, motivo_cancelamento = :m WHERE id = :id "
                "AND status = 'AGENDADO' AND data_prevista >= :hoje RETURNING id"
            ),
            {
                "id": agendamento_id,
                "r": responsavel_id,
                "m": motivo,
                "em": em,
                "hoje": hoje,
            },
        ).one_or_none()
        if alterado is None:
            raise ErroStatusAgendamento(str(agendamento_id))
        self._conexao.execute(
            text(
                "INSERT INTO registro_auditoria (tipo, responsavel_id, agendamento_id, "
                "ocorrido_em) VALUES ('AGENDAMENTO_CANCELADO', :r, :id, :em)"
            ),
            {"r": responsavel_id, "id": agendamento_id, "em": em},
        )
