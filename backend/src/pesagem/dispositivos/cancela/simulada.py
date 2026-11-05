"""Cancela simulada para testes e demonstração (spec 004 §6.3).

Guarda uma posição física simulada, que o sensor simulado informa, e a lista
dos comandos enviados. Não faz I/O e não espera tempo real.
"""

from enum import StrEnum

from pesagem.dispositivos.cancela.interface import (
    ComandoCancela,
    EstadoCancela,
    ResultadoComandoCancela,
    RetornoEnvio,
)
from pesagem.dispositivos.cancela.tentativas import (
    POSICAO_PEDIDA,
    comandar_com_segunda_tentativa,
)
from pesagem.dispositivos.erros import ErroConfiguracaoDispositivo


class CenarioCancela(StrEnum):
    CONFIRMADO = "CONFIRMADO"
    CONFIRMADO_NA_SEGUNDA = "CONFIRMADO_NA_SEGUNDA"
    NAO_MOVE = "NAO_MOVE"
    FALHA = "FALHA"
    # A cancela se move, mas o sensor não responde: o estado é desconhecido.
    SENSOR_SEM_RESPOSTA = "SENSOR_SEM_RESPOSTA"


class CancelaSimulada:
    def __init__(self, cenario: CenarioCancela, posicao_inicial: EstadoCancela) -> None:
        if posicao_inicial is EstadoCancela.DESCONHECIDO:
            raise ErroConfiguracaoDispositivo(
                "posição inicial simulada deve ser ABERTA ou FECHADA"
            )
        self._posicao: EstadoCancela = posicao_inicial
        self._cenario = cenario
        self._envios_no_comando = 0
        self.comandos_enviados: list[ComandoCancela] = []

    def definir_cenario(self, cenario: CenarioCancela) -> None:
        self._cenario = cenario

    async def abrir(self) -> ResultadoComandoCancela:
        return await self._comandar(ComandoCancela.ABRIR)

    async def fechar(self) -> ResultadoComandoCancela:
        return await self._comandar(ComandoCancela.FECHAR)

    async def consultar_estado(self) -> EstadoCancela:
        if self._cenario is CenarioCancela.SENSOR_SEM_RESPOSTA:
            return EstadoCancela.DESCONHECIDO
        return self._posicao

    async def _comandar(self, comando: ComandoCancela) -> ResultadoComandoCancela:
        self._envios_no_comando = 0
        return await comandar_com_segunda_tentativa(
            comando,
            self.consultar_estado,
            self._enviar,
            self._aguardar_posicao,
            _sem_espera,
        )

    async def _enviar(self, comando: ComandoCancela) -> RetornoEnvio:
        self.comandos_enviados.append(comando)
        self._envios_no_comando += 1
        cenario = self._cenario
        if cenario is CenarioCancela.FALHA:
            return RetornoEnvio.FALHA_INFORMADA
        move = cenario in (
            CenarioCancela.CONFIRMADO,
            CenarioCancela.SENSOR_SEM_RESPOSTA,
        ) or (
            cenario is CenarioCancela.CONFIRMADO_NA_SEGUNDA
            and self._envios_no_comando == 2
        )
        if move:
            self._posicao = POSICAO_PEDIDA[comando]
        return RetornoEnvio.ENVIADO

    async def _aguardar_posicao(self, pedida: EstadoCancela) -> EstadoCancela:
        return await self.consultar_estado()


async def _sem_espera() -> None:
    """O simulador não espera o intervalo entre tentativas (§6.3)."""
