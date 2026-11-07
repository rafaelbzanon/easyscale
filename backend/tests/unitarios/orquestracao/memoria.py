"""Persistência em memória com a interface da spec 014, para os testes da spec 015.

Imita a transação: tudo sai junto ou nada sai (cópia do estado e restauração em
exceção). As restrições do banco viram os mesmos erros da `persistencia`.
"""

import copy
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date, datetime, time

from pesagem.dominio.operacao.maquina_estados import (
    AcaoManual,
    EventoOperacao,
    EventoRegistrado,
    Operacao,
    SituacaoOperacao,
    TransicaoRejeitada,
)
from pesagem.dominio.pesagem.calculo_peso import TipoOperacao
from pesagem.persistencia.erros import (
    ErroBalancaOcupada,
    ErroConflitoVersao,
    ErroLeituraJaUsada,
    ErroLiberacaoIndisponivel,
    ErroNaoEncontrado,
    ErroOperacaoAberta,
    ErroPersistencia,
    ErroStatusAgendamento,
)
from pesagem.persistencia.repositorios.leitura_placa import (
    LeituraPlacaRegistrada,
    NovaLeituraPlaca,
)
from pesagem.persistencia.repositorios.pesagem import (
    LiberacaoCaminhao,
    OperacaoRegistrada,
)
from pesagem.persistencia.repositorios.veiculo import (
    AgendamentoAberto,
    OperacaoAbertaDoVeiculo,
    SituacaoVeiculo,
)

S = SituacaoOperacao
OCUPAM = frozenset(S) - {
    S.AGUARDANDO_BALANCA_INICIAL,
    S.AGUARDANDO_BALANCA_FINAL,
    S.EM_CARGA_DESCARGA,
    S.AGUARDANDO_INTERVENCAO,
    S.FINALIZADA,
    S.CANCELADA,
}
PONTO_CONTROLE_ID = 1


@dataclass
class Veiculo:
    chave_comparacao: str
    ativo: bool = True


@dataclass
class Agendamento:
    veiculo_id: int
    data_prevista: date
    tipo_operacao: TipoOperacao = TipoOperacao.CARGA
    faixa_hora_inicio: time = time(8, 0)
    motorista_ativo: bool = True
    status: str = "AGENDADO"


@dataclass(frozen=True)
class RegistroAuditoria:
    pesagem_id: int
    tipo: str
    evento: str
    motivo: str | None


@dataclass(frozen=True)
class ComandoRegistrado:
    pesagem_id: int
    cancela: str
    comando: str
    resultado: str
    responsavel_id: int | None


@dataclass
class Estado:
    veiculos: dict[int, Veiculo]
    agendamentos: dict[int, Agendamento]
    pesagens: dict[int, OperacaoRegistrada]
    leituras: dict[int, NovaLeituraPlaca]
    imagens: dict[int, bytes]
    liberacoes: dict[int, LiberacaoCaminhao]
    auditoria: list[RegistroAuditoria]
    comandos: list[ComandoRegistrado]


def _ocupa(operacao: Operacao) -> bool:
    if operacao.situacao is S.AGUARDANDO_INTERVENCAO:
        return operacao.situacao_anterior in OCUPAM
    return operacao.situacao in OCUPAM


class BancoMemoria:
    def __init__(self) -> None:
        self.estado = Estado({}, {}, {}, {}, {}, {}, [], [])
        # Nome do método que deve falhar uma vez (CA-013).
        self.falhar_em: str | None = None

    @contextmanager
    def transacao(self) -> Iterator["TransacaoMemoria"]:
        copia = copy.deepcopy(self.estado)
        try:
            yield TransacaoMemoria(self)
        except BaseException:
            self.estado = copia
            raise

    def _falhar_se_pedido(self, metodo: str) -> None:
        if self.falhar_em == metodo:
            self.falhar_em = None
            raise ErroPersistencia("falha simulada")

    def operacoes_abertas(self) -> list[OperacaoRegistrada]:
        abertas = [
            p
            for p in self.estado.pesagens.values()
            if p.operacao.situacao not in (S.FINALIZADA, S.CANCELADA)
        ]
        return sorted(abertas, key=lambda p: (p.situacao_desde, p.pesagem_id))

    def situacao_veiculo(self, veiculo_id: int) -> SituacaoVeiculo:
        veiculo = self.estado.veiculos[veiculo_id]
        aberta = next(
            (p for p in self.operacoes_abertas() if p.veiculo_id == veiculo_id), None
        )
        return SituacaoVeiculo(
            veiculo_id,
            veiculo.ativo,
            None
            if aberta is None
            else OperacaoAbertaDoVeiculo(aberta.pesagem_id, aberta.operacao.situacao),
            tuple(
                AgendamentoAberto(
                    id_,
                    a.status,
                    a.data_prevista,
                    a.tipo_operacao,
                    a.faixa_hora_inicio,
                    a.motorista_ativo,
                )
                for id_, a in self.estado.agendamentos.items()
                if a.veiculo_id == veiculo_id
                and a.status in ("AGENDADO", "EM_ANDAMENTO")
            ),
        )


class TransacaoMemoria:
    def __init__(self, banco: BancoMemoria) -> None:
        self.pesagens = PesagensMemoria(banco)
        self.veiculos = VeiculosMemoria(banco)
        self.leituras_placa = LeiturasMemoria(banco)
        self.imagens = ImagensMemoria(banco)
        self.pontos_controle = PontosControleMemoria()


class PontosControleMemoria:
    def obter_unico(self) -> int:
        return PONTO_CONTROLE_ID


class VeiculosMemoria:
    def __init__(self, banco: BancoMemoria) -> None:
        self._banco = banco

    def buscar_situacao_por_chave(
        self, chave_comparacao: str
    ) -> SituacaoVeiculo | None:
        for veiculo_id, veiculo in self._banco.estado.veiculos.items():
            if veiculo.chave_comparacao == chave_comparacao:
                return self._banco.situacao_veiculo(veiculo_id)
        return None

    def buscar_situacao_por_agendamento(
        self, agendamento_id: int
    ) -> SituacaoVeiculo | None:
        agendamento = self._banco.estado.agendamentos.get(agendamento_id)
        return (
            None
            if agendamento is None
            else self._banco.situacao_veiculo(agendamento.veiculo_id)
        )


class LeiturasMemoria:
    def __init__(self, banco: BancoMemoria) -> None:
        self._banco = banco

    def registrar(self, leitura: NovaLeituraPlaca) -> int:
        leituras = self._banco.estado.leituras
        leitura_id = len(leituras) + 1
        leituras[leitura_id] = leitura
        return leitura_id

    def buscar(self, leitura_placa_id: int) -> LeituraPlacaRegistrada | None:
        leitura = self._banco.estado.leituras.get(leitura_placa_id)
        if leitura is None:
            return None
        return LeituraPlacaRegistrada(
            leitura_placa_id,
            leitura.decisao,
            leitura.pesagem_id,
            leitura.agendamento_id,
        )


class ImagensMemoria:
    def __init__(self, banco: BancoMemoria) -> None:
        self._banco = banco

    def salvar(
        self,
        conteudo: bytes,
        origem: str,
        capturada_em: datetime,
        roi: tuple[int, int, int, int] | None = None,
    ) -> int:
        imagens = self._banco.estado.imagens
        imagem_id = len(imagens) + 1
        imagens[imagem_id] = conteudo
        return imagem_id


class PesagensMemoria:
    def __init__(self, banco: BancoMemoria) -> None:
        self._banco = banco
        self._estado = banco.estado

    def _ligar_leitura(self, leitura_placa_id: int | None, pesagem_id: int) -> None:
        if leitura_placa_id is None:
            return
        leitura = self._estado.leituras[leitura_placa_id]
        # Como na spec 014: a leitura só é ligada a uma pesagem uma vez.
        if leitura.pesagem_id is not None:
            raise ErroLeituraJaUsada(str(leitura_placa_id))
        self._estado.leituras[leitura_placa_id] = replace(
            leitura, pesagem_id=pesagem_id
        )

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
        self._banco._falhar_se_pedido("criar_operacao")
        agendamento = self._estado.agendamentos.get(agendamento_id)
        # Spec 014: o agendamento precisa ser do veículo da decisão.
        if (
            agendamento is None
            or agendamento.status != "AGENDADO"
            or agendamento.veiculo_id != veiculo_id
        ):
            raise ErroStatusAgendamento(str(agendamento_id))
        if any(
            p.veiculo_id == agendamento.veiculo_id
            for p in self._banco.operacoes_abertas()
        ):
            raise ErroOperacaoAberta(str(agendamento.veiculo_id))
        agendamento.status = "EM_ANDAMENTO"
        pesagem_id = len(self._estado.pesagens) + 1
        registrada = OperacaoRegistrada(
            pesagem_id,
            agendamento_id,
            ponto_controle_id,
            agendamento.veiculo_id,
            em,
            False,
            Operacao(agendamento.tipo_operacao, liberacao_manual=liberacao_manual),
        )
        self._estado.pesagens[pesagem_id] = registrada
        self._ligar_leitura(leitura_placa_id, pesagem_id)
        return registrada

    def obter_operacao(self, pesagem_id: int) -> OperacaoRegistrada:
        try:
            return self._estado.pesagens[pesagem_id]
        except KeyError:
            raise ErroNaoEncontrado(str(pesagem_id)) from None

    def listar_operacoes_abertas(self) -> list[OperacaoRegistrada]:
        return self._banco.operacoes_abertas()

    def listar_aguardando_liberacao_balanca(self) -> list[OperacaoRegistrada]:
        return [
            p for p in self._estado.pesagens.values() if p.aguarda_liberacao_balanca
        ]

    def buscar_liberacao_caminhao(self, pesagem_id: int) -> LiberacaoCaminhao | None:
        return self._estado.liberacoes.get(pesagem_id)

    def pedir_liberacao_caminhao(
        self, pesagem_id: int, pedido_por: int, motivo: str, em: datetime
    ) -> None:
        liberacao = self._estado.liberacoes.get(pesagem_id)
        if liberacao is None or liberacao.etapa not in ("PENDENTE", "FALHOU"):
            raise ErroLiberacaoIndisponivel(str(pesagem_id))
        self._estado.liberacoes[pesagem_id] = LiberacaoCaminhao(
            pesagem_id, "ABRINDO_SAIDA", None, pedido_por, motivo, em, em
        )

    def atualizar_liberacao_caminhao(
        self, pesagem_id: int, etapa: str, em: datetime, motivo_falha: str | None = None
    ) -> None:
        self._banco._falhar_se_pedido("atualizar_liberacao_caminhao")
        atual = self._estado.liberacoes[pesagem_id]
        self._estado.liberacoes[pesagem_id] = replace(
            atual, etapa=etapa, motivo_falha=motivo_falha, atualizada_em=em
        )
        if etapa == "CONCLUIDA":
            pesagem = self._estado.pesagens[pesagem_id]
            self._estado.pesagens[pesagem_id] = replace(
                pesagem, aguarda_liberacao_balanca=False
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
        self._banco._falhar_se_pedido("gravar_transicao")
        antiga = self.obter_operacao(pesagem_id)
        if antiga.operacao.versao != versao_lida:
            raise ErroConflitoVersao(str(pesagem_id))
        if operacao_nova.situacao in (S.AUTORIZADA, S.RETORNO_AUTORIZADO) and any(
            p.pesagem_id != pesagem_id and _ocupa(p.operacao)
            for p in self._banco.operacoes_abertas()
        ):
            raise ErroBalancaOcupada(str(pesagem_id))
        self._estado.pesagens[pesagem_id] = replace(
            antiga,
            operacao=operacao_nova,
            situacao_desde=em,
            aguarda_liberacao_balanca=antiga.aguarda_liberacao_balanca
            or aguarda_liberacao_balanca,
        )
        if aguarda_liberacao_balanca:
            self._estado.liberacoes[pesagem_id] = LiberacaoCaminhao(
                pesagem_id, "PENDENTE", None, None, None, None, em
            )
        self._ligar_leitura(leitura_placa_id, pesagem_id)
        agendamento = self._estado.agendamentos[antiga.agendamento_id]
        if operacao_nova.situacao is S.FINALIZADA:
            agendamento.status = "CONCLUIDO"
        elif operacao_nova.situacao is S.CANCELADA:
            agendamento.status = (
                "AGENDADO" if agendamento.data_prevista >= hoje else "EXPIRADO"
            )
        motivo = evento.motivo if isinstance(evento, AcaoManual) else None
        self._estado.auditoria.append(
            RegistroAuditoria(pesagem_id, "TRANSICAO", _nome(evento), motivo)
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
        tipo = (
            "TRANSICAO_REJEITADA"
            if isinstance(resultado, TransicaoRejeitada)
            else "EVENTO_REGISTRADO"
        )
        self._estado.auditoria.append(
            RegistroAuditoria(
                pesagem_id, tipo, _nome(resultado.evento), motivo_dispositivo
            )
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
        self._banco._falhar_se_pedido("registrar_comando_cancela")
        self._estado.comandos.append(
            ComandoRegistrado(pesagem_id, cancela, comando, resultado, responsavel_id)
        )


def _nome(evento: EventoOperacao) -> str:
    return getattr(evento, "tipo", "PESO_ACEITO")
