"""Leitor de placa com EasyOCR (spec 005 §5.2; P-10, D-08, D-09).

Roda só em CPU e nunca baixa modelos: sem eles, a criação falha. O download é
feito antes, por comando explícito (`baixar_modelos`). Não usa `allowlist`:
forçar A–Z e 0–9 trocaria um caractere estranho por um "parecido" e poderia
criar uma placa válida errada.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import easyocr  # type: ignore[import-untyped]
from cv2.typing import MatLike

from pesagem.lpr.erros import ErroConfiguracaoLpr
from pesagem.lpr.resultado import TextoOcr


class LeitorEasyOcr:
    def __init__(self, pasta_modelos: Path, idiomas: Sequence[str]) -> None:
        if not idiomas:
            raise ErroConfiguracaoLpr("lista de idiomas do OCR vazia")
        try:
            self._leitor: Any = easyocr.Reader(
                list(idiomas),
                gpu=False,
                model_storage_directory=str(pasta_modelos),
                # Sem isto, o EasyOCR cria `~/.EasyOCR/user_network` no usuário.
                user_network_directory=str(pasta_modelos),
                download_enabled=False,
                verbose=False,
            )
        except (FileNotFoundError, ValueError) as erro:
            raise ErroConfiguracaoLpr(
                f"modelos do OCR indisponíveis em {pasta_modelos}: {erro}"
            ) from erro

    def ler(self, recorte: MatLike) -> Sequence[TextoOcr]:
        # Com `detail=1`, cada item é (caixa, texto, confiança).
        return tuple(
            TextoOcr(str(texto), float(confianca))
            for _caixa, texto, confianca in self._leitor.readtext(recorte, detail=1)
        )
