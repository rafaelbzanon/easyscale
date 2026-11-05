"""Testes da seleção da placa (spec 005 §6.3; RN-002, RN-003)."""

from decimal import Decimal

import pytest

from pesagem.dominio.erros import ErroParametrosInvalidos
from pesagem.dominio.placa.selecao import (
    CandidatoPlaca,
    MotivoRejeicaoLeituraPlaca,
    ParametrosLeituraPlaca,
    PlacaSelecionada,
    RejeicaoLeituraPlaca,
    selecionar_placa,
)

LIMIAR = ParametrosLeituraPlaca(Decimal("0.800"))


def candidato(placa_lida: str, confianca: str) -> CandidatoPlaca:
    return CandidatoPlaca(placa_lida, Decimal(confianca))


def motivo(resultado: PlacaSelecionada | RejeicaoLeituraPlaca) -> str:
    assert isinstance(resultado, RejeicaoLeituraPlaca)
    return resultado.motivo


@pytest.mark.parametrize("confianca", ["0.800", "0.801", "1.000"])
def test_aceita_candidato_unico_no_limiar_ou_acima(confianca: str) -> None:
    """CA-012 (RN-002: limiar inclusivo)."""
    resultado = selecionar_placa([candidato("ABC1D23", confianca)], LIMIAR)
    assert isinstance(resultado, PlacaSelecionada)
    assert resultado.placa.placa_normalizada == "ABC1D23"
    assert resultado.confianca == Decimal(confianca)
    assert resultado.indice == 0


def test_rejeita_confianca_abaixo_do_limiar() -> None:
    """CA-013."""
    resultado = selecionar_placa([candidato("ABC1D23", "0.799")], LIMIAR)
    assert motivo(resultado) is MotivoRejeicaoLeituraPlaca.CONFIANCA_BAIXA


def test_rejeita_sem_candidatos() -> None:
    """CA-014."""
    assert motivo(selecionar_placa([], LIMIAR)) is (
        MotivoRejeicaoLeituraPlaca.SEM_CANDIDATO
    )


def test_rejeita_quando_so_ha_candidatos_invalidos() -> None:
    """CA-014: a faixa da placa (`BRASIL`, cidade) não é placa."""
    candidatos = [candidato("BRASIL", "0.990"), candidato("GRAMADO", "0.990")]
    assert motivo(selecionar_placa(candidatos, LIMIAR)) is (
        MotivoRejeicaoLeituraPlaca.PLACA_INVALIDA
    )


def test_duas_placas_diferentes_sao_ambiguas_mesmo_abaixo_do_limiar() -> None:
    """CA-015 (P-5)."""
    candidatos = [candidato("ABC1D23", "0.990"), candidato("XYZ9876", "0.100")]
    assert motivo(selecionar_placa(candidatos, LIMIAR)) is (
        MotivoRejeicaoLeituraPlaca.AMBIGUA
    )


def test_mesma_placa_antiga_e_mercosul_usa_a_menor_confianca() -> None:
    """CA-016 (P-5; chave de comparação da spec 003 §5.2)."""
    candidatos = [candidato("ABC1234", "0.950"), candidato("ABC1C34", "0.800")]
    resultado = selecionar_placa(candidatos, LIMIAR)
    assert isinstance(resultado, PlacaSelecionada)
    assert resultado.confianca == Decimal("0.800")
    assert resultado.indice == 1
    assert resultado.placa.placa_normalizada == "ABC1C34"


def test_mesma_placa_com_confianca_minima_abaixo_do_limiar_e_rejeitada() -> None:
    """CA-016: a menor confiança decide, mesmo com outra leitura alta."""
    candidatos = [candidato("ABC1234", "0.990"), candidato("ABC-1234", "0.500")]
    assert motivo(selecionar_placa(candidatos, LIMIAR)) is (
        MotivoRejeicaoLeituraPlaca.CONFIANCA_BAIXA
    )


def test_empate_de_confianca_devolve_o_primeiro() -> None:
    """§6.3, passo 4."""
    candidatos = [candidato("ABC1234", "0.900"), candidato("abc1234", "0.900")]
    resultado = selecionar_placa(candidatos, LIMIAR)
    assert isinstance(resultado, PlacaSelecionada)
    assert resultado.indice == 0


def test_candidato_invalido_e_ignorado_antes_do_limiar() -> None:
    """CA-017: `CONFIANCA_BAIXA`, e não `PLACA_INVALIDA`."""
    candidatos = [candidato("BRASIL", "0.990"), candidato("ABC1D23", "0.500")]
    assert motivo(selecionar_placa(candidatos, LIMIAR)) is (
        MotivoRejeicaoLeituraPlaca.CONFIANCA_BAIXA
    )


def test_indice_aponta_o_candidato_na_entrada() -> None:
    """§5.3: o índice conta também os candidatos inválidos."""
    candidatos = [candidato("BRASIL", "0.990"), candidato("ABC1D23", "0.900")]
    resultado = selecionar_placa(candidatos, LIMIAR)
    assert isinstance(resultado, PlacaSelecionada)
    assert resultado.indice == 1


@pytest.mark.parametrize("limiar", ["0", "-0.5", "1.5", "NaN", "Infinity", "-0"])
def test_limiar_invalido_levanta_erro_ao_criar(limiar: str) -> None:
    """CA-018."""
    with pytest.raises(ErroParametrosInvalidos):
        ParametrosLeituraPlaca(Decimal(limiar))


def test_limiar_um_e_aceito() -> None:
    """CA-018."""
    assert ParametrosLeituraPlaca(Decimal("1")).limiar_confianca == Decimal("1")
