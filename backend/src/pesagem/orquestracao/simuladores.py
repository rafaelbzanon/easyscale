"""Controle dos simuladores (spec 015 §6.9; contrato 011). Só em `SIMULADO`."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pesagem.dispositivos.balanca.simulada import BalancaSimulada, CenarioBalanca
from pesagem.dispositivos.cancela.simulada import CancelaSimulada, CenarioCancela
from pesagem.dispositivos.modo import ModoDispositivo
from pesagem.dominio.operacao.maquina_estados import CancelaPedida
from pesagem.lpr.posicao.simulada import CenarioPosicao, FontePosicaoSimulada
from pesagem.lpr.reconhecedor_simulado import ReconhecedorPlacaSimulado
from pesagem.lpr.resultado import TextoOcr
from pesagem.orquestracao.operacao import Orquestracao


@dataclass(frozen=True)
class EstadoSimuladores:
    cenario_balanca: CenarioBalanca
    peso_kg: Decimal
    amplitude_kg: Decimal
    cenario_cancelas: dict[CancelaPedida, CenarioCancela]
    cenario_posicao: CenarioPosicao
    chegadas_na_fila: int


class Simuladores:
    def __init__(
        self,
        orquestracao: Orquestracao,
        cancelas: dict[CancelaPedida, CancelaSimulada],
        fonte_posicao: FontePosicaoSimulada,
        reconhecedor: ReconhecedorPlacaSimulado,
        relogio: Callable[[], datetime],
        cenario_balanca: CenarioBalanca,
        peso_kg: Decimal,
        amplitude_kg: Decimal,
        cenario_cancelas: dict[CancelaPedida, CenarioCancela],
        cenario_posicao: CenarioPosicao,
    ) -> None:
        self._orquestracao = orquestracao
        self._cancelas = cancelas
        self._fonte_posicao = fonte_posicao
        self._reconhecedor = reconhecedor
        self._relogio = relogio
        self._estado = EstadoSimuladores(
            cenario_balanca,
            peso_kg,
            amplitude_kg,
            dict(cenario_cancelas),
            cenario_posicao,
            0,
        )

    def estado(self) -> EstadoSimuladores:
        return EstadoSimuladores(
            self._estado.cenario_balanca,
            self._estado.peso_kg,
            self._estado.amplitude_kg,
            dict(self._estado.cenario_cancelas),
            self._estado.cenario_posicao,
            self._reconhecedor.tamanho_fila(),
        )

    def definir_balanca(
        self, cenario: CenarioBalanca, peso_kg: Decimal, amplitude_kg: Decimal
    ) -> None:
        # Troca a instância: `BalancaSimulada` fixa o peso na criação (spec 004 §6.3).
        self._orquestracao.balanca = BalancaSimulada(
            cenario, peso_kg, self._relogio, amplitude_kg
        )
        self._estado = EstadoSimuladores(
            cenario,
            peso_kg,
            amplitude_kg,
            self._estado.cenario_cancelas,
            self._estado.cenario_posicao,
            0,
        )

    def definir_cancela(self, cancela: CancelaPedida, cenario: CenarioCancela) -> None:
        self._cancelas[cancela].definir_cenario(cenario)
        self._estado.cenario_cancelas[cancela] = cenario

    def definir_posicao(self, cenario: CenarioPosicao) -> None:
        self._fonte_posicao.definir_cenario(cenario)
        self._estado = EstadoSimuladores(
            self._estado.cenario_balanca,
            self._estado.peso_kg,
            self._estado.amplitude_kg,
            self._estado.cenario_cancelas,
            cenario,
            0,
        )

    def simular_chegada(self, textos: Sequence[TextoOcr]) -> None:
        self._reconhecedor.enfileirar(tuple(textos))


def criar_simuladores(
    modos: Sequence[ModoDispositivo], criar: Callable[[], Simuladores]
) -> Simuladores | None:
    """`None` com qualquer dispositivo em `REAL`: as rotas do contrato 011 não existem."""
    if any(modo is not ModoDispositivo.SIMULADO for modo in modos):
        return None
    return criar()
