"""Comando de cancela com segunda tentativa guiada pelo sensor (spec 004 §6.2).

O comando só é reenviado quando o sensor responde e mostra que a cancela não
se moveu (P-10): nunca é um reenvio cego (`AGENTS.md` §7.1.4). Sem resposta do
sensor ou com falha informada pelo equipamento, não há reenvio.
"""

from collections.abc import Awaitable, Callable

from pesagem.dispositivos.cancela.interface import (
    ComandoCancela,
    EstadoCancela,
    ResultadoComando,
    ResultadoComandoCancela,
    RetornoEnvio,
)

MAXIMO_TENTATIVAS = 2

POSICAO_PEDIDA = {
    ComandoCancela.ABRIR: EstadoCancela.ABERTA,
    ComandoCancela.FECHAR: EstadoCancela.FECHADA,
}


async def comandar_com_segunda_tentativa(
    comando: ComandoCancela,
    ler_sensor: Callable[[], Awaitable[EstadoCancela]],
    enviar: Callable[[ComandoCancela], Awaitable[RetornoEnvio]],
    aguardar_posicao: Callable[[EstadoCancela], Awaitable[EstadoCancela]],
    esperar_intervalo: Callable[[], Awaitable[None]],
) -> ResultadoComandoCancela:
    """`aguardar_posicao` espera até o timeout e devolve a leitura do sensor."""
    pedida = POSICAO_PEDIDA[comando]
    if await ler_sensor() is pedida:
        return ResultadoComandoCancela(ResultadoComando.CONFIRMADO, 0)

    tentativa = 1
    while True:
        if await enviar(comando) is RetornoEnvio.FALHA_INFORMADA:
            return ResultadoComandoCancela(ResultadoComando.FALHA, tentativa)
        estado = await aguardar_posicao(pedida)
        if estado is pedida:
            return ResultadoComandoCancela(ResultadoComando.CONFIRMADO, tentativa)
        if estado is EstadoCancela.DESCONHECIDO or tentativa == MAXIMO_TENTATIVAS:
            return ResultadoComandoCancela(ResultadoComando.SEM_CONFIRMACAO, tentativa)
        await esperar_intervalo()
        tentativa += 1
