"""Interface da fonte de posição (spec 015 §5.2)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pesagem.lpr.fontes.interface import ImagemCapturada


class ResultadoPosicao(StrEnum):
    CONFIRMADA = "CONFIRMADA"
    AUSENTE = "AUSENTE"
    INCONCLUSIVA = "INCONCLUSIVA"


# `eq=False`: a imagem é uma matriz do OpenCV.
@dataclass(frozen=True, eq=False)
class LeituraPosicao:
    resultado: ResultadoPosicao
    capturada_em: datetime
    # `None` quando a câmera não entregou imagem: o resultado é `INCONCLUSIVA`.
    imagem: ImagemCapturada | None


class FontePosicao(Protocol):
    async def analisar_posicao(self) -> LeituraPosicao: ...
