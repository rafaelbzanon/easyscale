"""Testes da balança simulada e da segunda tentativa (spec 004, `camada-dispositivos`)."""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from pesagem.dispositivos.balanca.interface import (
    Balanca,
    FalhaBalanca,
    LeituraBalanca,
    MotivoFalhaBalanca,
    PesoRecebido,
)
from pesagem.dispositivos.balanca.simulada import BalancaSimulada, CenarioBalanca
from pesagem.dispositivos.balanca.tentativas import ler_com_segunda_tentativa
from pesagem.dominio.pesagem.aceitacao_peso import (
    LeituraPeso,
    MotivoRejeicaoPeso,
    ParametrosAceitacaoPeso,
    RejeicaoPeso,
    validar_leituras_peso,
)

INICIO = datetime(2026, 10, 29, 8, 0, tzinfo=UTC)
PESO = Decimal("15000.000")


class RelogioControlado:
    """Avança 500 ms a cada leitura."""

    def __init__(self) -> None:
        self.agora = INICIO

    def __call__(self) -> datetime:
        instante = self.agora
        self.agora += timedelta(milliseconds=500)
        return instante


def balanca(
    cenario: CenarioBalanca, amplitude_kg: Decimal = Decimal("0")
) -> BalancaSimulada:
    return BalancaSimulada(cenario, PESO, RelogioControlado(), amplitude_kg)


def ler(simulada: Balanca, vezes: int = 1) -> list[LeituraBalanca | FalhaBalanca]:
    async def ler_varias() -> list[LeituraBalanca | FalhaBalanca]:
        return [await simulada.ler_peso() for _ in range(vezes)]

    return asyncio.run(ler_varias())


def test_estavel_devolve_o_peso_configurado_com_o_relogio_injetado() -> None:
    """CA-001."""
    assert ler(balanca(CenarioBalanca.ESTAVEL), 3) == [
        LeituraBalanca(PESO, INICIO, 1),
        LeituraBalanca(PESO, INICIO + timedelta(milliseconds=500), 1),
        LeituraBalanca(PESO, INICIO + timedelta(milliseconds=1000), 1),
    ]


def test_instavel_alterna_abaixo_e_acima_do_peso() -> None:
    """CA-002."""
    leituras = ler(balanca(CenarioBalanca.INSTAVEL, Decimal("8")), 4)
    pesos = [
        leitura.peso_kg for leitura in leituras if isinstance(leitura, LeituraBalanca)
    ]
    assert pesos == [
        Decimal("14992"),
        Decimal("15008"),
        Decimal("14992"),
        Decimal("15008"),
    ]


def test_serie_instavel_e_rejeitada_pela_spec_002() -> None:
    """CA-002: amplitude 8 kg dá variação de 16 kg, acima do limite de 10 kg."""
    parametros = ParametrosAceitacaoPeso(
        peso_minimo_kg=Decimal("1000"),
        peso_maximo_kg=Decimal("80000"),
        quantidade_leituras_estaveis=3,
        variacao_maxima_kg=Decimal("10"),
        janela_estabilidade_ms=2000,
    )
    leituras = [
        LeituraPeso(leitura.peso_kg, leitura.lida_em)
        for leitura in ler(balanca(CenarioBalanca.INSTAVEL, Decimal("8")), 3)
        if isinstance(leitura, LeituraBalanca)
    ]
    assert validar_leituras_peso(leituras, parametros) == RejeicaoPeso(
        MotivoRejeicaoPeso.INSTAVEL
    )


def test_sem_resposta_faz_segunda_tentativa_e_falha() -> None:
    """CA-003."""
    assert ler(balanca(CenarioBalanca.SEM_RESPOSTA)) == [
        FalhaBalanca(MotivoFalhaBalanca.SEM_RESPOSTA, 2)
    ]


def test_sem_resposta_na_primeira_devolve_a_leitura_da_segunda() -> None:
    """CA-003 (P-9: a balança pode demorar para estabilizar)."""
    assert ler(balanca(CenarioBalanca.SEM_RESPOSTA_NA_PRIMEIRA)) == [
        LeituraBalanca(PESO, INICIO, 2)
    ]


@pytest.mark.parametrize(
    ("cenario", "motivo"),
    [
        (CenarioBalanca.QUADRO_CORROMPIDO, MotivoFalhaBalanca.QUADRO_CORROMPIDO),
        (CenarioBalanca.DESCONECTADA, MotivoFalhaBalanca.DESCONECTADA),
    ],
)
def test_quadro_corrompido_e_desconectada_nao_repetem(
    cenario: CenarioBalanca, motivo: MotivoFalhaBalanca
) -> None:
    """CA-004."""
    assert ler(balanca(cenario)) == [FalhaBalanca(motivo, 1)]


def test_simulador_nao_espera_tempo_real() -> None:
    """CA-005."""
    simulada = balanca(CenarioBalanca.SEM_RESPOSTA)
    inicio = time.perf_counter()
    resultados = ler(simulada, 1000)
    assert time.perf_counter() - inicio < 1
    assert len(resultados) == 1000


def test_definir_cenario_vale_a_partir_da_chamada_seguinte() -> None:
    """CA-006."""
    simulada = balanca(CenarioBalanca.ESTAVEL)
    primeira = ler(simulada)
    simulada.definir_cenario(CenarioBalanca.DESCONECTADA)
    segunda = ler(simulada)
    assert isinstance(primeira[0], LeituraBalanca)
    assert segunda == [FalhaBalanca(MotivoFalhaBalanca.DESCONECTADA, 1)]


def test_peso_nao_e_validado_pelo_simulador() -> None:
    """§6.3: peso negativo é só um valor configurado; quem rejeita é a spec 002."""
    simulada = BalancaSimulada(
        CenarioBalanca.ESTAVEL, Decimal("-5"), RelogioControlado()
    )
    assert ler(simulada) == [LeituraBalanca(Decimal("-5"), INICIO, 1)]


def roteiro(
    *resultados: PesoRecebido | MotivoFalhaBalanca,
) -> tuple[list[int], LeituraBalanca | FalhaBalanca]:
    """Executa a política com tentativas roteirizadas; devolve as esperas feitas."""
    fila = list(resultados)
    esperas: list[int] = []

    async def tentar() -> PesoRecebido | MotivoFalhaBalanca:
        return fila.pop(0)

    async def esperar() -> None:
        esperas.append(1)

    resultado = asyncio.run(ler_com_segunda_tentativa(tentar, esperar))
    return esperas, resultado


def test_politica_espera_o_intervalo_so_antes_da_segunda_tentativa() -> None:
    """§6.2: um intervalo entre as tentativas; nenhum quando não há repetição."""
    peso = PesoRecebido(PESO, INICIO)
    assert roteiro(peso) == ([], LeituraBalanca(PESO, INICIO, 1))
    assert roteiro(MotivoFalhaBalanca.SEM_RESPOSTA, peso) == (
        [1],
        LeituraBalanca(PESO, INICIO, 2),
    )
    assert roteiro(
        MotivoFalhaBalanca.SEM_RESPOSTA, MotivoFalhaBalanca.QUADRO_CORROMPIDO
    ) == ([1], FalhaBalanca(MotivoFalhaBalanca.QUADRO_CORROMPIDO, 2))


def test_politica_nunca_passa_de_2_tentativas() -> None:
    """§6.2."""
    esperas, resultado = roteiro(
        MotivoFalhaBalanca.SEM_RESPOSTA,
        MotivoFalhaBalanca.SEM_RESPOSTA,
        PesoRecebido(PESO, INICIO),
    )
    assert esperas == [1]
    assert resultado == FalhaBalanca(MotivoFalhaBalanca.SEM_RESPOSTA, 2)


def test_simulada_satisfaz_a_interface() -> None:
    """CA-017: o mypy estrito verifica a atribuição."""
    interface: Balanca = balanca(CenarioBalanca.ESTAVEL)
    assert isinstance(ler(interface)[0], LeituraBalanca)
