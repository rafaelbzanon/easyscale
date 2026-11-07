"""Balança real por RS232 com PySerial (spec 029; spec 004 §5.1, §6).

Só este arquivo importa `serial` (`CONVENCOES.md` P-6). O formato do quadro é do
`ProtocoloBalanca`; aqui ficam a porta, os prazos e o mapeamento das falhas. O
peso não é validado aqui: quem aceita ou rejeita é a spec 002.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import serial  # type: ignore[import-untyped]

from pesagem.dispositivos.balanca.interface import (
    FalhaBalanca,
    LeituraBalanca,
    MotivoFalhaBalanca,
    PesoRecebido,
    ProtocoloBalanca,
)
from pesagem.dispositivos.balanca.tentativas import ler_com_segunda_tentativa

# Valores aceitos pelo PySerial, indexados pelo texto da variável (spec 029 §6.3).
BAUD_RATES: dict[str, int] = {str(b): b for b in serial.Serial.BAUDRATES}
PARIDADES: dict[str, str] = {p: p for p in serial.PARITY_NAMES}
DATA_BITS: dict[str, int] = {str(b): b for b in serial.Serial.BYTESIZES}
STOP_BITS: dict[str, float] = {str(s): s for s in serial.Serial.STOPBITS}


@dataclass(frozen=True)
class ParametrosSerial:
    porta: str
    baud_rate: int
    paridade: str
    data_bits: int
    stop_bits: float
    timeout_ms: int
    intervalo_tentativa_ms: int


class BalancaSerial:
    """Única dona da porta (ADR-0002): abre na primeira leitura, mantém aberta e,
    depois de `DESCONECTADA`, tenta reabrir uma vez por chamada."""

    def __init__(
        self,
        protocolo: ProtocoloBalanca,
        parametros: ParametrosSerial,
        relogio: Callable[[], datetime],
    ) -> None:
        self._protocolo = protocolo
        self._parametros = parametros
        self._relogio = relogio
        self._porta: Any = None

    async def ler_peso(self) -> LeituraBalanca | FalhaBalanca:
        return await ler_com_segunda_tentativa(self._tentar, self._esperar_intervalo)

    async def _tentar(self) -> PesoRecebido | MotivoFalhaBalanca:
        quadro = await asyncio.to_thread(self._receber_quadro)
        if isinstance(quadro, MotivoFalhaBalanca):
            return quadro
        peso_kg = self._protocolo.interpretar_quadro(quadro)
        if peso_kg is None:
            return MotivoFalhaBalanca.QUADRO_CORROMPIDO
        return PesoRecebido(peso_kg, self._relogio())

    async def _esperar_intervalo(self) -> None:
        await asyncio.sleep(self._parametros.intervalo_tentativa_ms / 1000)

    def _receber_quadro(self) -> bytes | MotivoFalhaBalanca:
        try:
            if self._porta is None:
                self._porta = self._abrir()
            return self._ler(self._porta)
        except serial.SerialTimeoutException:
            # O pedido não saiu dentro do write_timeout: tratado como sem resposta.
            return MotivoFalhaBalanca.SEM_RESPOSTA
        except OSError:  # SerialException deriva de OSError
            self.fechar()
            return MotivoFalhaBalanca.DESCONECTADA

    def _abrir(self) -> Any:
        p = self._parametros
        timeout_s = p.timeout_ms / 1000
        return serial.serial_for_url(
            p.porta,
            baudrate=p.baud_rate,
            bytesize=p.data_bits,
            parity=p.paridade,
            stopbits=p.stop_bits,
            timeout=timeout_s,
            write_timeout=timeout_s,
            exclusive=True,  # outro processo não abre a mesma porta (ADR-0002)
        )

    def _ler(self, porta: Any) -> bytes | MotivoFalhaBalanca:
        # Nunca usa um peso que chegou antes desta tentativa (spec 029 §6.1).
        porta.reset_input_buffer()
        pedido = self._protocolo.montar_pedido()
        if pedido is not None:
            porta.write(pedido)
        prazo = time.monotonic() + self._parametros.timeout_ms / 1000
        recebido = b""
        while (restante := prazo - time.monotonic()) > 0:
            porta.timeout = restante
            recebido += porta.read(max(1, porta.in_waiting))
            quadro = self._protocolo.extrair_quadro(recebido)
            if quadro is not None:
                return quadro
        return MotivoFalhaBalanca.SEM_RESPOSTA

    def fechar(self) -> None:
        """Libera a porta; a próxima leitura abre de novo."""
        porta, self._porta = self._porta, None
        if porta is not None:
            try:
                porta.close()
            except OSError:
                pass  # a porta já falhou; o que importa é reabrir na próxima chamada
