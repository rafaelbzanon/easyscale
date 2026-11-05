"""Resultado estruturado do pipeline (spec 005 §5.2; RF-022).

Guarda tudo o que foi lido, inclusive o que a seleção vai descartar, para a
tela de diagnóstico mostrar as interpretações do algoritmo.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from cv2.typing import MatLike


@dataclass(frozen=True)
class Roi:
    x: int
    y: int
    largura: int
    altura: int


@dataclass(frozen=True)
class TextoOcr:
    """Saída bruta do OCR: entrada não confiável, validada pelo pipeline."""

    texto: str
    confianca: float


@dataclass(frozen=True)
class TextoLido:
    texto: str
    # De 0 a 1, com 3 casas, truncada para baixo (P-3).
    confianca: Decimal


@dataclass(frozen=True)
class LeituraRoi:
    roi: Roi
    textos: tuple[TextoLido, ...]


# `eq=False`: comparar matrizes do OpenCV com `==` não devolve um booleano.
@dataclass(frozen=True, eq=False)
class LeituraPlaca:
    origem: str
    capturada_em: datetime
    # Só em memória: guardar a evidência depende da Q-08 e da D-13.
    pixels: MatLike
    leituras: tuple[LeituraRoi, ...]


@dataclass(frozen=True)
class FalhaLeitor:
    origem: str
