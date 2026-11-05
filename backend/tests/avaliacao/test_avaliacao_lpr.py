"""Avaliação do LPR sem câmera (spec 005 §6.4; RNF-012, P-7, P-8).

- `test_avalia_conjunto_de_referencia` usa o EasyOCR real sobre o acervo e é
  marcado `avaliacao`: fica fora da execução padrão e só roda com
  `pytest -m avaliacao`, com a configuração abaixo. O acervo e o gabarito ficam
  **fora do repositório** (§12.1): contêm placas.
- Os demais testes verificam o gabarito e as métricas, sem OCR, e rodam sempre.

Sem meta numérica, a avaliação não reprova nada: mede e relata. O relatório
traz só nomes de arquivo, nunca placas (RNF-013).

Configuração (nomes de exemplo; os finais saem na spec de configuração):
`PESAGEM_LPR_PASTA_AVALIACAO`, `PESAGEM_LPR_PASTA_MODELOS`,
`PESAGEM_LPR_IDIOMAS` (separados por vírgula), `PESAGEM_LPR_LIMIAR_CONFIANCA`,
`PESAGEM_LPR_LIMIAR_BORDAS_INFERIOR`, `PESAGEM_LPR_LIMIAR_BORDAS_SUPERIOR`,
`PESAGEM_LPR_AREA_MINIMA_PX`, `PESAGEM_LPR_PROPORCAO_MINIMA`,
`PESAGEM_LPR_PROPORCAO_MAXIMA` e `PESAGEM_LPR_MAXIMO_ROIS`.
"""

import asyncio
import csv
import os
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path, PurePosixPath

import cv2
import numpy as np
import pytest

from pesagem.dominio.placa.normalizacao import PlacaNormalizada, normalizar_placa
from pesagem.dominio.placa.selecao import (
    CandidatoPlaca,
    MotivoRejeicaoLeituraPlaca,
    ParametrosLeituraPlaca,
    PlacaSelecionada,
    RejeicaoLeituraPlaca,
    selecionar_placa,
)
from pesagem.lpr.erros import ErroLpr
from pesagem.lpr.fontes.interface import FalhaImagem, ImagemCapturada, MotivoFalhaImagem
from pesagem.lpr.fontes.pasta_imagens import EXTENSOES
from pesagem.lpr.leitor_placa import LeitorPlaca
from pesagem.lpr.localizacao import ParametrosLocalizacao
from pesagem.lpr.pipeline import reconhecer_placa
from pesagem.lpr.resultado import FalhaLeitor, LeituraPlaca

CABECALHO = ["arquivo", "placa_esperada", "observacao"]


class ErroGabaritoInvalido(ErroLpr):
    """O gabarito não serve: a avaliação para e não produz métricas."""


class ResultadoAvaliacao(StrEnum):
    # Ordem do relatório: a aceitação incorreta vem primeiro (§6.4).
    ACEITACAO_INCORRETA = "ACEITACAO_INCORRETA"
    ACERTO = "ACERTO"
    REJEICAO_SEGURA = "REJEICAO_SEGURA"
    REJEICAO_CORRETA = "REJEICAO_CORRETA"


@dataclass(frozen=True)
class LinhaGabarito:
    arquivo: str
    # `None`: a imagem não tem placa legível e o esperado é a rejeição.
    placa_esperada: str | None


def ler_gabarito(pasta: Path) -> tuple[LinhaGabarito, ...]:
    arquivo_gabarito = pasta / "gabarito.csv"
    try:
        with arquivo_gabarito.open(encoding="utf-8", newline="") as entrada:
            linhas = list(csv.reader(entrada))
    except (OSError, UnicodeDecodeError) as erro:
        raise ErroGabaritoInvalido(f"gabarito ilegível: {erro}") from erro
    if not linhas or linhas[0] != CABECALHO:
        raise ErroGabaritoInvalido(f"cabeçalho deve ser {','.join(CABECALHO)}")

    resultado: list[LinhaGabarito] = []
    vistos: set[str] = set()
    for numero, colunas in enumerate(linhas[1:], start=2):
        if len(colunas) != len(CABECALHO):
            raise ErroGabaritoInvalido(f"linha {numero}: número de colunas")
        arquivo, placa, _observacao = colunas
        if arquivo in vistos:
            raise ErroGabaritoInvalido(f"linha {numero}: arquivo repetido")
        if not (pasta / arquivo).is_file():
            raise ErroGabaritoInvalido(f"linha {numero}: arquivo inexistente")
        vistos.add(arquivo)
        if placa:
            normalizada = normalizar_placa(placa)
            if not (
                isinstance(normalizada, PlacaNormalizada)
                and normalizada.placa_normalizada == placa
            ):
                # Sem a placa na mensagem: só a linha (RNF-013).
                raise ErroGabaritoInvalido(f"linha {numero}: placa esperada inválida")
        resultado.append(LinhaGabarito(arquivo, placa or None))

    imagens = {
        imagem.relative_to(pasta).as_posix()
        for imagem in pasta.rglob("*")
        if imagem.is_file() and imagem.suffix.lower() in EXTENSOES
    }
    fora = imagens - vistos
    if fora:
        raise ErroGabaritoInvalido(f"imagens fora do gabarito: {len(fora)}")
    return tuple(resultado)


def classificar(
    placa_esperada: str | None,
    selecao: PlacaSelecionada | RejeicaoLeituraPlaca,
) -> ResultadoAvaliacao:
    """Compara pela chave de comparação (spec 003 §5.2)."""
    if isinstance(selecao, RejeicaoLeituraPlaca):
        if placa_esperada is None:
            return ResultadoAvaliacao.REJEICAO_CORRETA
        return ResultadoAvaliacao.REJEICAO_SEGURA
    if placa_esperada is None:
        return ResultadoAvaliacao.ACEITACAO_INCORRETA
    esperada = normalizar_placa(placa_esperada)
    assert isinstance(esperada, PlacaNormalizada)  # garantido por `ler_gabarito`
    if esperada.chave_comparacao == selecao.placa.chave_comparacao:
        return ResultadoAvaliacao.ACERTO
    return ResultadoAvaliacao.ACEITACAO_INCORRETA


def montar_relatorio(
    resultados: Sequence[tuple[str, ResultadoAvaliacao]],
    limiar: Decimal,
    latencias_ms: Sequence[float],
) -> str:
    """Contagem e taxa por resultado, no total e por subpasta; sem placas."""
    grupos: dict[str, list[ResultadoAvaliacao]] = {"total": []}
    for arquivo, resultado in resultados:
        grupos["total"].append(resultado)
        subpasta = str(PurePosixPath(arquivo).parent)
        grupos.setdefault(subpasta, []).append(resultado)

    linhas = [f"limiar de confiança: {limiar}"]
    if latencias_ms:
        media = sum(latencias_ms) / len(latencias_ms)
        linhas.append(
            f"latência por imagem: média {media:.0f} ms, máxima {max(latencias_ms):.0f} ms"
        )
    for grupo, itens in grupos.items():
        contagem = Counter(itens)
        linhas.append(f"[{grupo}] imagens: {len(itens)}")
        for tipo in ResultadoAvaliacao:
            taxa = contagem[tipo] / len(itens) if itens else 0.0
            linhas.append(f"  {tipo}: {contagem[tipo]} ({taxa:.1%})")
    return "\n".join(linhas)


# --- Gabarito e métricas (sem OCR; rodam sempre) -----------------------------


def gravar_imagem(arquivo: Path) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(arquivo), np.full((10, 10, 3), 127, np.uint8))


def preparar_pasta(pasta: Path, conteudo: str, imagens: Sequence[str]) -> None:
    for imagem in imagens:
        gravar_imagem(pasta / imagem)
    (pasta / "gabarito.csv").write_text(conteudo, encoding="utf-8")


def test_le_gabarito_valido(tmp_path: Path) -> None:
    """CA-019."""
    preparar_pasta(
        tmp_path,
        "arquivo,placa_esperada,observacao\n"
        "diurno/img-0001.jpg,ABC1D23,\n"
        "noturno/img-0002.png,,sem placa legível\n",
        ["diurno/img-0001.jpg", "noturno/img-0002.png"],
    )
    assert ler_gabarito(tmp_path) == (
        LinhaGabarito("diurno/img-0001.jpg", "ABC1D23"),
        LinhaGabarito("noturno/img-0002.png", None),
    )


@pytest.mark.parametrize(
    ("conteudo", "imagens"),
    [
        ("arquivo,placa\nimg-0001.png,ABC1D23\n", ["img-0001.png"]),
        ("", []),
        (
            "arquivo,placa_esperada,observacao\nimg-0001.png,ABC1D23,\n"
            "img-0001.png,ABC1D23,\n",
            ["img-0001.png"],
        ),
        ("arquivo,placa_esperada,observacao\nimg-0009.png,ABC1D23,\n", []),
        (
            "arquivo,placa_esperada,observacao\nimg-0001.png,ABC1D23,\n",
            ["img-0001.png", "img-0002.png"],
        ),
        ("arquivo,placa_esperada,observacao\nimg-0001.png,ABC12,\n", ["img-0001.png"]),
        # Esperada precisa estar já normalizada: `abc-1d23` não serve.
        (
            "arquivo,placa_esperada,observacao\nimg-0001.png,abc-1d23,\n",
            ["img-0001.png"],
        ),
        ("arquivo,placa_esperada,observacao\nimg-0001.png,ABC1D23\n", ["img-0001.png"]),
    ],
)
def test_gabarito_invalido_levanta_erro(
    tmp_path: Path, conteudo: str, imagens: list[str]
) -> None:
    """CA-019."""
    preparar_pasta(tmp_path, conteudo, imagens)
    with pytest.raises(ErroGabaritoInvalido):
        ler_gabarito(tmp_path)


def test_gabarito_ausente_levanta_erro(tmp_path: Path) -> None:
    """CA-019."""
    with pytest.raises(ErroGabaritoInvalido):
        ler_gabarito(tmp_path)


def test_mensagem_de_gabarito_invalido_nao_contem_a_placa(tmp_path: Path) -> None:
    """RNF-013."""
    preparar_pasta(
        tmp_path,
        "arquivo,placa_esperada,observacao\nimg-0001.png,QQQ1QQQ,\n",
        ["img-0001.png"],
    )
    with pytest.raises(ErroGabaritoInvalido) as erro:
        ler_gabarito(tmp_path)
    assert "QQQ1QQQ" not in str(erro.value)


def selecionada(placa: str) -> PlacaSelecionada:
    normalizada = normalizar_placa(placa)
    assert isinstance(normalizada, PlacaNormalizada)
    return PlacaSelecionada(normalizada, Decimal("0.900"), 0)


REJEICAO = RejeicaoLeituraPlaca(MotivoRejeicaoLeituraPlaca.CONFIANCA_BAIXA)


@pytest.mark.parametrize(
    ("esperada", "selecao", "resultado"),
    [
        ("ABC1D23", selecionada("ABC1D23"), ResultadoAvaliacao.ACERTO),
        ("ABC1234", selecionada("ABC1C34"), ResultadoAvaliacao.ACERTO),
        ("ABC1D23", selecionada("ABC1D24"), ResultadoAvaliacao.ACEITACAO_INCORRETA),
        (None, selecionada("ABC1D23"), ResultadoAvaliacao.ACEITACAO_INCORRETA),
        ("ABC1D23", REJEICAO, ResultadoAvaliacao.REJEICAO_SEGURA),
        (None, REJEICAO, ResultadoAvaliacao.REJEICAO_CORRETA),
    ],
)
def test_classifica_pela_chave_de_comparacao(
    esperada: str | None,
    selecao: PlacaSelecionada | RejeicaoLeituraPlaca,
    resultado: ResultadoAvaliacao,
) -> None:
    """CA-020."""
    assert classificar(esperada, selecao) is resultado


def test_relatorio_por_subpasta_comeca_pela_aceitacao_incorreta() -> None:
    """CA-020 (§6.4)."""
    relatorio = montar_relatorio(
        [
            ("diurno/img-0001.jpg", ResultadoAvaliacao.ACERTO),
            ("diurno/img-0002.jpg", ResultadoAvaliacao.ACEITACAO_INCORRETA),
            ("noturno/img-0003.jpg", ResultadoAvaliacao.REJEICAO_SEGURA),
        ],
        Decimal("0.800"),
        [100.0, 300.0],
    )
    linhas = relatorio.splitlines()
    assert linhas[0] == "limiar de confiança: 0.800"
    assert linhas[1] == "latência por imagem: média 200 ms, máxima 300 ms"
    assert linhas[2] == "[total] imagens: 3"
    assert linhas[3] == "  ACEITACAO_INCORRETA: 1 (33.3%)"
    assert "[diurno] imagens: 2" in linhas
    assert "  ACEITACAO_INCORRETA: 1 (50.0%)" in linhas
    assert "[noturno] imagens: 1" in linhas


def test_relatorio_nao_contem_placas() -> None:
    """CA-020 (RNF-013): o relatório só recebe nomes de arquivo e resultados."""
    relatorio = montar_relatorio(
        [("img-0001.jpg", classificar("ABC1D23", selecionada("ABC1D23")))],
        Decimal("0.800"),
        [],
    )
    assert "ABC1D23" not in relatorio
    assert "latência" not in relatorio


# --- Avaliação real (EasyOCR; só com `pytest -m avaliacao`) -------------------


class FonteArquivo:
    """Uma imagem do acervo como `FonteImagem`."""

    def __init__(self, pasta: Path, arquivo: str) -> None:
        self._pasta = pasta
        self._arquivo = arquivo

    async def obter_imagem(self) -> ImagemCapturada | FalhaImagem:
        pixels = cv2.imread(str(self._pasta / self._arquivo))
        if pixels is None or pixels.size == 0:
            return FalhaImagem(MotivoFalhaImagem.IMAGEM_INVALIDA, self._arquivo)
        return ImagemCapturada(pixels, datetime.now(UTC), self._arquivo)


def configuracao(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        pytest.fail(f"avaliação sem configuração: defina {nome}")
    return valor


def avaliar_imagem(
    pasta: Path,
    linha: LinhaGabarito,
    leitor: LeitorPlaca,
    localizacao: ParametrosLocalizacao,
    parametros: ParametrosLeituraPlaca,
) -> ResultadoAvaliacao:
    fonte = FonteArquivo(pasta, linha.arquivo)
    leitura = asyncio.run(reconhecer_placa(fonte, leitor, localizacao))
    if isinstance(leitura, (FalhaImagem, FalhaLeitor)):
        # Falha não autoriza: conta como rejeição.
        return classificar(linha.placa_esperada, REJEICAO)
    assert isinstance(leitura, LeituraPlaca)
    candidatos = [
        CandidatoPlaca(texto.texto, texto.confianca)
        for leitura_roi in leitura.leituras
        for texto in leitura_roi.textos
    ]
    return classificar(linha.placa_esperada, selecionar_placa(candidatos, parametros))


@pytest.mark.avaliacao
def test_avalia_conjunto_de_referencia() -> None:
    """§6.4: mede e relata; sem meta numérica, não reprova."""
    from pesagem.lpr.leitor_easyocr import LeitorEasyOcr

    pasta = Path(configuracao("PESAGEM_LPR_PASTA_AVALIACAO"))
    linhas = ler_gabarito(pasta)
    leitor = LeitorEasyOcr(
        Path(configuracao("PESAGEM_LPR_PASTA_MODELOS")),
        configuracao("PESAGEM_LPR_IDIOMAS").split(","),
    )
    limiar = Decimal(configuracao("PESAGEM_LPR_LIMIAR_CONFIANCA"))
    parametros = ParametrosLeituraPlaca(limiar)
    localizacao = ParametrosLocalizacao(
        float(configuracao("PESAGEM_LPR_LIMIAR_BORDAS_INFERIOR")),
        float(configuracao("PESAGEM_LPR_LIMIAR_BORDAS_SUPERIOR")),
        int(configuracao("PESAGEM_LPR_AREA_MINIMA_PX")),
        float(configuracao("PESAGEM_LPR_PROPORCAO_MINIMA")),
        float(configuracao("PESAGEM_LPR_PROPORCAO_MAXIMA")),
        int(configuracao("PESAGEM_LPR_MAXIMO_ROIS")),
    )

    resultados: list[tuple[str, ResultadoAvaliacao]] = []
    latencias_ms: list[float] = []
    for linha in linhas:
        inicio = time.perf_counter()
        resultado = avaliar_imagem(pasta, linha, leitor, localizacao, parametros)
        latencias_ms.append((time.perf_counter() - inicio) * 1000)
        resultados.append((linha.arquivo, resultado))

    print("\n" + montar_relatorio(resultados, limiar, latencias_ms))
