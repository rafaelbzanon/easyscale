"""Testes da aceitação de peso (spec 002 §6.1, `regras-pesagem`)."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from pesagem.dominio.erros import ErroParametrosInvalidos
from pesagem.dominio.pesagem.aceitacao_peso import (
    LeituraPeso,
    MotivoRejeicaoPeso,
    ParametrosAceitacaoPeso,
    PesoAceito,
    RejeicaoPeso,
    validar_leituras_peso,
)

INICIO = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)

# Valores próprios dos testes: a spec não define valores padrão (P-3).
PARAMETROS = ParametrosAceitacaoPeso(
    peso_minimo_kg=Decimal("1000"),
    peso_maximo_kg=Decimal("80000"),
    quantidade_leituras_estaveis=3,
    variacao_maxima_kg=Decimal("10"),
    janela_estabilidade_ms=2000,
)


def em(ms: int) -> datetime:
    return INICIO + timedelta(milliseconds=ms)


def leituras(*pesos: str, instantes_ms: tuple[int, ...] = ()) -> list[LeituraPeso]:
    instantes = instantes_ms or tuple(i * 500 for i in range(len(pesos)))
    return [
        LeituraPeso(Decimal(peso), em(ms))
        for peso, ms in zip(pesos, instantes, strict=True)
    ]


def validar(lista: list[LeituraPeso]) -> PesoAceito | RejeicaoPeso:
    return validar_leituras_peso(lista, PARAMETROS)


def rejeicao(motivo: MotivoRejeicaoPeso) -> RejeicaoPeso:
    return RejeicaoPeso(motivo)


def test_aceita_serie_estavel_e_devolve_a_ultima_leitura() -> None:
    """CA-001 (P-2: sem média nem arredondamento)."""
    lista = leituras("15000.000", "15004.500", "15002.125")
    assert validar(lista) == PesoAceito(Decimal("15002.125"), lista[-1].lida_em)
    resultado = validar(lista)
    assert isinstance(resultado, PesoAceito)
    assert str(resultado.peso_kg) == "15002.125"


def test_usa_so_as_ultimas_leituras_para_a_estabilidade() -> None:
    """CA-001: leituras antigas, mas válidas e em ordem, não impedem a aceitação."""
    lista = leituras("2000", "9000", "15000", "15001", "15002")
    assert validar(lista) == PesoAceito(Decimal("15002"), lista[-1].lida_em)


def test_aceita_lida_em_com_fuso_diferente_de_utc() -> None:
    """CA-001: qualquer fuso explícito é válido."""
    fuso = timezone(timedelta(hours=-3))
    lista = [
        LeituraPeso(
            Decimal("15000"), (INICIO + timedelta(milliseconds=ms)).astimezone(fuso)
        )
        for ms in (0, 500, 1000)
    ]
    assert isinstance(validar(lista), PesoAceito)


def test_variacao_igual_ao_limite_e_aceita() -> None:
    """CA-002."""
    assert isinstance(validar(leituras("15000", "15010", "15005")), PesoAceito)


@pytest.mark.parametrize("maior", ["15010.001", "15011"])
def test_variacao_acima_do_limite_e_instavel(maior: str) -> None:
    """CA-002."""
    resultado = validar(leituras("15000", maior, "15005"))
    assert resultado == rejeicao(MotivoRejeicaoPeso.INSTAVEL)


def test_janela_igual_ao_limite_e_aceita() -> None:
    """CA-003."""
    lista = leituras("15000", "15000", "15000", instantes_ms=(0, 1000, 2000))
    assert isinstance(validar(lista), PesoAceito)


def test_janela_1_ms_acima_do_limite_e_instavel() -> None:
    """CA-003."""
    lista = leituras("15000", "15000", "15000", instantes_ms=(0, 1000, 2001))
    assert validar(lista) == rejeicao(MotivoRejeicaoPeso.INSTAVEL)


@pytest.mark.parametrize("peso", ["1000", "80000", "1000.000", "80000.000"])
def test_peso_nos_limites_da_faixa_e_aceito(peso: str) -> None:
    """CA-004."""
    lista = leituras(peso, peso, peso)
    assert validar(lista) == PesoAceito(Decimal(peso), lista[-1].lida_em)


@pytest.mark.parametrize("peso", ["999.999", "80000.001", "0", "-5"])
def test_peso_fora_da_faixa_e_rejeitado(peso: str) -> None:
    """CA-004 (inclui peso negativo, com mínimo >= 0)."""
    assert validar(leituras(peso, peso, peso)) == rejeicao(
        MotivoRejeicaoPeso.FORA_DE_FAIXA
    )


def test_uma_leitura_da_serie_fora_da_faixa_rejeita() -> None:
    """CA-004: todas as leituras da série precisam estar na faixa."""
    lista = leituras("999.999", "1000", "1005")
    assert validar(lista) == rejeicao(MotivoRejeicaoPeso.FORA_DE_FAIXA)


@pytest.mark.parametrize("pesos", [(), ("15000",), ("15000", "15000")])
def test_leituras_insuficientes(pesos: tuple[str, ...]) -> None:
    """CA-005."""
    assert validar(leituras(*pesos)) == rejeicao(
        MotivoRejeicaoPeso.LEITURAS_INSUFICIENTES
    )


@pytest.mark.parametrize("valor", ["NaN", "sNaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("posicao", [0, 2, 4])
def test_peso_nao_finito_e_leitura_invalida(valor: str, posicao: int) -> None:
    """CA-006: a leitura inválida não é descartada, mesmo fora da série final."""
    lista = leituras("15000", "15000", "15000", "15000", "15000")
    lista[posicao] = LeituraPeso(Decimal(valor), lista[posicao].lida_em)
    assert validar(lista) == rejeicao(MotivoRejeicaoPeso.LEITURA_INVALIDA)


@pytest.mark.parametrize("posicao", [0, 2])
def test_lida_em_sem_fuso_e_leitura_invalida(posicao: int) -> None:
    """CA-006."""
    lista = leituras("15000", "15000", "15000")
    sem_fuso = lista[posicao].lida_em.replace(tzinfo=None)
    lista[posicao] = LeituraPeso(lista[posicao].peso_kg, sem_fuso)
    assert validar(lista) == rejeicao(MotivoRejeicaoPeso.LEITURA_INVALIDA)


@pytest.mark.parametrize(
    "instantes_ms",
    [(0, 500, 500), (0, 0, 500), (0, 1000, 500), (1000, 500, 0), (500, 0, 1000, 1500)],
)
def test_instantes_repetidos_ou_decrescentes_sao_fora_de_ordem(
    instantes_ms: tuple[int, ...],
) -> None:
    """CA-007 (inclui desordem fora da série final)."""
    pesos = ("15000",) * len(instantes_ms)
    lista = leituras(*pesos, instantes_ms=instantes_ms)
    assert validar(lista) == rejeicao(MotivoRejeicaoPeso.FORA_DE_ORDEM)


@pytest.mark.parametrize(
    ("lista", "esperado"),
    [
        # Curta e inválida: LEITURAS_INSUFICIENTES vem primeiro.
        (
            [LeituraPeso(Decimal("NaN"), em(0))],
            MotivoRejeicaoPeso.LEITURAS_INSUFICIENTES,
        ),
        # Inválida e fora de ordem: LEITURA_INVALIDA.
        (
            leituras("NaN", "15000", "15000", instantes_ms=(1000, 500, 0)),
            MotivoRejeicaoPeso.LEITURA_INVALIDA,
        ),
        # Fora de ordem, instável e fora da faixa: FORA_DE_ORDEM.
        (
            leituras("10", "90000", "500", instantes_ms=(0, 0, 5000)),
            MotivoRejeicaoPeso.FORA_DE_ORDEM,
        ),
        # Instável e fora da faixa: INSTAVEL.
        (leituras("10", "90000", "500"), MotivoRejeicaoPeso.INSTAVEL),
        # Fora da janela e fora da faixa: INSTAVEL.
        (
            leituras("10", "10", "10", instantes_ms=(0, 1000, 5000)),
            MotivoRejeicaoPeso.INSTAVEL,
        ),
    ],
)
def test_motivo_segue_a_ordem_da_spec(
    lista: list[LeituraPeso], esperado: MotivoRejeicaoPeso
) -> None:
    """CA-008."""
    assert validar(lista) == rejeicao(esperado)


def parametros(**alteracoes: object) -> ParametrosAceitacaoPeso:
    valores: dict[str, object] = {
        "peso_minimo_kg": Decimal("1000"),
        "peso_maximo_kg": Decimal("80000"),
        "quantidade_leituras_estaveis": 3,
        "variacao_maxima_kg": Decimal("10"),
        "janela_estabilidade_ms": 2000,
    }
    valores.update(alteracoes)
    return ParametrosAceitacaoPeso(**valores)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"peso_minimo_kg": Decimal("80000")},
        {"peso_minimo_kg": Decimal("90000")},
        {"peso_minimo_kg": Decimal("-0.001")},
        {"quantidade_leituras_estaveis": 1},
        {"quantidade_leituras_estaveis": 0},
        {"variacao_maxima_kg": Decimal("-0.001")},
        {"janela_estabilidade_ms": 0},
        {"janela_estabilidade_ms": -1},
        {"peso_minimo_kg": Decimal("NaN")},
        {"peso_maximo_kg": Decimal("Infinity")},
        {"variacao_maxima_kg": Decimal("NaN")},
    ],
)
def test_parametros_incoerentes_levantam_erro(alteracoes: dict[str, object]) -> None:
    """CA-009 (inclui valores não finitos)."""
    with pytest.raises(ErroParametrosInvalidos):
        parametros(**alteracoes)


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"peso_minimo_kg": Decimal("0")},
        {"quantidade_leituras_estaveis": 2},
        {"variacao_maxima_kg": Decimal("0")},
        {"janela_estabilidade_ms": 1},
    ],
)
def test_parametros_nos_limites_validos_sao_aceitos(
    alteracoes: dict[str, object],
) -> None:
    """CA-009: os limites da §7 que não são incoerentes."""
    parametros(**alteracoes)


def test_variacao_zero_exige_pesos_identicos() -> None:
    """CA-002 com variação máxima 0."""
    rigidos = parametros(variacao_maxima_kg=Decimal("0"))
    iguais = leituras("15000", "15000.000", "15000")
    diferentes = leituras("15000", "15000.001", "15000")
    assert isinstance(validar_leituras_peso(iguais, rigidos), PesoAceito)
    assert validar_leituras_peso(diferentes, rigidos) == rejeicao(
        MotivoRejeicaoPeso.INSTAVEL
    )
