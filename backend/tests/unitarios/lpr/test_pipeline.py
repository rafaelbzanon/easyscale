"""Testes do pipeline com o leitor simulado (spec 005 §6.2, §7, §8).

Usam OpenCV, mas não o EasyOCR: o pipeline e o OCR são testados em separado
(`AMBIENTE.md` §14.3).
"""

import asyncio
import logging
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import cv2
import numpy as np
import pytest
from cv2.typing import MatLike

from pesagem.lpr.fontes.interface import (
    FalhaImagem,
    ImagemCapturada,
    MotivoFalhaImagem,
)
from pesagem.lpr.fontes.pasta_imagens import FontePastaImagens
from pesagem.lpr.leitor_simulado import LeitorPlacaSimulado
from pesagem.lpr.localizacao import ParametrosLocalizacao, localizar_placas
from pesagem.lpr.pipeline import converter_confianca, reconhecer_placa
from pesagem.lpr.resultado import FalhaLeitor, LeituraPlaca, TextoLido, TextoOcr

PARAMETROS = ParametrosLocalizacao(50, 150, 2000, 2.0, 6.0, 5)
INSTANTE = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)


class FonteFixa:
    """Dublê de `FonteImagem` que devolve um resultado fixo."""

    def __init__(self, resultado: ImagemCapturada | FalhaImagem) -> None:
        self._resultado = resultado

    async def obter_imagem(self) -> ImagemCapturada | FalhaImagem:
        return self._resultado


def imagem_com_duas_placas() -> MatLike:
    imagem = np.full((480, 640, 3), 100, np.uint8)
    cv2.rectangle(imagem, (20, 20), (219, 79), (255,) * 3, -1)
    cv2.rectangle(imagem, (20, 300), (339, 389), (255,) * 3, -1)
    return imagem


def capturada(pixels: MatLike) -> FonteFixa:
    return FonteFixa(ImagemCapturada(pixels, INSTANTE, "img-0001.png"))


def reconhecer(
    fonte: FonteFixa | FontePastaImagens, leitor: LeitorPlacaSimulado
) -> LeituraPlaca | FalhaImagem | FalhaLeitor:
    return asyncio.run(reconhecer_placa(fonte, leitor, PARAMETROS))


def test_cada_roi_vai_ao_leitor_e_cada_texto_e_candidato_separado() -> None:
    """CA-008 (P-2)."""
    pixels = imagem_com_duas_placas()
    rois = localizar_placas(pixels, PARAMETROS)
    respostas = [
        [TextoOcr("BRASIL", 0.99), TextoOcr("ABC1D23", 0.9)],
        [TextoOcr("XYZ9876", 0.5)],
    ]
    respostas.extend([] for _ in rois[2:])
    leitor = LeitorPlacaSimulado(respostas)

    resultado = reconhecer(capturada(pixels), leitor)

    assert isinstance(resultado, LeituraPlaca)
    assert resultado.origem == "img-0001.png"
    assert resultado.capturada_em == INSTANTE
    assert resultado.pixels is pixels
    assert [leitura.roi for leitura in resultado.leituras] == list(rois)
    assert leitor.recortes_recebidos == [(roi.largura, roi.altura) for roi in rois]
    assert resultado.leituras[0].textos == (
        TextoLido("BRASIL", Decimal("0.990")),
        TextoLido("ABC1D23", Decimal("0.900")),
    )
    assert resultado.leituras[1].textos == (TextoLido("XYZ9876", Decimal("0.500")),)


def test_sem_roi_o_leitor_nao_e_chamado() -> None:
    """CA-007."""
    leitor = LeitorPlacaSimulado([[TextoOcr("ABC1D23", 0.9)]])
    resultado = reconhecer(capturada(np.full((480, 640, 3), 100, np.uint8)), leitor)
    assert isinstance(resultado, LeituraPlaca)
    assert resultado.leituras == ()
    assert leitor.recortes_recebidos == []


@pytest.mark.parametrize("motivo", list(MotivoFalhaImagem))
def test_falha_da_fonte_e_repassada_sem_chamar_o_leitor(
    motivo: MotivoFalhaImagem,
) -> None:
    """CA-009."""
    falha = FalhaImagem(motivo, "img-0001.png")
    leitor = LeitorPlacaSimulado([[TextoOcr("ABC1D23", 0.9)]])
    assert reconhecer(FonteFixa(falha), leitor) == falha
    assert leitor.recortes_recebidos == []


def test_excecao_do_leitor_vira_falha_sem_texto_no_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CA-010 (§7: a exceção vira resultado e é registrada só pelo tipo)."""
    leitor = LeitorPlacaSimulado([RuntimeError("ABC1D23 detalhe interno")])
    with caplog.at_level(logging.WARNING):
        resultado = reconhecer(capturada(imagem_com_duas_placas()), leitor)
    assert resultado == FalhaLeitor("img-0001.png")
    assert "RuntimeError" in caplog.text
    assert "ABC1D23" not in caplog.text


@pytest.mark.parametrize("confianca", [math.nan, math.inf, -0.1, 1.01])
def test_confianca_invalida_descarta_a_imagem(
    confianca: float, caplog: pytest.LogCaptureFixture
) -> None:
    """CA-010."""
    leitor = LeitorPlacaSimulado([[TextoOcr("ABC1D23", confianca)]])
    with caplog.at_level(logging.WARNING):
        resultado = reconhecer(capturada(imagem_com_duas_placas()), leitor)
    assert resultado == FalhaLeitor("img-0001.png")
    assert "ABC1D23" not in caplog.text


@pytest.mark.parametrize(
    ("bruta", "convertida"),
    [
        (0.98765, "0.987"),
        (0.9999, "0.999"),
        (1.0, "1.000"),
        (0.3, "0.300"),
        (0.0, "0.000"),
        (1, "1.000"),
        (np.float64(0.98765), "0.987"),
    ],
)
def test_confianca_e_truncada_para_baixo(bruta: float, convertida: str) -> None:
    """CA-011 (P-3: truncar nunca aumenta a confiança)."""
    resultado = converter_confianca(bruta)
    assert resultado == Decimal(convertida)
    assert resultado is not None
    assert resultado <= Decimal(repr(float(bruta)))


def test_pipeline_com_fonte_por_pasta_nao_cria_arquivos(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """CA-022 (RNF-013): nada é gravado e o texto lido não vai para o log."""
    pasta = tmp_path / "imagens"
    pasta.mkdir()
    assert cv2.imwrite(str(pasta / "img-0001.png"), imagem_com_duas_placas())
    antes = sorted(tmp_path.rglob("*"))
    leitor = LeitorPlacaSimulado([[TextoOcr("ABC1D23", 0.9)]])

    with caplog.at_level(logging.DEBUG):
        resultado = reconhecer(FontePastaImagens(pasta, lambda: INSTANTE), leitor)

    assert isinstance(resultado, LeituraPlaca)
    assert resultado.leituras[0].textos == (TextoLido("ABC1D23", Decimal("0.900")),)
    assert sorted(tmp_path.rglob("*")) == antes
    assert "ABC1D23" not in caplog.text


def test_leitor_simulado_esgotado_nao_devolve_textos() -> None:
    """§5.2: depois da última resposta configurada, nenhum texto."""
    leitor = LeitorPlacaSimulado([])
    assert leitor.ler(np.zeros((10, 40, 3), np.uint8)) == ()
    assert leitor.recortes_recebidos == [(40, 10)]
