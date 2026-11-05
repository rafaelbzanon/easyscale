"""Testes da fonte por pasta de imagens (spec 005 §6.1; RF-006, RNF-012)."""

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from pesagem.lpr.erros import ErroConfiguracaoLpr
from pesagem.lpr.fontes.interface import (
    FalhaImagem,
    ImagemCapturada,
    MotivoFalhaImagem,
)
from pesagem.lpr.fontes.pasta_imagens import FontePastaImagens

INSTANTE = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)


def relogio() -> datetime:
    return INSTANTE


def gravar_imagem(arquivo: Path) -> None:
    imagem = np.full((20, 30, 3), 127, np.uint8)
    assert cv2.imwrite(str(arquivo), imagem)


def obter(fonte: FontePastaImagens) -> ImagemCapturada | FalhaImagem:
    return asyncio.run(fonte.obter_imagem())


def origem(resultado: ImagemCapturada | FalhaImagem) -> str | None:
    return resultado.origem


def test_lista_so_imagens_em_ordem_de_nome(tmp_path: Path) -> None:
    """CA-001."""
    for nome in ("b.png", "a.JPG", "c.jpeg"):
        gravar_imagem(tmp_path / nome)
    (tmp_path / "d.txt").write_text("não é imagem", encoding="utf-8")
    (tmp_path / "subpasta").mkdir()
    gravar_imagem(tmp_path / "subpasta" / "0.png")

    fonte = FontePastaImagens(tmp_path, relogio)

    resultados = [obter(fonte) for _ in range(3)]
    assert all(isinstance(r, ImagemCapturada) for r in resultados)
    assert [origem(r) for r in resultados] == ["a.JPG", "b.png", "c.jpeg"]
    assert obter(fonte) == FalhaImagem(MotivoFalhaImagem.SEM_IMAGEM, None)


def test_fim_da_pasta_nao_volta_ao_comeco(tmp_path: Path) -> None:
    """CA-002 (P-6)."""
    gravar_imagem(tmp_path / "img-0001.png")
    fonte = FontePastaImagens(tmp_path, relogio)
    assert isinstance(obter(fonte), ImagemCapturada)
    for _ in range(3):
        assert obter(fonte) == FalhaImagem(MotivoFalhaImagem.SEM_IMAGEM, None)


def test_arquivo_invalido_e_informado_e_a_fonte_segue(tmp_path: Path) -> None:
    """CA-003."""
    (tmp_path / "img-0001.jpg").write_bytes(b"isto nao e um jpeg")
    (tmp_path / "img-0002.png").write_bytes(b"")
    gravar_imagem(tmp_path / "img-0003.png")
    fonte = FontePastaImagens(tmp_path, relogio)

    assert obter(fonte) == FalhaImagem(
        MotivoFalhaImagem.IMAGEM_INVALIDA, "img-0001.jpg"
    )
    assert obter(fonte) == FalhaImagem(
        MotivoFalhaImagem.IMAGEM_INVALIDA, "img-0002.png"
    )
    assert origem(obter(fonte)) == "img-0003.png"


def test_pasta_inexistente_na_criacao_levanta_erro(tmp_path: Path) -> None:
    """CA-004."""
    with pytest.raises(ErroConfiguracaoLpr):
        FontePastaImagens(tmp_path / "nao-existe", relogio)


def test_arquivo_no_lugar_da_pasta_levanta_erro(tmp_path: Path) -> None:
    """CA-004."""
    arquivo = tmp_path / "arquivo.png"
    gravar_imagem(arquivo)
    with pytest.raises(ErroConfiguracaoLpr):
        FontePastaImagens(arquivo, relogio)


def test_pasta_removida_depois_da_criacao(tmp_path: Path) -> None:
    """CA-004."""
    pasta = tmp_path / "imagens"
    pasta.mkdir()
    gravar_imagem(pasta / "img-0001.png")
    fonte = FontePastaImagens(pasta, relogio)
    shutil.rmtree(pasta)
    assert obter(fonte) == FalhaImagem(MotivoFalhaImagem.FONTE_INDISPONIVEL, None)


def test_imagem_traz_instante_do_relogio_e_nome_do_arquivo(tmp_path: Path) -> None:
    """CA-005."""
    gravar_imagem(tmp_path / "img-0001.png")
    resultado = obter(FontePastaImagens(tmp_path, relogio))
    assert isinstance(resultado, ImagemCapturada)
    assert resultado.capturada_em == INSTANTE
    assert resultado.capturada_em.utcoffset() is not None
    assert resultado.origem == "img-0001.png"
    assert resultado.pixels.shape == (20, 30, 3)


def test_pasta_vazia_devolve_sem_imagem(tmp_path: Path) -> None:
    """§6.1."""
    fonte = FontePastaImagens(tmp_path, relogio)
    assert obter(fonte) == FalhaImagem(MotivoFalhaImagem.SEM_IMAGEM, None)
