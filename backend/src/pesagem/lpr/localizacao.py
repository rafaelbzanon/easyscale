"""Localização das ROIs candidatas com OpenCV (spec 005 §6.2; P-1, RF-007).

Os valores dos parâmetros não têm padrão no código: vêm de configuração e são
calibrados com o conjunto de avaliação.
"""

import math
from dataclasses import dataclass

import cv2
from cv2.typing import MatLike

from pesagem.lpr.erros import ErroConfiguracaoLpr
from pesagem.lpr.preprocessamento import detectar_bordas
from pesagem.lpr.resultado import Roi


@dataclass(frozen=True)
class ParametrosLocalizacao:
    limiar_bordas_inferior: float
    limiar_bordas_superior: float
    area_minima_px: int
    # Largura ÷ altura do retângulo envolvente.
    proporcao_minima: float
    proporcao_maxima: float
    maximo_rois: int

    def __post_init__(self) -> None:
        numeros = (
            self.limiar_bordas_inferior,
            self.limiar_bordas_superior,
            self.proporcao_minima,
            self.proporcao_maxima,
        )
        if not all(math.isfinite(numero) for numero in numeros):
            raise ErroConfiguracaoLpr("parâmetros de localização não finitos")
        if not 0 <= self.limiar_bordas_inferior < self.limiar_bordas_superior:
            raise ErroConfiguracaoLpr("limiares de borda incoerentes")
        if self.area_minima_px <= 0:
            raise ErroConfiguracaoLpr("área mínima deve ser positiva")
        if not 0 < self.proporcao_minima < self.proporcao_maxima:
            raise ErroConfiguracaoLpr("proporções incoerentes")
        if self.maximo_rois < 1:
            raise ErroConfiguracaoLpr("máximo de ROIs deve ser ao menos 1")


def localizar_placas(
    pixels: MatLike, parametros: ParametrosLocalizacao
) -> tuple[Roi, ...]:
    bordas = detectar_bordas(
        pixels, parametros.limiar_bordas_inferior, parametros.limiar_bordas_superior
    )
    contornos, _ = cv2.findContours(bordas, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidatas: set[Roi] = set()
    for contorno in contornos:
        x, y, largura, altura = cv2.boundingRect(contorno)
        if largura * altura < parametros.area_minima_px:
            continue
        proporcao = largura / altura
        if parametros.proporcao_minima <= proporcao <= parametros.proporcao_maxima:
            candidatas.add(Roi(x, y, largura, altura))
    # Maior área primeiro; posição como desempate, para a ordem ser determinística.
    ordenadas = sorted(
        candidatas, key=lambda roi: (-roi.largura * roi.altura, roi.y, roi.x)
    )
    return tuple(ordenadas[: parametros.maximo_rois])
