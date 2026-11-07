"""Configuração e distribuição de eventos (spec 015; CA-022, CA-023)."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from pesagem.orquestracao.configuracao import ConfiguracaoOrquestracao
from pesagem.orquestracao.erros import ErroConfiguracaoOrquestracao
from pesagem.orquestracao.eventos import (
    TAMANHO_FILA,
    DistribuidorEventos,
    Evento,
    EventoPesoLido,
)

VALIDA = ConfiguracaoOrquestracao(UTC, 100, 2000, 100, 60_000, 60_000, 60_000, 500)


@pytest.mark.parametrize(
    "campo", [c for c in VALIDA.__dataclass_fields__ if c != "fuso_patio"]
)
@pytest.mark.parametrize("valor", [0, -1])
def test_recusa_valor_nao_positivo(campo: str, valor: int) -> None:
    """CA-023."""
    with pytest.raises(ErroConfiguracaoOrquestracao, match=campo):
        replace(VALIDA, **{campo: valor})  # type: ignore[arg-type]


def test_assinante_lento_perde_eventos_sem_travar() -> None:
    """CA-022."""
    distribuidor = DistribuidorEventos()
    fila = distribuidor.assinar()
    evento = EventoPesoLido(Decimal("1"), datetime(2026, 11, 7, tzinfo=UTC))
    for _ in range(TAMANHO_FILA + 5):
        distribuidor.publicar(evento)
    assert fila.qsize() == TAMANHO_FILA
    distribuidor.cancelar(fila)
    distribuidor.publicar(evento)
    assert fila.qsize() == TAMANHO_FILA
    assert asyncio.run(_ler(fila)) == evento


async def _ler(fila: asyncio.Queue[Evento]) -> Evento:
    return await fila.get()
