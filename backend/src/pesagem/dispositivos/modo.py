"""Escolha do modo e das implementações (spec 004 §5.3, §6.4; RNF-003).

`SIMULADO` é o padrão. `REAL` precisa ser escrito exatamente assim e, enquanto
não houver implementação real (P-3), impede a partida: nunca cai para o
simulado em silêncio.
"""

from collections.abc import Callable, Mapping
from enum import StrEnum

from pesagem.dispositivos.balanca.interface import Balanca, ProtocoloBalanca
from pesagem.dispositivos.cancela.interface import Cancela
from pesagem.dispositivos.erros import (
    ErroConfiguracaoDispositivo,
    ErroModoIndisponivel,
)


class ModoDispositivo(StrEnum):
    SIMULADO = "SIMULADO"
    REAL = "REAL"


def selecionar_modo(valor: str | None) -> ModoDispositivo:
    if not valor:
        return ModoDispositivo.SIMULADO
    # Comparação exata: "real" ou " REAL" não são aceitos como um modo parecido.
    for modo in ModoDispositivo:
        if valor == modo.value:
            return modo
    raise ErroConfiguracaoDispositivo(f"modo de dispositivo inválido: {valor!r}")


def criar_balanca(
    modo: ModoDispositivo,
    nome_protocolo: str | None,
    protocolos: Mapping[str, ProtocoloBalanca],
    criar_simulada: Callable[[], Balanca],
) -> Balanca:
    if modo is ModoDispositivo.SIMULADO:
        return criar_simulada()
    if not nome_protocolo or nome_protocolo not in protocolos:
        raise ErroConfiguracaoDispositivo(
            f"protocolo de balança ausente ou desconhecido: {nome_protocolo!r}"
        )
    raise ErroModoIndisponivel("balança real ainda não implementada")


def criar_cancela(
    modo: ModoDispositivo, criar_simulada: Callable[[], Cancela]
) -> Cancela:
    if modo is ModoDispositivo.SIMULADO:
        return criar_simulada()
    raise ErroModoIndisponivel("cancela real ainda não implementada")
