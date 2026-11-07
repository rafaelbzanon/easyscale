"""Codificação da imagem de uma decisão para a persistência (RN-022).

Só o `lpr` importa o OpenCV (P-6). Imagem que não codifica devolve `None`, e a
orquestração a trata como `FALHA_IMAGEM` (spec 015 §6.1).
"""

import cv2
from cv2.typing import MatLike


def codificar_jpeg(pixels: MatLike) -> bytes | None:
    try:
        sucesso, dados = cv2.imencode(".jpg", pixels)
    except cv2.error:
        return None
    return dados.tobytes() if sucesso else None
