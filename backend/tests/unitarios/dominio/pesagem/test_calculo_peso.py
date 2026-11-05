"""Testes do cálculo do peso líquido (spec 002 §6.2, `regras-pesagem`)."""

from decimal import Decimal
from typing import cast

import pytest

from pesagem.dominio.erros import ErroParametrosInvalidos, ErroTipoOperacaoInvalido
from pesagem.dominio.pesagem.calculo_peso import (
    ClassificacaoPesoLiquido,
    ParametrosPesoLiquido,
    ResultadoPesoLiquido,
    TipoOperacao,
    calcular_peso_liquido,
)

TOLERANCIA = ParametrosPesoLiquido(Decimal("20"))


def test_carga_e_final_menos_inicial() -> None:
    """CA-010."""
    resultado = calcular_peso_liquido(
        TipoOperacao.CARGA, Decimal("15000.125"), Decimal("42000.250"), TOLERANCIA
    )
    assert resultado == ResultadoPesoLiquido(
        Decimal("27000.125"), ClassificacaoPesoLiquido.COM_MOVIMENTACAO
    )
    assert str(resultado.peso_liquido_kg) == "27000.125"


def test_descarga_e_inicial_menos_final() -> None:
    """CA-010."""
    resultado = calcular_peso_liquido(
        TipoOperacao.DESCARGA, Decimal("42000.250"), Decimal("15000.125"), TOLERANCIA
    )
    assert resultado == ResultadoPesoLiquido(
        Decimal("27000.125"), ClassificacaoPesoLiquido.COM_MOVIMENTACAO
    )


def test_decimal_sem_perda_de_precisao() -> None:
    """CA-010: com float, 0.3 - 0.1 daria 0.19999999999999998."""
    resultado = calcular_peso_liquido(
        TipoOperacao.CARGA, Decimal("0.1"), Decimal("1000.3"), TOLERANCIA
    )
    assert str(resultado.peso_liquido_kg) == "1000.2"


@pytest.mark.parametrize(
    ("liquido", "classificacao"),
    [
        ("20", ClassificacaoPesoLiquido.SEM_MOVIMENTACAO),
        ("0", ClassificacaoPesoLiquido.SEM_MOVIMENTACAO),
        ("-20", ClassificacaoPesoLiquido.SEM_MOVIMENTACAO),
        ("20.001", ClassificacaoPesoLiquido.COM_MOVIMENTACAO),
        ("-20.001", ClassificacaoPesoLiquido.NEGATIVO_FORA_TOLERANCIA),
        ("-5000", ClassificacaoPesoLiquido.NEGATIVO_FORA_TOLERANCIA),
    ],
)
@pytest.mark.parametrize("tipo", list(TipoOperacao))
def test_classificacao_com_tolerancia_de_20_kg(
    liquido: str, classificacao: ClassificacaoPesoLiquido, tipo: TipoOperacao
) -> None:
    """CA-011, para CARGA e DESCARGA."""
    base = Decimal("15000")
    if tipo is TipoOperacao.CARGA:
        inicial, final = base, base + Decimal(liquido)
    else:
        inicial, final = base + Decimal(liquido), base
    resultado = calcular_peso_liquido(tipo, inicial, final, TOLERANCIA)
    assert resultado == ResultadoPesoLiquido(Decimal(liquido), classificacao)


@pytest.mark.parametrize("liquido", ["12", "-12", "0.001"])
def test_sem_movimentacao_devolve_o_valor_calculado(liquido: str) -> None:
    """CA-012: o líquido nunca é trocado por zero."""
    resultado = calcular_peso_liquido(
        TipoOperacao.CARGA,
        Decimal("15000"),
        Decimal("15000") + Decimal(liquido),
        TOLERANCIA,
    )
    assert resultado.classificacao is ClassificacaoPesoLiquido.SEM_MOVIMENTACAO
    assert resultado.peso_liquido_kg == Decimal(liquido)
    assert resultado.peso_liquido_kg != 0


def test_tolerancia_zero() -> None:
    """CA-011 com tolerância 0: só o zero exato é sem movimentação."""

    def classificar(final: str) -> ClassificacaoPesoLiquido:
        return calcular_peso_liquido(
            TipoOperacao.CARGA,
            Decimal("15000"),
            Decimal(final),
            ParametrosPesoLiquido(Decimal("0")),
        ).classificacao

    assert classificar("15000") is ClassificacaoPesoLiquido.SEM_MOVIMENTACAO
    assert classificar("15000.001") is ClassificacaoPesoLiquido.COM_MOVIMENTACAO
    assert classificar("14999.999") is ClassificacaoPesoLiquido.NEGATIVO_FORA_TOLERANCIA


@pytest.mark.parametrize("tipo", ["TRANSFERENCIA", "carga", "", None])
def test_tipo_operacao_invalido_levanta_erro(tipo: object) -> None:
    """CA-013."""
    with pytest.raises(ErroTipoOperacaoInvalido):
        calcular_peso_liquido(
            cast(TipoOperacao, tipo), Decimal("1"), Decimal("2"), TOLERANCIA
        )


@pytest.mark.parametrize("tolerancia", ["-0.001", "NaN", "sNaN", "Infinity"])
def test_tolerancia_invalida_levanta_erro_ao_criar_parametros(tolerancia: str) -> None:
    """CA-009 (tolerância < 0 ou não finita)."""
    with pytest.raises(ErroParametrosInvalidos):
        ParametrosPesoLiquido(Decimal(tolerancia))
