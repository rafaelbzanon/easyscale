"""Pipeline de LPR: imagem → ROIs → OCR (spec 005 §6.2).

Não normaliza, não aplica limiar e não decide: isso é do domínio e da
orquestração. A confiança do OCR é entrada não confiável: fora de [0, 1] ou
não finita, a imagem inteira é descartada, nunca "corrigida".
"""

import asyncio
import logging
import math
from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal

from pesagem.lpr.fontes.interface import FalhaImagem, FonteImagem, ImagemCapturada
from pesagem.lpr.leitor_placa import LeitorPlaca
from pesagem.lpr.localizacao import ParametrosLocalizacao, localizar_placas
from pesagem.lpr.resultado import (
    FalhaLeitor,
    LeituraPlaca,
    LeituraRoi,
    TextoLido,
    TextoOcr,
)

CASAS_CONFIANCA = Decimal("0.001")

registro = logging.getLogger(__name__)


async def reconhecer_placa(
    fonte: FonteImagem, leitor: LeitorPlaca, parametros: ParametrosLocalizacao
) -> LeituraPlaca | FalhaImagem | FalhaLeitor:
    imagem = await fonte.obter_imagem()
    if isinstance(imagem, FalhaImagem):
        return imagem
    # Localização e OCR são trabalho de CPU: fora do laço de eventos (P-9).
    return await asyncio.to_thread(_reconhecer, imagem, leitor, parametros)


def converter_confianca(confianca: float) -> Decimal | None:
    """De 0 a 1 com 3 casas, truncada para baixo; `None` se inválida (P-3)."""
    if not math.isfinite(confianca) or not 0 <= confianca <= 1:
        return None
    # Pelo texto, e não pelo valor binário: `Decimal(0.3)` é 0.29999…, e o
    # truncamento o levaria a 0.299.
    return Decimal(repr(float(confianca))).quantize(CASAS_CONFIANCA, ROUND_DOWN)


def _reconhecer(
    imagem: ImagemCapturada, leitor: LeitorPlaca, parametros: ParametrosLocalizacao
) -> LeituraPlaca | FalhaLeitor:
    leituras: list[LeituraRoi] = []
    for roi in localizar_placas(imagem.pixels, parametros):
        recorte = imagem.pixels[roi.y : roi.y + roi.altura, roi.x : roi.x + roi.largura]
        try:
            textos_ocr = leitor.ler(recorte)
        except Exception as erro:
            # Exceção de biblioteca de terceiros vira resultado tratado; o log
            # leva só o tipo do erro, sem imagem nem texto (RNF-013).
            registro.warning(
                "falha do leitor de placa em %s: %s",
                imagem.origem,
                type(erro).__name__,
            )
            return FalhaLeitor(imagem.origem)
        textos = _validar_textos(textos_ocr)
        if textos is None:
            registro.warning(
                "leitor de placa devolveu confiança inválida em %s", imagem.origem
            )
            return FalhaLeitor(imagem.origem)
        leituras.append(LeituraRoi(roi, textos))
    return LeituraPlaca(
        imagem.origem, imagem.capturada_em, imagem.pixels, tuple(leituras)
    )


def _validar_textos(textos_ocr: Sequence[TextoOcr]) -> tuple[TextoLido, ...] | None:
    textos: list[TextoLido] = []
    for texto_ocr in textos_ocr:
        confianca = converter_confianca(texto_ocr.confianca)
        if confianca is None:
            return None
        textos.append(TextoLido(texto_ocr.texto, confianca))
    return tuple(textos)
