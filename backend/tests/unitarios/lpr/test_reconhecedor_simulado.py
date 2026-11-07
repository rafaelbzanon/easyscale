"""Reconhecedor simulado e codificação JPEG (spec 015 §5.3)."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import numpy as np

from pesagem.lpr.codificacao import codificar_jpeg
from pesagem.lpr.fontes.interface import FalhaImagem, MotivoFalhaImagem
from pesagem.lpr.reconhecedor_simulado import (
    ReconhecedorPlacaSimulado,
    imagem_sintetica,
)
from pesagem.lpr.resultado import FalhaLeitor, LeituraPlaca, TextoOcr

AGORA = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)


def test_fila_vazia_e_sem_imagem_e_textos_viram_uma_roi() -> None:
    reconhecedor = ReconhecedorPlacaSimulado(lambda: AGORA)
    assert asyncio.run(reconhecedor.reconhecer()) == FalhaImagem(
        MotivoFalhaImagem.SEM_IMAGEM, None
    )
    reconhecedor.enfileirar([TextoOcr("ABC1234", 0.98765), TextoOcr("BRASIL", 0.5)])
    assert reconhecedor.tamanho_fila() == 1
    leitura = asyncio.run(reconhecedor.reconhecer())
    assert isinstance(leitura, LeituraPlaca)
    (roi,) = leitura.leituras
    assert [t.texto for t in roi.textos] == ["ABC1234", "BRASIL"]
    assert roi.textos[0].confianca == Decimal("0.987")
    assert leitura.capturada_em == AGORA


def test_confianca_invalida_e_falhas_enfileiradas() -> None:
    reconhecedor = ReconhecedorPlacaSimulado(lambda: AGORA)
    reconhecedor.enfileirar([TextoOcr("ABC1234", 1.5)])
    reconhecedor.enfileirar(FalhaLeitor("x"))
    assert isinstance(asyncio.run(reconhecedor.reconhecer()), FalhaLeitor)
    assert asyncio.run(reconhecedor.reconhecer()) == FalhaLeitor("x")


def test_codificar_jpeg_devolve_bytes_ou_none() -> None:
    conteudo = codificar_jpeg(imagem_sintetica())
    assert conteudo is not None and conteudo[:2] == b"\xff\xd8"
    assert codificar_jpeg(np.zeros((0, 0, 3), dtype=np.uint8)) is None


def test_imagem_da_leitura_tem_a_placa_dentro_da_roi() -> None:
    """A ROI fica dentro da cena e cobre a placa desenhada (diagnóstico, spec 011)."""
    reconhecedor = ReconhecedorPlacaSimulado(lambda: AGORA)
    reconhecedor.enfileirar([TextoOcr("RTX4B72", 0.97)])
    leitura = asyncio.run(reconhecedor.reconhecer())
    assert isinstance(leitura, LeituraPlaca)
    (lida,) = leitura.leituras
    altura, largura = leitura.pixels.shape[:2]
    roi = lida.roi
    assert 0 <= roi.x and roi.x + roi.largura <= largura
    assert 0 <= roi.y and roi.y + roi.altura <= altura
    recorte = leitura.pixels[roi.y : roi.y + roi.altura, roi.x : roi.x + roi.largura]
    assert recorte.mean() > leitura.pixels.mean()  # a placa clara se destaca do fundo
    assert codificar_jpeg(leitura.pixels) is not None
