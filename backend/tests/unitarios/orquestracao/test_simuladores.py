"""Controle dos simuladores (spec 015 §6.9; CA-024)."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from test_operacao import Cenario

from pesagem.dispositivos.balanca.interface import LeituraBalanca
from pesagem.dispositivos.balanca.simulada import CenarioBalanca
from pesagem.dispositivos.cancela.interface import EstadoCancela
from pesagem.dispositivos.cancela.simulada import CenarioCancela
from pesagem.dispositivos.modo import ModoDispositivo
from pesagem.dominio.operacao.maquina_estados import CancelaPedida
from pesagem.lpr.posicao.interface import ResultadoPosicao
from pesagem.lpr.posicao.simulada import CenarioPosicao
from pesagem.lpr.resultado import TextoOcr
from pesagem.orquestracao.simuladores import Simuladores, criar_simuladores

AGORA = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)


def montar(cenario: Cenario) -> Simuladores:
    return Simuladores(
        cenario.orquestracao,
        {CancelaPedida.ENTRADA: cenario.entrada, CancelaPedida.SAIDA: cenario.saida},
        cenario.posicao,
        cenario.reconhecedor,
        cenario.relogio,
        CenarioBalanca.ESTAVEL,
        Decimal("15000"),
        Decimal("0"),
        {c: CenarioCancela.CONFIRMADO for c in CancelaPedida},
        CenarioPosicao.AUSENTE,
    )


def test_troca_cenarios_e_enfileira_chegada() -> None:
    """CA-024."""

    async def rodar() -> None:
        c = Cenario()
        simuladores = montar(c)
        simuladores.definir_balanca(
            CenarioBalanca.INSTAVEL, Decimal("200"), Decimal("7")
        )
        leitura = await c.orquestracao.balanca.ler_peso()
        assert isinstance(leitura, LeituraBalanca) and leitura.peso_kg == Decimal("193")
        simuladores.definir_cancela(
            CancelaPedida.SAIDA, CenarioCancela.SENSOR_SEM_RESPOSTA
        )
        assert await c.saida.consultar_estado() is EstadoCancela.DESCONHECIDO
        assert await c.entrada.consultar_estado() is EstadoCancela.FECHADA
        simuladores.definir_posicao(CenarioPosicao.CONFIRMADA)
        assert (
            await c.posicao.analisar_posicao()
        ).resultado is ResultadoPosicao.CONFIRMADA
        simuladores.simular_chegada([TextoOcr("ABC1234", 0.9)])
        estado = simuladores.estado()
        assert (estado.cenario_balanca, estado.peso_kg, estado.amplitude_kg) == (
            CenarioBalanca.INSTAVEL,
            Decimal("200"),
            Decimal("7"),
        )
        assert (
            estado.cenario_cancelas[CancelaPedida.SAIDA]
            is CenarioCancela.SENSOR_SEM_RESPOSTA
        )
        assert estado.cenario_posicao is CenarioPosicao.CONFIRMADA
        assert estado.chegadas_na_fila == 1

    asyncio.run(rodar())


def test_nao_existe_com_algum_dispositivo_real() -> None:
    """CA-024."""
    c = Cenario()
    modos = [ModoDispositivo.SIMULADO, ModoDispositivo.REAL, ModoDispositivo.SIMULADO]
    assert criar_simuladores(modos, lambda: montar(c)) is None
    assert (
        criar_simuladores([ModoDispositivo.SIMULADO] * 3, lambda: montar(c)) is not None
    )
