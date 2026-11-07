"""Fonte de posição simulada (spec 015 §5.2)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from pesagem.lpr.posicao.interface import ResultadoPosicao
from pesagem.lpr.posicao.simulada import CenarioPosicao, FontePosicaoSimulada

AGORA = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize("cenario", list(CenarioPosicao))
def test_devolve_o_cenario_com_imagem_salvo_em_inconclusiva(
    cenario: CenarioPosicao,
) -> None:
    fonte = FontePosicaoSimulada(cenario, lambda: AGORA)
    leitura = asyncio.run(fonte.analisar_posicao())
    assert leitura.resultado is ResultadoPosicao[cenario.name]
    assert leitura.capturada_em == AGORA
    assert (leitura.imagem is None) is (cenario is CenarioPosicao.INCONCLUSIVA)


def test_atraso_e_troca_de_cenario() -> None:
    fonte = FontePosicaoSimulada(
        CenarioPosicao.AUSENTE, lambda: AGORA, atraso_captura_ms=1500
    )
    assert asyncio.run(fonte.analisar_posicao()).capturada_em == AGORA - timedelta(
        milliseconds=1500
    )
    fonte.definir_cenario(CenarioPosicao.CONFIRMADA)
    assert (
        asyncio.run(fonte.analisar_posicao()).resultado is ResultadoPosicao.CONFIRMADA
    )
