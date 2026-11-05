"""Pré-processamento da imagem para a localização (spec 005 §6.2, passo 2)."""

import cv2
from cv2.typing import MatLike


def detectar_bordas(
    pixels: MatLike, limiar_inferior: float, limiar_superior: float
) -> MatLike:
    """Tons de cinza e bordas (Canny). Aceita imagem colorida ou já em cinza."""
    cinza = pixels if pixels.ndim == 2 else cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(cinza, limiar_inferior, limiar_superior)
