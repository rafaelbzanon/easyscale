"""Comando explícito que baixa os modelos do EasyOCR (spec 005, P-10; D-08).

Uso: `python -m pesagem.lpr.baixar_modelos <pasta> <idioma> [<idioma>...]`.
É o único ponto com download habilitado; a operação usa `LeitorEasyOcr`, que
nunca baixa nada.
"""

import sys
from pathlib import Path

import easyocr  # type: ignore[import-untyped]


def baixar_modelos(pasta: Path, idiomas: list[str]) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    easyocr.Reader(
        idiomas,
        gpu=False,
        model_storage_directory=str(pasta),
        user_network_directory=str(pasta),
        download_enabled=True,
    )


def main(argumentos: list[str]) -> int:
    if len(argumentos) < 2:
        print(
            "uso: python -m pesagem.lpr.baixar_modelos <pasta> <idioma> [...]",
            file=sys.stderr,
        )
        return 2
    baixar_modelos(Path(argumentos[0]), argumentos[1:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
