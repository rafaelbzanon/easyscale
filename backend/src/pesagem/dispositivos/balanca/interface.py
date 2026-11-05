"""Interfaces da balança (spec 004 §5.1).

Tipos próprios da camada: `dispositivos` não importa `dominio` (P-6). A
orquestração converte `LeituraBalanca` em `LeituraPeso`.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class MotivoFalhaBalanca(StrEnum):
    SEM_RESPOSTA = "SEM_RESPOSTA"
    QUADRO_CORROMPIDO = "QUADRO_CORROMPIDO"
    DESCONECTADA = "DESCONECTADA"


@dataclass(frozen=True)
class LeituraBalanca:
    peso_kg: Decimal
    lida_em: datetime
    tentativas: int


@dataclass(frozen=True)
class FalhaBalanca:
    motivo: MotivoFalhaBalanca
    tentativas: int


@dataclass(frozen=True)
class PesoRecebido:
    """Resultado de uma única tentativa bem-sucedida, antes da política."""

    peso_kg: Decimal
    lida_em: datetime


class Balanca(Protocol):
    async def ler_peso(self) -> LeituraBalanca | FalhaBalanca:
        """Uma leitura, com no máximo 2 tentativas (§6.2)."""
        ...


class ProtocoloBalanca(Protocol):
    """O que muda de um modelo de balança para outro, sem I/O (RF-030).

    Cada modelo é implementado a partir do manual e de quadros reais; nenhum
    existe ainda (Q-01).
    """

    def montar_pedido(self) -> bytes | None:
        """Bytes do pedido de leitura, ou `None` se o modelo envia sem pedido."""
        ...

    def interpretar_quadro(self, quadro: bytes) -> Decimal | None:
        """Peso em kg, ou `None` se o quadro está corrompido."""
        ...
