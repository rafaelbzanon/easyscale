"""Interfaces da cancela (spec 004 §5.2).

O estado vem sempre do sensor de status, nunca do comando enviado (P-7).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class EstadoCancela(StrEnum):
    ABERTA = "ABERTA"
    FECHADA = "FECHADA"
    DESCONHECIDO = "DESCONHECIDO"


class ResultadoComando(StrEnum):
    CONFIRMADO = "CONFIRMADO"
    FALHA = "FALHA"
    SEM_CONFIRMACAO = "SEM_CONFIRMACAO"


class ComandoCancela(StrEnum):
    ABRIR = "ABRIR"
    FECHAR = "FECHAR"


class RetornoEnvio(StrEnum):
    """O que o equipamento respondeu ao envio, antes de olhar o sensor."""

    ENVIADO = "ENVIADO"
    FALHA_INFORMADA = "FALHA_INFORMADA"


@dataclass(frozen=True)
class ResultadoComandoCancela:
    resultado: ResultadoComando
    tentativas: int


class Cancela(Protocol):
    async def abrir(self) -> ResultadoComandoCancela: ...

    async def fechar(self) -> ResultadoComandoCancela: ...

    async def consultar_estado(self) -> EstadoCancela: ...
