"""Testes da cancela simulada e da segunda tentativa (spec 004, `camada-dispositivos`)."""

import asyncio
from collections.abc import Callable, Coroutine

import pytest

from pesagem.dispositivos.cancela.interface import (
    Cancela,
    ComandoCancela,
    EstadoCancela,
    ResultadoComando,
    ResultadoComandoCancela,
)
from pesagem.dispositivos.cancela.simulada import CancelaSimulada, CenarioCancela
from pesagem.dispositivos.erros import ErroConfiguracaoDispositivo

ABERTA = EstadoCancela.ABERTA
FECHADA = EstadoCancela.FECHADA
DESCONHECIDO = EstadoCancela.DESCONHECIDO
ABRIR = ComandoCancela.ABRIR
FECHAR = ComandoCancela.FECHAR


def executar(
    acao: Callable[[], Coroutine[None, None, ResultadoComandoCancela]],
) -> ResultadoComandoCancela:
    return asyncio.run(acao())


def estado(cancela: Cancela) -> EstadoCancela:
    return asyncio.run(cancela.consultar_estado())


def resultado(valor: ResultadoComando, tentativas: int) -> ResultadoComandoCancela:
    return ResultadoComandoCancela(valor, tentativas)


@pytest.mark.parametrize("cenario", list(CenarioCancela))
@pytest.mark.parametrize("posicao_inicial", [ABERTA, FECHADA])
def test_estado_inicial_vem_do_sensor(
    cenario: CenarioCancela, posicao_inicial: EstadoCancela
) -> None:
    """§5.2: o estado vem sempre do sensor, nunca é suposto."""
    cancela = CancelaSimulada(cenario, posicao_inicial)
    esperado = (
        DESCONHECIDO
        if cenario is CenarioCancela.SENSOR_SEM_RESPOSTA
        else posicao_inicial
    )
    assert estado(cancela) is esperado


def test_posicao_inicial_desconhecida_e_recusada() -> None:
    """§6.3: a posição física simulada é ABERTA ou FECHADA."""
    with pytest.raises(ErroConfiguracaoDispositivo):
        CancelaSimulada(CenarioCancela.CONFIRMADO, DESCONHECIDO)


def test_confirmado_abre_e_fecha_com_um_comando() -> None:
    """CA-007."""
    cancela = CancelaSimulada(CenarioCancela.CONFIRMADO, FECHADA)
    assert executar(cancela.abrir) == resultado(ResultadoComando.CONFIRMADO, 1)
    assert estado(cancela) is ABERTA
    assert executar(cancela.fechar) == resultado(ResultadoComando.CONFIRMADO, 1)
    assert estado(cancela) is FECHADA
    assert cancela.comandos_enviados == [ABRIR, FECHAR]


def test_confirmado_na_segunda_envia_2_comandos() -> None:
    """CA-008."""
    cancela = CancelaSimulada(CenarioCancela.CONFIRMADO_NA_SEGUNDA, FECHADA)
    assert executar(cancela.abrir) == resultado(ResultadoComando.CONFIRMADO, 2)
    assert estado(cancela) is ABERTA
    assert cancela.comandos_enviados == [ABRIR, ABRIR]


def test_confirmado_na_segunda_vale_para_cada_comando() -> None:
    """CA-008: a contagem de envios recomeça a cada chamada."""
    cancela = CancelaSimulada(CenarioCancela.CONFIRMADO_NA_SEGUNDA, FECHADA)
    executar(cancela.abrir)
    assert executar(cancela.fechar) == resultado(ResultadoComando.CONFIRMADO, 2)
    assert cancela.comandos_enviados == [ABRIR, ABRIR, FECHAR, FECHAR]


def test_nao_move_reenvia_uma_vez_e_mantem_a_posicao() -> None:
    """CA-009 (P-10: o sensor funciona e mostra que a cancela não se moveu)."""
    cancela = CancelaSimulada(CenarioCancela.NAO_MOVE, FECHADA)
    assert executar(cancela.abrir) == resultado(ResultadoComando.SEM_CONFIRMACAO, 2)
    assert estado(cancela) is FECHADA
    assert cancela.comandos_enviados == [ABRIR, ABRIR]


def test_falha_informada_nao_repete() -> None:
    """CA-010."""
    cancela = CancelaSimulada(CenarioCancela.FALHA, ABERTA)
    assert executar(cancela.fechar) == resultado(ResultadoComando.FALHA, 1)
    assert estado(cancela) is ABERTA
    assert cancela.comandos_enviados == [FECHAR]


def test_sensor_sem_resposta_nao_reenvia() -> None:
    """CA-011 (P-10: reenviar sem o sensor seria cego)."""
    cancela = CancelaSimulada(CenarioCancela.SENSOR_SEM_RESPOSTA, FECHADA)
    assert executar(cancela.abrir) == resultado(ResultadoComando.SEM_CONFIRMACAO, 1)
    assert estado(cancela) is DESCONHECIDO
    assert cancela.comandos_enviados == [ABRIR]


@pytest.mark.parametrize(
    "cenario",
    [c for c in CenarioCancela if c is not CenarioCancela.SENSOR_SEM_RESPOSTA],
)
def test_sensor_ja_na_posicao_pedida_nao_envia_comando(cenario: CenarioCancela) -> None:
    """CA-012."""
    cancela = CancelaSimulada(cenario, ABERTA)
    assert executar(cancela.abrir) == resultado(ResultadoComando.CONFIRMADO, 0)
    assert cancela.comandos_enviados == []


@pytest.mark.parametrize("cenario", list(CenarioCancela))
@pytest.mark.parametrize("posicao_inicial", [ABERTA, FECHADA])
def test_nenhuma_chamada_envia_mais_de_2_comandos(
    cenario: CenarioCancela, posicao_inicial: EstadoCancela
) -> None:
    """CA-013."""
    cancela = CancelaSimulada(cenario, posicao_inicial)
    for acao in (cancela.abrir, cancela.fechar, cancela.abrir):
        antes = len(cancela.comandos_enviados)
        retorno = executar(acao)
        enviados = len(cancela.comandos_enviados) - antes
        assert enviados <= 2
        assert retorno.tentativas == enviados


def test_definir_cenario_vale_a_partir_da_chamada_seguinte() -> None:
    """CA-006 (spec §6.3)."""
    cancela = CancelaSimulada(CenarioCancela.CONFIRMADO, FECHADA)
    executar(cancela.abrir)
    cancela.definir_cenario(CenarioCancela.FALHA)
    assert executar(cancela.fechar) == resultado(ResultadoComando.FALHA, 1)


def test_simulada_satisfaz_a_interface() -> None:
    """CA-017: o mypy estrito verifica a atribuição."""
    interface: Cancela = CancelaSimulada(CenarioCancela.CONFIRMADO, FECHADA)
    assert executar(interface.abrir).resultado is ResultadoComando.CONFIRMADO
