"""Interface da fonte de imagem e seus resultados (spec 005 §5.1)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from cv2.typing import MatLike


class MotivoFalhaImagem(StrEnum):
    SEM_IMAGEM = "SEM_IMAGEM"
    IMAGEM_INVALIDA = "IMAGEM_INVALIDA"
    FONTE_INDISPONIVEL = "FONTE_INDISPONIVEL"


# `eq=False`: comparar matrizes do OpenCV com `==` não devolve um booleano.
@dataclass(frozen=True, eq=False)
class ImagemCapturada:
    pixels: MatLike
    capturada_em: datetime
    # Nome do arquivo relativo à pasta; nunca contém a placa (`CONVENCOES.md` §9).
    origem: str


@dataclass(frozen=True)
class FalhaImagem:
    motivo: MotivoFalhaImagem
    origem: str | None


class FonteImagem(Protocol):
    async def obter_imagem(self) -> ImagemCapturada | FalhaImagem: ...
