"""Segunda tentativa da leitura da balança (spec 004 §6.2, P-9).

Só `SEM_RESPOSTA` é repetido, porque a balança pode demorar para estabilizar.
`QUADRO_CORROMPIDO` e `DESCONECTADA` não são repetidos.
"""

from collections.abc import Awaitable, Callable

from pesagem.dispositivos.balanca.interface import (
    FalhaBalanca,
    LeituraBalanca,
    MotivoFalhaBalanca,
    PesoRecebido,
)

MAXIMO_TENTATIVAS = 2


async def ler_com_segunda_tentativa(
    tentar: Callable[[], Awaitable[PesoRecebido | MotivoFalhaBalanca]],
    esperar_intervalo: Callable[[], Awaitable[None]],
) -> LeituraBalanca | FalhaBalanca:
    tentativa = 1
    while True:
        resultado = await tentar()
        if isinstance(resultado, PesoRecebido):
            return LeituraBalanca(resultado.peso_kg, resultado.lida_em, tentativa)
        if (
            resultado is not MotivoFalhaBalanca.SEM_RESPOSTA
            or tentativa == MAXIMO_TENTATIVAS
        ):
            return FalhaBalanca(resultado, tentativa)
        await esperar_intervalo()
        tentativa += 1
