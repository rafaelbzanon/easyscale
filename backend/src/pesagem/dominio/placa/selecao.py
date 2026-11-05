"""Seleção da placa entre os textos lidos (spec 005 §6.3; RN-002, RN-003).

Na dúvida, rejeita: uma segunda placa válida, mesmo abaixo do limiar, é
ambiguidade, e a mesma placa lida mais de uma vez vale pela menor confiança
(P-5). Nunca escolhe automaticamente entre placas diferentes.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from pesagem.dominio.erros import ErroParametrosInvalidos
from pesagem.dominio.placa.normalizacao import PlacaNormalizada, normalizar_placa


class MotivoRejeicaoLeituraPlaca(StrEnum):
    SEM_CANDIDATO = "SEM_CANDIDATO"
    PLACA_INVALIDA = "PLACA_INVALIDA"
    AMBIGUA = "AMBIGUA"
    CONFIANCA_BAIXA = "CONFIANCA_BAIXA"


@dataclass(frozen=True)
class CandidatoPlaca:
    placa_lida: str
    confianca: Decimal


@dataclass(frozen=True)
class ParametrosLeituraPlaca:
    limiar_confianca: Decimal

    def __post_init__(self) -> None:
        limiar = self.limiar_confianca
        if not limiar.is_finite() or not 0 < limiar <= 1:
            raise ErroParametrosInvalidos(
                f"limiar de confiança deve ser maior que 0 e no máximo 1: {limiar}"
            )


@dataclass(frozen=True)
class PlacaSelecionada:
    placa: PlacaNormalizada
    confianca: Decimal
    # Posição do candidato na entrada, para o diagnóstico apontar a ROI.
    indice: int


@dataclass(frozen=True)
class RejeicaoLeituraPlaca:
    motivo: MotivoRejeicaoLeituraPlaca


def selecionar_placa(
    candidatos: Sequence[CandidatoPlaca], parametros: ParametrosLeituraPlaca
) -> PlacaSelecionada | RejeicaoLeituraPlaca:
    """Aplica as regras da spec §6.3, nesta ordem."""
    if not candidatos:
        return RejeicaoLeituraPlaca(MotivoRejeicaoLeituraPlaca.SEM_CANDIDATO)

    validos: list[PlacaSelecionada] = []
    for indice, candidato in enumerate(candidatos):
        placa = normalizar_placa(candidato.placa_lida)
        if isinstance(placa, PlacaNormalizada):
            validos.append(PlacaSelecionada(placa, candidato.confianca, indice))
    if not validos:
        return RejeicaoLeituraPlaca(MotivoRejeicaoLeituraPlaca.PLACA_INVALIDA)

    chaves = {valido.placa.chave_comparacao for valido in validos}
    if len(chaves) > 1:
        return RejeicaoLeituraPlaca(MotivoRejeicaoLeituraPlaca.AMBIGUA)

    # `min` devolve o primeiro em caso de empate (ordem de entrada).
    selecionada = min(validos, key=lambda valido: valido.confianca)
    if selecionada.confianca < parametros.limiar_confianca:
        return RejeicaoLeituraPlaca(MotivoRejeicaoLeituraPlaca.CONFIANCA_BAIXA)
    return selecionada
