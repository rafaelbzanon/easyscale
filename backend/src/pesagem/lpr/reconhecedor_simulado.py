"""Reconhecedor de placa simulado (spec 015 §5.3).

Entrega uma `LeituraPlaca` com imagem sintética e os textos enfileirados, para
os testes e para o controle dos simuladores (contrato 011). Sem fila, devolve
`SEM_IMAGEM`: nada a analisar.
"""

from collections import deque
from collections.abc import Callable, Sequence
from datetime import datetime

import numpy as np
from cv2.typing import MatLike

from pesagem.lpr.fontes.interface import FalhaImagem, MotivoFalhaImagem
from pesagem.lpr.pipeline import converter_confianca
from pesagem.lpr.resultado import (
    FalhaLeitor,
    LeituraPlaca,
    LeituraRoi,
    Roi,
    TextoLido,
    TextoOcr,
)

ORIGEM = "placa-simulada"
LADO_IMAGEM_PX = 8


def imagem_sintetica() -> MatLike:
    """Imagem preta pequena, sem dado pessoal (`CONVENCOES.md` §9)."""
    return np.zeros((LADO_IMAGEM_PX, LADO_IMAGEM_PX, 3), dtype=np.uint8)


type RespostaSimulada = Sequence[TextoOcr] | FalhaImagem | FalhaLeitor


class ReconhecedorPlacaSimulado:
    def __init__(self, relogio: Callable[[], datetime]) -> None:
        self._relogio = relogio
        self._fila: deque[RespostaSimulada] = deque()

    def enfileirar(self, resposta: RespostaSimulada) -> None:
        self._fila.append(resposta)

    def tamanho_fila(self) -> int:
        return len(self._fila)

    async def reconhecer(self) -> LeituraPlaca | FalhaImagem | FalhaLeitor:
        if not self._fila:
            return FalhaImagem(MotivoFalhaImagem.SEM_IMAGEM, None)
        resposta = self._fila.popleft()
        if isinstance(resposta, FalhaImagem | FalhaLeitor):
            return resposta
        textos: list[TextoLido] = []
        for texto_ocr in resposta:
            confianca = converter_confianca(texto_ocr.confianca)
            if confianca is None:
                return FalhaLeitor(ORIGEM)
            textos.append(TextoLido(texto_ocr.texto, confianca))
        roi = Roi(0, 0, LADO_IMAGEM_PX, LADO_IMAGEM_PX)
        return LeituraPlaca(
            ORIGEM,
            self._relogio(),
            imagem_sintetica(),
            (LeituraRoi(roi, tuple(textos)),),
        )
