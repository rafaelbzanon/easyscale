"""Aceitação de peso a partir das leituras da balança (spec 002 §6.1; RN-004).

A estabilidade é decidida só pelo software (P-1) e o peso aceito é a última
leitura da série estável, sem média nem arredondamento (P-2). Na dúvida,
rejeita (RNF-009); uma rejeição nunca traz peso.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise

from pesagem.dominio.erros import ErroParametrosInvalidos


class MotivoRejeicaoPeso(StrEnum):
    LEITURA_INVALIDA = "LEITURA_INVALIDA"
    FORA_DE_FAIXA = "FORA_DE_FAIXA"
    LEITURAS_INSUFICIENTES = "LEITURAS_INSUFICIENTES"
    INSTAVEL = "INSTAVEL"
    FORA_DE_ORDEM = "FORA_DE_ORDEM"


@dataclass(frozen=True)
class LeituraPeso:
    peso_kg: Decimal
    lida_em: datetime


@dataclass(frozen=True)
class ParametrosAceitacaoPeso:
    """Parâmetros vindos de configuração, sem valor padrão (P-3)."""

    peso_minimo_kg: Decimal
    peso_maximo_kg: Decimal
    quantidade_leituras_estaveis: int
    variacao_maxima_kg: Decimal
    janela_estabilidade_ms: int

    def __post_init__(self) -> None:
        # Valores não finitos são recusados antes das comparações: com NaN a
        # comparação levantaria `InvalidOperation`, e um máximo infinito
        # desligaria o limite superior sem ninguém perceber.
        decimais = (self.peso_minimo_kg, self.peso_maximo_kg, self.variacao_maxima_kg)
        if not all(valor.is_finite() for valor in decimais):
            raise ErroParametrosInvalidos("parâmetro de peso não finito")
        if self.peso_minimo_kg < 0:
            raise ErroParametrosInvalidos("peso_minimo_kg < 0")
        if self.peso_minimo_kg >= self.peso_maximo_kg:
            raise ErroParametrosInvalidos("peso_minimo_kg >= peso_maximo_kg")
        if self.quantidade_leituras_estaveis < 2:
            raise ErroParametrosInvalidos("quantidade_leituras_estaveis < 2")
        if self.variacao_maxima_kg < 0:
            raise ErroParametrosInvalidos("variacao_maxima_kg < 0")
        if self.janela_estabilidade_ms <= 0:
            raise ErroParametrosInvalidos("janela_estabilidade_ms <= 0")


@dataclass(frozen=True)
class PesoAceito:
    peso_kg: Decimal
    lida_em: datetime


@dataclass(frozen=True)
class RejeicaoPeso:
    motivo: MotivoRejeicaoPeso


def validar_leituras_peso(
    leituras: Sequence[LeituraPeso], parametros: ParametrosAceitacaoPeso
) -> PesoAceito | RejeicaoPeso:
    """Avalia as leituras em ordem cronológica; motivos na ordem da spec §7."""
    quantidade = parametros.quantidade_leituras_estaveis
    if len(leituras) < quantidade:
        return RejeicaoPeso(MotivoRejeicaoPeso.LEITURAS_INSUFICIENTES)
    # Todas as leituras recebidas são analisadas: uma inválida nunca é
    # descartada em silêncio para a regra seguir com as outras.
    if not all(_e_valida(leitura) for leitura in leituras):
        return RejeicaoPeso(MotivoRejeicaoPeso.LEITURA_INVALIDA)
    if any(a.lida_em >= b.lida_em for a, b in pairwise(leituras)):
        return RejeicaoPeso(MotivoRejeicaoPeso.FORA_DE_ORDEM)

    serie = leituras[-quantidade:]
    janela = timedelta(milliseconds=parametros.janela_estabilidade_ms)
    if serie[-1].lida_em - serie[0].lida_em > janela:
        return RejeicaoPeso(MotivoRejeicaoPeso.INSTAVEL)
    pesos = [leitura.peso_kg for leitura in serie]
    if max(pesos) - min(pesos) > parametros.variacao_maxima_kg:
        return RejeicaoPeso(MotivoRejeicaoPeso.INSTAVEL)
    if not all(
        parametros.peso_minimo_kg <= peso <= parametros.peso_maximo_kg for peso in pesos
    ):
        return RejeicaoPeso(MotivoRejeicaoPeso.FORA_DE_FAIXA)

    ultima = serie[-1]
    return PesoAceito(ultima.peso_kg, ultima.lida_em)


def _e_valida(leitura: LeituraPeso) -> bool:
    return leitura.peso_kg.is_finite() and leitura.lida_em.utcoffset() is not None
