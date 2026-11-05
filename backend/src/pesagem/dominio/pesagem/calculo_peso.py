"""Cálculo e classificação do peso líquido (spec 002 §6.2; RN-006).

O valor devolvido é sempre o calculado: nunca é trocado por zero, nem dentro
da tolerância (RN-004). O negativo fora da tolerância não é aceito e vai para
o administrador (RN-016).
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from pesagem.dominio.erros import ErroParametrosInvalidos, ErroTipoOperacaoInvalido


class TipoOperacao(StrEnum):
    CARGA = "CARGA"
    DESCARGA = "DESCARGA"


class ClassificacaoPesoLiquido(StrEnum):
    COM_MOVIMENTACAO = "COM_MOVIMENTACAO"
    SEM_MOVIMENTACAO = "SEM_MOVIMENTACAO"
    NEGATIVO_FORA_TOLERANCIA = "NEGATIVO_FORA_TOLERANCIA"


@dataclass(frozen=True)
class ParametrosPesoLiquido:
    """Validados ao criar, junto com a configuração: um erro aparece na
    partida do sistema, e não com o caminhão já pesado duas vezes."""

    tolerancia_movimentacao_kg: Decimal

    def __post_init__(self) -> None:
        tolerancia = self.tolerancia_movimentacao_kg
        if not tolerancia.is_finite() or tolerancia < 0:
            raise ErroParametrosInvalidos("tolerancia_movimentacao_kg inválida")


@dataclass(frozen=True)
class ResultadoPesoLiquido:
    peso_liquido_kg: Decimal
    classificacao: ClassificacaoPesoLiquido


def calcular_peso_liquido(
    tipo_operacao: TipoOperacao,
    peso_inicial_kg: Decimal,
    peso_final_kg: Decimal,
    parametros: ParametrosPesoLiquido,
) -> ResultadoPesoLiquido:
    if tipo_operacao is TipoOperacao.CARGA:
        peso_liquido_kg = peso_final_kg - peso_inicial_kg
    elif tipo_operacao is TipoOperacao.DESCARGA:
        peso_liquido_kg = peso_inicial_kg - peso_final_kg
    else:
        raise ErroTipoOperacaoInvalido(repr(tipo_operacao))

    tolerancia_movimentacao_kg = parametros.tolerancia_movimentacao_kg
    if peso_liquido_kg > tolerancia_movimentacao_kg:
        classificacao = ClassificacaoPesoLiquido.COM_MOVIMENTACAO
    elif peso_liquido_kg >= -tolerancia_movimentacao_kg:
        classificacao = ClassificacaoPesoLiquido.SEM_MOVIMENTACAO
    else:
        classificacao = ClassificacaoPesoLiquido.NEGATIVO_FORA_TOLERANCIA
    return ResultadoPesoLiquido(peso_liquido_kg, classificacao)
