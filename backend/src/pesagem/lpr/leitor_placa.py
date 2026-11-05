"""Fronteira do OCR (spec 005 §5.2; `AMBIENTE.md` §9.2).

Síncrona: o OCR é trabalho de CPU, e o pipeline a chama em
`asyncio.to_thread` (P-9).
"""

from collections.abc import Sequence
from typing import Protocol

from cv2.typing import MatLike

from pesagem.lpr.resultado import TextoOcr


class LeitorPlaca(Protocol):
    def ler(self, recorte: MatLike) -> Sequence[TextoOcr]: ...
