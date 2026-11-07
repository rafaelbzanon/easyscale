"""Reconhecedor de placa simulado (spec 015 §5.3).

Entrega uma `LeituraPlaca` com imagem sintética e os textos enfileirados, para
os testes e para o controle dos simuladores (contrato 011). Sem fila, devolve
`SEM_IMAGEM`: nada a analisar.
"""

from collections import deque
from collections.abc import Callable, Sequence
from datetime import datetime

import cv2
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


# Cena sintética da câmera de identificação: fundo neutro com uma placa no
# formato Mercosul desenhada com o texto simulado. Só para o diagnóstico
# mostrar a ROI sobre algo legível; não passa pelo OCR.
LARGURA_CENA_PX, ALTURA_CENA_PX = 640, 360
ROI_PLACA = Roi(200, 200, 240, 80)


def imagem_placa_sintetica(texto: str) -> MatLike:
    """Cena sintética com a placa simulada desenhada na ROI_PLACA."""
    cena = np.full((ALTURA_CENA_PX, LARGURA_CENA_PX, 3), 96, dtype=np.uint8)
    x, y, w, h = ROI_PLACA.x, ROI_PLACA.y, ROI_PLACA.largura, ROI_PLACA.altura
    cv2.rectangle(cena, (x, y), (x + w, y + h), (245, 245, 245), -1)
    cv2.rectangle(cena, (x, y), (x + w, y + 18), (153, 51, 0), -1)  # faixa azul (BGR)
    cv2.putText(
        cena,
        "BRASIL",
        (x + 92, y + 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (255, 255, 255),
        1,
    )
    cv2.rectangle(cena, (x, y), (x + w, y + h), (30, 30, 30), 2)
    cv2.putText(
        cena, texto[:7], (x + 14, y + 68), cv2.FONT_HERSHEY_DUPLEX, 1.5, (20, 20, 20), 2
    )
    return cena


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
        texto_desenhado = textos[0].texto if textos else ""
        return LeituraPlaca(
            ORIGEM,
            self._relogio(),
            imagem_placa_sintetica(texto_desenhado),
            (LeituraRoi(ROI_PLACA, tuple(textos)),),
        )
