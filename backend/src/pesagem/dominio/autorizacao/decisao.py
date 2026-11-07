"""Decisão de autorização da entrada e da volta (spec 015 §5.1).

Regra pura: recebe a leitura selecionada, a fotografia do cadastro e o
instante com o fuso do pátio. Na dúvida, não autoriza (RNF-009). A volta
(RN-018) não reaplica a RN-014 (spec 006 §14).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
from enum import StrEnum

from pesagem.dominio.operacao.maquina_estados import SituacaoOperacao
from pesagem.dominio.pesagem.calculo_peso import TipoOperacao
from pesagem.dominio.placa.selecao import PlacaSelecionada, RejeicaoLeituraPlaca

STATUS_AGENDADO = "AGENDADO"


class MotivoNaoAutorizacao(StrEnum):
    FALHA_IMAGEM = "FALHA_IMAGEM"
    FALHA_LEITOR = "FALHA_LEITOR"
    SEM_CANDIDATO = "SEM_CANDIDATO"
    PLACA_INVALIDA = "PLACA_INVALIDA"
    AMBIGUA = "AMBIGUA"
    CONFIANCA_BAIXA = "CONFIANCA_BAIXA"
    VEICULO_NAO_CADASTRADO = "VEICULO_NAO_CADASTRADO"
    VEICULO_INATIVO = "VEICULO_INATIVO"
    OPERACAO_JA_ABERTA = "OPERACAO_JA_ABERTA"
    SEM_AGENDAMENTO = "SEM_AGENDAMENTO"
    AGENDAMENTO_AMBIGUO = "AGENDAMENTO_AMBIGUO"
    MOTORISTA_INATIVO = "MOTORISTA_INATIVO"
    ANTES_DA_FAIXA = "ANTES_DA_FAIXA"


class FalhaIdentificacao(StrEnum):
    FALHA_IMAGEM = "FALHA_IMAGEM"
    FALHA_LEITOR = "FALHA_LEITOR"


# §6.7: só a identificação e o horário podem ser substituídos pelo administrador.
MOTIVOS_SUBSTITUIVEIS = frozenset(
    {
        MotivoNaoAutorizacao.FALHA_IMAGEM,
        MotivoNaoAutorizacao.FALHA_LEITOR,
        MotivoNaoAutorizacao.SEM_CANDIDATO,
        MotivoNaoAutorizacao.PLACA_INVALIDA,
        MotivoNaoAutorizacao.AMBIGUA,
        MotivoNaoAutorizacao.CONFIANCA_BAIXA,
        MotivoNaoAutorizacao.ANTES_DA_FAIXA,
    }
)


@dataclass(frozen=True)
class AgendamentoCandidato:
    id: int
    status: str
    data_prevista: date
    tipo_operacao: TipoOperacao
    faixa_hora_inicio: time
    motorista_ativo: bool


@dataclass(frozen=True)
class OperacaoAberta:
    pesagem_id: int
    situacao: SituacaoOperacao


@dataclass(frozen=True)
class SituacaoVeiculo:
    veiculo_id: int
    ativo: bool
    operacao_aberta: OperacaoAberta | None
    agendamentos: tuple[AgendamentoCandidato, ...]


@dataclass(frozen=True)
class EntradaAutorizada:
    agendamento_id: int
    veiculo_id: int
    tipo_operacao: TipoOperacao


@dataclass(frozen=True)
class RetornoAceito:
    pesagem_id: int


@dataclass(frozen=True)
class EntradaNaoAutorizada:
    motivo: MotivoNaoAutorizacao


type ResultadoAutorizacao = EntradaAutorizada | RetornoAceito | EntradaNaoAutorizada
type LeituraIdentificacao = PlacaSelecionada | RejeicaoLeituraPlaca | FalhaIdentificacao


def decidir_autorizacao(
    leitura: LeituraIdentificacao,
    situacao_veiculo: SituacaoVeiculo | None,
    agora: datetime,
    fuso_patio: tzinfo,
) -> ResultadoAutorizacao:
    if isinstance(leitura, FalhaIdentificacao | RejeicaoLeituraPlaca):
        motivo = leitura if isinstance(leitura, FalhaIdentificacao) else leitura.motivo
        return EntradaNaoAutorizada(MotivoNaoAutorizacao[motivo.name])
    if situacao_veiculo is None:
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.VEICULO_NAO_CADASTRADO)
    return _decidir_veiculo(situacao_veiculo, agora, fuso_patio, ignorar_faixa=False)


def decidir_liberacao_manual(
    situacao_veiculo: SituacaoVeiculo | None,
    agendamento_id: int,
    agora: datetime,
    fuso_patio: tzinfo,
) -> EntradaAutorizada | EntradaNaoAutorizada:
    """§6.7: ignora a identificação e a faixa; o resto continua obrigatório."""
    if situacao_veiculo is None:
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.VEICULO_NAO_CADASTRADO)
    resultado = _decidir_veiculo(
        situacao_veiculo, agora, fuso_patio, ignorar_faixa=True
    )
    if isinstance(resultado, RetornoAceito):
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.OPERACAO_JA_ABERTA)
    if (
        isinstance(resultado, EntradaAutorizada)
        and resultado.agendamento_id != agendamento_id
    ):
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.SEM_AGENDAMENTO)
    return resultado


def _decidir_veiculo(
    veiculo: SituacaoVeiculo, agora: datetime, fuso_patio: tzinfo, ignorar_faixa: bool
) -> ResultadoAutorizacao:
    if not veiculo.ativo:
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.VEICULO_INATIVO)
    if veiculo.operacao_aberta is not None:
        if veiculo.operacao_aberta.situacao is SituacaoOperacao.EM_CARGA_DESCARGA:
            return RetornoAceito(veiculo.operacao_aberta.pesagem_id)
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.OPERACAO_JA_ABERTA)

    agora_patio = agora.astimezone(fuso_patio)
    hoje = [
        agendamento
        for agendamento in veiculo.agendamentos
        if agendamento.status == STATUS_AGENDADO
        and agendamento.data_prevista == agora_patio.date()
    ]
    if not hoje:
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.SEM_AGENDAMENTO)
    if len(hoje) > 1:
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.AGENDAMENTO_AMBIGUO)
    (agendamento,) = hoje
    if not agendamento.motorista_ativo:
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.MOTORISTA_INATIVO)
    if not ignorar_faixa and agora_patio.time() < agendamento.faixa_hora_inicio:
        return EntradaNaoAutorizada(MotivoNaoAutorizacao.ANTES_DA_FAIXA)
    return EntradaAutorizada(
        agendamento.id, veiculo.veiculo_id, agendamento.tipo_operacao
    )
