"""Balança simulada para testes e demonstração (spec 004 §6.3).

Não faz I/O e não espera tempo real. Não valida o peso: quem aceita ou rejeita
é a regra da spec 002.
"""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pesagem.dispositivos.balanca.interface import (
    FalhaBalanca,
    LeituraBalanca,
    MotivoFalhaBalanca,
    PesoRecebido,
)
from pesagem.dispositivos.balanca.tentativas import ler_com_segunda_tentativa


class CenarioBalanca(StrEnum):
    ESTAVEL = "ESTAVEL"
    INSTAVEL = "INSTAVEL"
    SEM_RESPOSTA = "SEM_RESPOSTA"
    SEM_RESPOSTA_NA_PRIMEIRA = "SEM_RESPOSTA_NA_PRIMEIRA"
    QUADRO_CORROMPIDO = "QUADRO_CORROMPIDO"
    DESCONECTADA = "DESCONECTADA"


_FALHAS = {
    CenarioBalanca.SEM_RESPOSTA: MotivoFalhaBalanca.SEM_RESPOSTA,
    CenarioBalanca.QUADRO_CORROMPIDO: MotivoFalhaBalanca.QUADRO_CORROMPIDO,
    CenarioBalanca.DESCONECTADA: MotivoFalhaBalanca.DESCONECTADA,
}


class BalancaSimulada:
    def __init__(
        self,
        cenario: CenarioBalanca,
        peso_kg: Decimal,
        relogio: Callable[[], datetime],
        amplitude_kg: Decimal = Decimal("0"),
    ) -> None:
        self._peso_kg = peso_kg
        self._amplitude_kg = amplitude_kg
        self._relogio = relogio
        self.definir_cenario(cenario)

    def definir_cenario(self, cenario: CenarioBalanca) -> None:
        self._cenario = cenario
        self._proxima_abaixo = True

    async def ler_peso(self) -> LeituraBalanca | FalhaBalanca:
        tentativas_feitas = 0

        async def tentar() -> PesoRecebido | MotivoFalhaBalanca:
            nonlocal tentativas_feitas
            tentativas_feitas += 1
            return self._tentar(tentativas_feitas)

        return await ler_com_segunda_tentativa(tentar, _sem_espera)

    def _tentar(self, tentativa: int) -> PesoRecebido | MotivoFalhaBalanca:
        cenario = self._cenario
        if cenario in _FALHAS:
            return _FALHAS[cenario]
        if cenario is CenarioBalanca.SEM_RESPOSTA_NA_PRIMEIRA and tentativa == 1:
            return MotivoFalhaBalanca.SEM_RESPOSTA
        peso_kg = self._peso_kg
        if cenario is CenarioBalanca.INSTAVEL:
            sinal = -1 if self._proxima_abaixo else 1
            self._proxima_abaixo = not self._proxima_abaixo
            peso_kg += sinal * self._amplitude_kg
        return PesoRecebido(peso_kg, self._relogio())


async def _sem_espera() -> None:
    """O simulador não espera o intervalo entre tentativas (§6.3)."""
