"""Fonte de imagem por pasta (spec 005 §6.1; RF-006, RNF-012).

A lista de arquivos é fixada na criação e percorrida uma vez, em ordem de
nome. No fim, devolve sempre `SEM_IMAGEM`: voltar ao começo faria a mesma
placa "chegar" de novo sem ninguém perceber (P-6).
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import cv2

from pesagem.lpr.erros import ErroConfiguracaoLpr
from pesagem.lpr.fontes.interface import (
    FalhaImagem,
    ImagemCapturada,
    MotivoFalhaImagem,
)

EXTENSOES = frozenset({".jpg", ".jpeg", ".png"})


class FontePastaImagens:
    def __init__(self, pasta: Path, relogio: Callable[[], datetime]) -> None:
        if not pasta.is_dir():
            raise ErroConfiguracaoLpr(f"pasta de imagens inexistente: {pasta}")
        self._pasta = pasta
        self._relogio = relogio
        self._arquivos = sorted(
            arquivo.name
            for arquivo in pasta.iterdir()
            if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES
        )
        self._proximo = 0

    async def obter_imagem(self) -> ImagemCapturada | FalhaImagem:
        if not self._pasta.is_dir():
            return FalhaImagem(MotivoFalhaImagem.FONTE_INDISPONIVEL, None)
        if self._proximo >= len(self._arquivos):
            return FalhaImagem(MotivoFalhaImagem.SEM_IMAGEM, None)
        nome = self._arquivos[self._proximo]
        self._proximo += 1
        # Leitura de arquivo é I/O: fora do laço de eventos (RNF-011).
        pixels = await asyncio.to_thread(cv2.imread, str(self._pasta / nome))
        if pixels is None or pixels.size == 0:
            return FalhaImagem(MotivoFalhaImagem.IMAGEM_INVALIDA, nome)
        return ImagemCapturada(pixels, self._relogio(), nome)
