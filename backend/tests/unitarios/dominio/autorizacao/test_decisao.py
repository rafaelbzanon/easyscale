"""Decisão de autorização (spec 015 §5.1; CA-001 a CA-004, CA-020)."""

from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest

from pesagem.dominio.autorizacao.decisao import (
    MOTIVOS_SUBSTITUIVEIS,
    AgendamentoCandidato,
    EntradaAutorizada,
    EntradaNaoAutorizada,
    FalhaIdentificacao,
    MotivoNaoAutorizacao,
    OperacaoAberta,
    RetornoAceito,
    SituacaoVeiculo,
    decidir_autorizacao,
    decidir_liberacao_manual,
)
from pesagem.dominio.operacao.maquina_estados import SituacaoOperacao
from pesagem.dominio.pesagem.calculo_peso import TipoOperacao
from pesagem.dominio.placa.normalizacao import PlacaNormalizada, normalizar_placa
from pesagem.dominio.placa.selecao import (
    MotivoRejeicaoLeituraPlaca,
    PlacaSelecionada,
    RejeicaoLeituraPlaca,
)

M = MotivoNaoAutorizacao
FUSO = timezone(timedelta(hours=-3))
# 2026-11-07 09:00 no pátio.
AGORA = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
HOJE = date(2026, 11, 7)


def placa() -> PlacaSelecionada:
    normalizada = normalizar_placa("ABC1234")
    assert isinstance(normalizada, PlacaNormalizada)
    return PlacaSelecionada(normalizada, Decimal("0.9"), 0)


def agendamento(**mudancas: object) -> AgendamentoCandidato:
    base: dict[str, object] = {
        "id": 10,
        "status": "AGENDADO",
        "data_prevista": HOJE,
        "tipo_operacao": TipoOperacao.CARGA,
        "faixa_hora_inicio": time(8, 0),
        "motorista_ativo": True,
    }
    base.update(mudancas)
    return AgendamentoCandidato(**base)  # type: ignore[arg-type]


def veiculo(*agendamentos: AgendamentoCandidato, **mudancas: object) -> SituacaoVeiculo:
    base: dict[str, object] = {"veiculo_id": 5, "ativo": True, "operacao_aberta": None}
    base.update(mudancas)
    return SituacaoVeiculo(agendamentos=agendamentos, **base)  # type: ignore[arg-type]


def decidir(leitura: object, situacao: SituacaoVeiculo | None) -> object:
    return decidir_autorizacao(leitura, situacao, AGORA, FUSO)  # type: ignore[arg-type]


def test_autoriza_com_agendamento_unico_de_hoje_dentro_da_faixa() -> None:
    """CA-001."""
    resultado = decidir(placa(), veiculo(agendamento()))
    assert resultado == EntradaAutorizada(10, 5, TipoOperacao.CARGA)


def test_autoriza_depois_do_fim_da_faixa_no_mesmo_dia() -> None:
    """CA-001 (RN-014: depois da faixa, no mesmo dia, pode autorizar)."""
    resultado = decidir(placa(), veiculo(agendamento(faixa_hora_inicio=time(6, 0))))
    assert isinstance(resultado, EntradaAutorizada)


@pytest.mark.parametrize(
    ("leitura", "situacao", "motivo"),
    [
        (FalhaIdentificacao.FALHA_IMAGEM, None, M.FALHA_IMAGEM),
        (FalhaIdentificacao.FALHA_LEITOR, None, M.FALHA_LEITOR),
        *[
            (RejeicaoLeituraPlaca(motivo), veiculo(agendamento()), M(motivo.value))
            for motivo in MotivoRejeicaoLeituraPlaca
        ],
        (placa(), None, M.VEICULO_NAO_CADASTRADO),
        (placa(), veiculo(agendamento(), ativo=False), M.VEICULO_INATIVO),
        (
            placa(),
            veiculo(
                agendamento(),
                operacao_aberta=OperacaoAberta(3, SituacaoOperacao.POSICIONADA_INICIAL),
            ),
            M.OPERACAO_JA_ABERTA,
        ),
        (placa(), veiculo(), M.SEM_AGENDAMENTO),
        (placa(), veiculo(agendamento(status="EM_ANDAMENTO")), M.SEM_AGENDAMENTO),
        (
            placa(),
            veiculo(agendamento(data_prevista=HOJE - timedelta(days=1))),
            M.SEM_AGENDAMENTO,
        ),
        (
            placa(),
            veiculo(agendamento(data_prevista=HOJE + timedelta(days=1))),
            M.SEM_AGENDAMENTO,
        ),
        (placa(), veiculo(agendamento(), agendamento(id=11)), M.AGENDAMENTO_AMBIGUO),
        (placa(), veiculo(agendamento(motorista_ativo=False)), M.MOTORISTA_INATIVO),
        (placa(), veiculo(agendamento(faixa_hora_inicio=time(9, 1))), M.ANTES_DA_FAIXA),
    ],
)
def test_cada_motivo_de_nao_autorizacao(
    leitura: object, situacao: SituacaoVeiculo | None, motivo: MotivoNaoAutorizacao
) -> None:
    """CA-002, CA-003."""
    assert decidir(leitura, situacao) == EntradaNaoAutorizada(motivo)


def test_precedencia_dos_motivos() -> None:
    """CA-002: veículo inativo prevalece sobre faixa; dois agendamentos sobre motorista."""
    inativo = veiculo(agendamento(faixa_hora_inicio=time(23, 0)), ativo=False)
    assert decidir(placa(), inativo) == EntradaNaoAutorizada(M.VEICULO_INATIVO)
    dois = veiculo(agendamento(motorista_ativo=False), agendamento(id=11))
    assert decidir(placa(), dois) == EntradaNaoAutorizada(M.AGENDAMENTO_AMBIGUO)


def test_dia_vem_do_fuso_do_patio_e_nao_do_servidor() -> None:
    """CA-003 (RN-014): 01:00 UTC do dia 8 ainda é dia 7 no pátio."""
    madrugada = datetime(2026, 11, 8, 1, 0, tzinfo=UTC)
    situacao = veiculo(agendamento(faixa_hora_inicio=time(20, 0)))
    assert isinstance(
        decidir_autorizacao(placa(), situacao, madrugada, FUSO), EntradaAutorizada
    )
    assert decidir_autorizacao(
        placa(), situacao, madrugada, UTC
    ) == EntradaNaoAutorizada(M.SEM_AGENDAMENTO)


def test_volta_aceita_em_carga_descarga_sem_reaplicar_horario() -> None:
    """CA-004 (RN-018; spec 006 §14)."""
    aberta = OperacaoAberta(7, SituacaoOperacao.EM_CARGA_DESCARGA)
    outro_dia = agendamento(
        status="EM_ANDAMENTO", data_prevista=HOJE - timedelta(days=1)
    )
    situacao = veiculo(outro_dia, operacao_aberta=aberta)
    assert decidir(placa(), situacao) == RetornoAceito(7)
    assert decidir(
        RejeicaoLeituraPlaca(MotivoRejeicaoLeituraPlaca.CONFIANCA_BAIXA), situacao
    ) == (EntradaNaoAutorizada(M.CONFIANCA_BAIXA))


def test_liberacao_manual_ignora_faixa_mas_exige_o_resto() -> None:
    """CA-020 (RN-016, §6.7)."""
    cedo = veiculo(agendamento(faixa_hora_inicio=time(23, 0)))
    assert decidir_liberacao_manual(cedo, 10, AGORA, FUSO) == EntradaAutorizada(
        10, 5, TipoOperacao.CARGA
    )
    assert decidir_liberacao_manual(cedo, 99, AGORA, FUSO) == EntradaNaoAutorizada(
        M.SEM_AGENDAMENTO
    )
    assert decidir_liberacao_manual(None, 10, AGORA, FUSO) == EntradaNaoAutorizada(
        M.VEICULO_NAO_CADASTRADO
    )
    inativo = veiculo(agendamento(), ativo=False)
    assert decidir_liberacao_manual(inativo, 10, AGORA, FUSO) == EntradaNaoAutorizada(
        M.VEICULO_INATIVO
    )
    em_carga = veiculo(
        agendamento(),
        operacao_aberta=OperacaoAberta(7, SituacaoOperacao.EM_CARGA_DESCARGA),
    )
    assert decidir_liberacao_manual(em_carga, 10, AGORA, FUSO) == EntradaNaoAutorizada(
        M.OPERACAO_JA_ABERTA
    )
    assert M.ANTES_DA_FAIXA in MOTIVOS_SUBSTITUIVEIS
    assert M.SEM_AGENDAMENTO not in MOTIVOS_SUBSTITUIVEIS
