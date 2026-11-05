"""Testes do leitor EasyOCR sem modelos e sem rede (spec 005 §7; P-10, D-08).

Não leem placas: a leitura real só é exercitada na avaliação (P-8).
"""

from pathlib import Path

import pytest

from pesagem.lpr.baixar_modelos import main
from pesagem.lpr.erros import ErroConfiguracaoLpr
from pesagem.lpr.leitor_easyocr import LeitorEasyOcr


def test_sem_modelos_levanta_erro_e_nao_baixa(tmp_path: Path) -> None:
    """§7: modelos ausentes impedem a partida; nada é baixado."""
    with pytest.raises(ErroConfiguracaoLpr, match="modelos do OCR"):
        LeitorEasyOcr(tmp_path, ["en"])
    assert not any(tmp_path.rglob("*.pth"))


def test_lista_de_idiomas_vazia_levanta_erro(tmp_path: Path) -> None:
    """§5.2: os idiomas vêm de configuração, sem padrão no código."""
    with pytest.raises(ErroConfiguracaoLpr, match="idiomas"):
        LeitorEasyOcr(tmp_path, [])


def test_idioma_desconhecido_levanta_erro(tmp_path: Path) -> None:
    """§5.2."""
    with pytest.raises(ErroConfiguracaoLpr):
        LeitorEasyOcr(tmp_path, ["idioma-inexistente"])


def test_comando_de_download_sem_argumentos_nao_baixa(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """P-10: o comando explícito exige pasta e idioma."""
    assert main([]) == 2
    assert main(["pasta"]) == 2
    assert "uso:" in capsys.readouterr().err
