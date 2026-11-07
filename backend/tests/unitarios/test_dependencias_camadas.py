"""Regras de dependência entre camadas (`CONVENCOES.md` P-4 a P-6).

Spec 001 (esqueleto-backend), CA-001 e CA-005; spec 004 (camada-dispositivos),
CA-016; spec 005 (pipeline-lpr), CA-021; spec 014 (persistencia), CA-017. Os imports são lidos com
`ast`, sem executar o código analisado; imports dinâmicos (`importlib`) não
são detectados.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

RAIZ_SRC = Path(__file__).resolve().parents[2] / "src"

CAMADAS_PROIBIDAS_NO_DOMINIO = (
    "pesagem.api",
    "pesagem.orquestracao",
    "pesagem.lpr",
    "pesagem.dispositivos",
    "pesagem.persistencia",
)
BIBLIOTECAS_PROIBIDAS_NO_DOMINIO = ("fastapi", "serial", "cv2", "easyocr")
# Spec 004, P-6: a camada de dispositivos tem tipos próprios.
CAMADAS_PROIBIDAS_EM_DISPOSITIVOS = ("pesagem.dominio",)
# Spec 005, CA-021: o LPR também tem tipos próprios; a orquestração converte.
CAMADAS_PROIBIDAS_NO_LPR = ("pesagem.dominio",)
# Biblioteca -> única camada que pode importá-la (P-6).
BIBLIOTECAS_RESTRITAS = {
    "serial": "pesagem.dispositivos",
    "cv2": "pesagem.lpr",
    "easyocr": "pesagem.lpr",
    # Spec 014, CA-017: o banco só é acessado pela persistência.
    "sqlalchemy": "pesagem.persistencia",
    "psycopg": "pesagem.persistencia",
    "alembic": "pesagem.persistencia",
}


@dataclass(frozen=True)
class Violacao:
    arquivo: Path
    importado: str
    regra: str


def pertence(nome: str, prefixo: str) -> bool:
    return nome == prefixo or nome.startswith(prefixo + ".")


def nome_modulo(raiz: Path, arquivo: Path) -> str:
    partes = arquivo.relative_to(raiz).with_suffix("").parts
    if partes[-1] == "__init__":
        partes = partes[:-1]
    return ".".join(partes)


def imports_do_arquivo(raiz: Path, arquivo: Path) -> set[str]:
    """Nomes absolutos importados pelo arquivo, com imports relativos resolvidos.

    Um arquivo que não pode ser analisado gera erro: nunca é ignorado.
    """
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    modulo = nome_modulo(raiz, arquivo)
    pacote = modulo if arquivo.name == "__init__.py" else modulo.rpartition(".")[0]
    importados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            if no.level == 0:
                base = no.module or ""
            else:
                partes = pacote.split(".")
                partes = partes[: len(partes) - (no.level - 1)]
                if no.module:
                    partes.append(no.module)
                base = ".".join(partes)
            importados.add(base)
            # `from pesagem import api` importa o submódulo `pesagem.api`.
            importados.update(f"{base}.{alias.name}" for alias in no.names)
    return importados


def verificar_camadas(raiz: Path) -> list[Violacao]:
    arquivos = sorted((raiz / "pesagem").rglob("*.py"))
    if not arquivos:
        raise ValueError(f"nenhum arquivo .py em {raiz / 'pesagem'}")
    violacoes: list[Violacao] = []
    for arquivo in arquivos:
        modulo = nome_modulo(raiz, arquivo)
        for importado in sorted(imports_do_arquivo(raiz, arquivo)):
            if pertence(modulo, "pesagem.dominio"):
                for proibido in (
                    *CAMADAS_PROIBIDAS_NO_DOMINIO,
                    *BIBLIOTECAS_PROIBIDAS_NO_DOMINIO,
                ):
                    if pertence(importado, proibido):
                        violacoes.append(Violacao(arquivo, importado, "P-4"))
            if pertence(modulo, "pesagem.dispositivos"):
                for proibido in CAMADAS_PROIBIDAS_EM_DISPOSITIVOS:
                    if pertence(importado, proibido):
                        violacoes.append(Violacao(arquivo, importado, "P-4"))
            if pertence(modulo, "pesagem.lpr"):
                for proibido in CAMADAS_PROIBIDAS_NO_LPR:
                    if pertence(importado, proibido):
                        violacoes.append(Violacao(arquivo, importado, "P-4"))
            for biblioteca, camada in BIBLIOTECAS_RESTRITAS.items():
                if pertence(importado, biblioteca) and not pertence(modulo, camada):
                    violacoes.append(Violacao(arquivo, importado, "P-6"))
    return violacoes


def criar_arquivo(raiz: Path, relativo: str, conteudo: str) -> None:
    arquivo = raiz / relativo
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(conteudo, encoding="utf-8")


def test_codigo_real_respeita_regras_de_camada() -> None:
    """CA-001."""
    violacoes = verificar_camadas(RAIZ_SRC)
    assert violacoes == [], "\n".join(
        f"{v.regra}: {v.arquivo} importa {v.importado}" for v in violacoes
    )


@pytest.mark.parametrize(
    ("relativo", "conteudo", "importado", "regra"),
    [
        ("pesagem/dominio/regra.py", "import fastapi\n", "fastapi", "P-4"),
        ("pesagem/dominio/regra.py", "from cv2 import imread\n", "cv2", "P-4"),
        ("pesagem/dominio/regra.py", "import easyocr\n", "easyocr", "P-4"),
        (
            "pesagem/dominio/regra.py",
            "from pesagem.persistencia import repositorios\n",
            "pesagem.persistencia",
            "P-4",
        ),
        (
            "pesagem/dominio/placa/regra.py",
            "from ...api import x\n",
            "pesagem.api",
            "P-4",
        ),
        ("pesagem/dominio/regra.py", "from pesagem import lpr\n", "pesagem.lpr", "P-4"),
        ("pesagem/api/rotas.py", "import serial\n", "serial", "P-6"),
        ("pesagem/orquestracao/fluxo.py", "import cv2\n", "cv2", "P-6"),
        ("pesagem/dispositivos/camera.py", "import easyocr\n", "easyocr", "P-6"),
        (
            "pesagem/orquestracao/fluxo.py",
            "from sqlalchemy import text\n",
            "sqlalchemy",
            "P-6",
        ),
        ("pesagem/api/rotas.py", "import psycopg\n", "psycopg", "P-6"),
        (
            "pesagem/dispositivos/balanca/simulada.py",
            "from pesagem.dominio.pesagem import aceitacao_peso\n",
            "pesagem.dominio.pesagem",
            "P-4",
        ),
        (
            "pesagem/dispositivos/cancela/simulada.py",
            "from ...dominio import erros\n",
            "pesagem.dominio",
            "P-4",
        ),
        (
            "pesagem/lpr/pipeline.py",
            "from pesagem.dominio.placa import selecao\n",
            "pesagem.dominio.placa",
            "P-4",
        ),
        (
            "pesagem/lpr/fontes/pasta_imagens.py",
            "from ...dominio import erros\n",
            "pesagem.dominio",
            "P-4",
        ),
    ],
)
def test_detecta_import_proibido(
    tmp_path: Path, relativo: str, conteudo: str, importado: str, regra: str
) -> None:
    """CA-005."""
    criar_arquivo(tmp_path, relativo, conteudo)
    violacoes = verificar_camadas(tmp_path)
    assert Violacao(tmp_path / relativo, importado, regra) in violacoes


@pytest.mark.parametrize(
    ("relativo", "conteudo"),
    [
        ("pesagem/dispositivos/balanca/serial.py", "import serial\n"),
        ("pesagem/lpr/leitor_easyocr.py", "import cv2\nimport easyocr\n"),
        (
            "pesagem/persistencia/banco.py",
            "from sqlalchemy import text\nimport psycopg\n",
        ),
        ("pesagem/dispositivos/balanca/interface.py", "from . import serial\n"),
        ("pesagem/dominio/operacao/maquina.py", "from ..erros import ErroDominio\n"),
    ],
)
def test_aceita_import_permitido(tmp_path: Path, relativo: str, conteudo: str) -> None:
    """CA-005: as regras não acusam imports permitidos."""
    criar_arquivo(tmp_path, relativo, conteudo)
    assert verificar_camadas(tmp_path) == []


def test_falha_com_arquivo_que_nao_pode_ser_analisado(tmp_path: Path) -> None:
    """CA-005."""
    criar_arquivo(tmp_path, "pesagem/dominio/quebrado.py", "def x(:\n")
    with pytest.raises(SyntaxError) as erro:
        verificar_camadas(tmp_path)
    assert erro.value.filename is not None
    assert erro.value.filename.endswith("quebrado.py")


def test_falha_quando_nao_ha_arquivos_python(tmp_path: Path) -> None:
    """CA-005."""
    (tmp_path / "pesagem").mkdir()
    with pytest.raises(ValueError, match="nenhum arquivo .py"):
        verificar_camadas(tmp_path)


def test_so_a_balanca_serial_importa_serial() -> None:
    """Spec 004, CA-016; spec 029, CA-011: simuladores, interfaces e protocolos
    não abrem porta; só `dispositivos/balanca/serial.py` importa `serial`."""
    dispositivos = RAIZ_SRC / "pesagem" / "dispositivos"
    arquivos = [
        arquivo
        for arquivo in sorted(dispositivos.rglob("*.py"))
        if arquivo != dispositivos / "balanca" / "serial.py"
    ]
    assert arquivos
    for arquivo in arquivos:
        importados = imports_do_arquivo(RAIZ_SRC, arquivo)
        assert not any(pertence(nome, "serial") for nome in importados), arquivo


def test_leitor_simulado_nunca_importa_easyocr() -> None:
    """Spec 005, CA-021: o pipeline é testável sem o EasyOCR."""
    lpr = RAIZ_SRC / "pesagem" / "lpr"
    for nome in ("leitor_simulado.py", "pipeline.py", "leitor_placa.py"):
        importados = imports_do_arquivo(RAIZ_SRC, lpr / nome)
        assert not any(pertence(n, "easyocr") for n in importados), nome


def test_orquestracao_nao_importa_bibliotecas_de_outras_camadas() -> None:
    """Spec 015, CA-025: OpenCV, EasyOCR, serial e FastAPI ficam nas suas camadas."""
    orquestracao = RAIZ_SRC / "pesagem" / "orquestracao"
    arquivos = sorted(orquestracao.rglob("*.py"))
    assert arquivos
    for arquivo in arquivos:
        importados = imports_do_arquivo(RAIZ_SRC, arquivo)
        for proibido in ("cv2", "easyocr", "serial", "fastapi", "pesagem.api"):
            assert not any(pertence(n, proibido) for n in importados), (
                arquivo,
                proibido,
            )
