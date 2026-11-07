"""Cria a aplicação FastAPI (ADR-0002: um único processo de servidor).

Execução: `uvicorn --factory pesagem.main:criar_aplicacao` (sem `--workers`).
Variável obrigatória ausente ou inválida impede a partida (`AMBIENTE.md` §8),
inclusive um dispositivo em `REAL`, que ainda não existe (spec 004 P-3).

Aqui também se compõe a orquestração (spec 015 §12): só simuladores por enquanto.
"""

import asyncio
import contextlib
import functools
import logging
import os
import signal
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import FastAPI, Request, Response

from pesagem.api.dependencias import Contexto, SinalCiclos, conferir_csrf
from pesagem.api.erros import registrar_tratadores
from pesagem.api.rotas import (
    agendamentos,
    autoatendimento,
    diagnostico,
    faixas_horario,
    motoristas,
    operacao,
    pesagens,
    produtos,
    sessoes,
    simuladores,
    tipos_veiculo,
    transportadoras,
    usuarios,
    veiculos,
)
from pesagem.config import Configuracao, ler_configuracao
from pesagem.dispositivos.balanca.simulada import BalancaSimulada, CenarioBalanca
from pesagem.dispositivos.cancela.interface import EstadoCancela
from pesagem.dispositivos.cancela.simulada import CancelaSimulada, CenarioCancela
from pesagem.dispositivos.erros import ErroModoIndisponivel
from pesagem.dispositivos.modo import (
    ModoDispositivo,
    criar_balanca,
    criar_cancela,
    selecionar_modo,
)
from pesagem.dominio.operacao.maquina_estados import CancelaPedida
from pesagem.dominio.pesagem.aceitacao_peso import ParametrosAceitacaoPeso
from pesagem.dominio.pesagem.calculo_peso import ParametrosPesoLiquido
from pesagem.dominio.placa.selecao import ParametrosLeituraPlaca
from pesagem.lpr.posicao.simulada import CenarioPosicao, FontePosicaoSimulada
from pesagem.lpr.reconhecedor_simulado import ReconhecedorPlacaSimulado
from pesagem.orquestracao.configuracao import ConfiguracaoOrquestracao
from pesagem.orquestracao.eventos import DistribuidorEventos
from pesagem.orquestracao.operacao import Orquestracao
from pesagem.orquestracao.simuladores import Simuladores, criar_simuladores
from pesagem.persistencia.banco import Engine, criar_engine, transacao

_log_acesso = logging.getLogger("pesagem.acesso")
_log = logging.getLogger("pesagem.main")


def _pedir_encerramento() -> None:
    # O uvicorn trata SIGTERM como desligamento limpo; separado para os testes.
    os.kill(os.getpid(), signal.SIGTERM)


def _vigiar_ciclos(sinal: SinalCiclos) -> Callable[[asyncio.Task[None]], None]:
    """Ciclos parados com a API de pé = tela com estado congelado e nenhuma leitura
    de balança, câmera ou tempo-limite. Fail-safe: marca os dispositivos como
    desconhecidos e encerra o processo; o supervisor reinicia, e a retomada da
    spec 006 §7.2 recompõe tudo a partir do banco, sem comando às cegas."""

    def ao_terminar(tarefa: asyncio.Task[None]) -> None:
        if tarefa.cancelled():
            return  # desligamento normal
        erro = tarefa.exception()
        _log.critical(
            "ciclos da orquestração terminaram (%s); encerrando o backend",
            type(erro).__name__ if erro else "sem erro",
        )
        sinal.parados = True
        _pedir_encerramento()

    return ao_terminar


_MUDAM_ESTADO = {"POST", "PUT", "PATCH", "DELETE"}


def _compor(
    configuracao: Configuracao, engine: Engine, relogio: Callable[[], datetime]
) -> tuple[Orquestracao, DistribuidorEventos, Simuladores | None]:
    """Spec 015 §12. Estado inicial seguro dos simuladores, fixo (spec 015 §6.9):
    balança sem resposta, posição ausente, cancelas fechadas que confirmam."""
    o = configuracao.operacao
    modos = [
        selecionar_modo(m) for m in (o.modo_balanca, o.modo_cancelas, o.modo_cameras)
    ]
    if modos[2] is ModoDispositivo.REAL:
        raise ErroModoIndisponivel("câmera real ainda não implementada (Q-06)")
    balanca = criar_balanca(
        modos[0],
        o.protocolo_balanca,
        o.serial_balanca,
        lambda: BalancaSimulada(CenarioBalanca.SEM_RESPOSTA, Decimal("0"), relogio),
        relogio,
    )
    cancelas = {
        pedida: CancelaSimulada(CenarioCancela.CONFIRMADO, EstadoCancela.FECHADA)
        for pedida in CancelaPedida
    }
    entrada = criar_cancela(modos[1], lambda: cancelas[CancelaPedida.ENTRADA])
    saida = criar_cancela(modos[1], lambda: cancelas[CancelaPedida.SAIDA])
    fonte_posicao = FontePosicaoSimulada(CenarioPosicao.AUSENTE, relogio)
    reconhecedor = ReconhecedorPlacaSimulado(relogio)
    distribuidor = DistribuidorEventos()
    orquestracao = Orquestracao(
        ConfiguracaoOrquestracao(
            fuso_patio=configuracao.patio_fuso,
            intervalo_analise_ms=o.intervalo_analise_ms,
            idade_maxima_imagem_ms=o.idade_maxima_imagem_ms,
            intervalo_leitura_balanca_ms=o.intervalo_leitura_balanca_ms,
            tempo_limite_posicionamento_ms=o.tempo_limite_posicionamento_ms,
            tempo_limite_pesagem_ms=o.tempo_limite_pesagem_ms,
            tempo_limite_saida_balanca_ms=o.tempo_limite_saida_balanca_ms,
            intervalo_minimo_peso_ms=o.intervalo_peso_ms,
        ),
        functools.partial(transacao, engine),
        balanca,
        entrada,
        saida,
        fonte_posicao,
        reconhecedor.reconhecer,
        ParametrosAceitacaoPeso(
            o.peso_minimo_kg,
            o.peso_maximo_kg,
            o.quantidade_leituras_estaveis,
            o.variacao_maxima_kg,
            o.janela_estabilidade_ms,
        ),
        ParametrosPesoLiquido(o.tolerancia_movimentacao_kg),
        ParametrosLeituraPlaca(o.limiar_confianca),
        distribuidor,
        relogio,
        *modos,
    )
    simuladores_ = criar_simuladores(
        modos,
        lambda: Simuladores(
            orquestracao,
            cancelas,
            fonte_posicao,
            reconhecedor,
            relogio,
            CenarioBalanca.SEM_RESPOSTA,
            Decimal("0"),
            Decimal("0"),
            dict.fromkeys(CancelaPedida, CenarioCancela.CONFIRMADO),
            CenarioPosicao.AUSENTE,
        ),
    )
    return orquestracao, distribuidor, simuladores_


def criar_aplicacao(
    configuracao: Configuracao | None = None,
    engine: Engine | None = None,
    relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
    executar_ciclos: bool = True,
) -> FastAPI:
    """`executar_ciclos=False` só nos testes da API: a retomada roda, os ciclos de
    câmera e balança não, para o resultado não depender do tempo."""
    configuracao = configuracao or ler_configuracao(os.environ)
    engine = engine or criar_engine(configuracao.banco)
    # O registro de acesso do uvicorn grava a query string; o nosso não (spec 007 §3.4).
    logging.getLogger("uvicorn.access").disabled = True
    # Sem configuração prévia de logging, o nosso registro de acesso vai para a saída.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    orquestracao, distribuidor, simuladores_ = _compor(configuracao, engine, relogio)
    sinal = SinalCiclos()

    @contextlib.asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        # Retomada antes de tudo, sem reenviar comando às cegas (spec 006 §7.2).
        await orquestracao.retomar()
        tarefa = (
            asyncio.create_task(orquestracao.executar()) if executar_ciclos else None
        )
        if tarefa is not None:
            tarefa.add_done_callback(_vigiar_ciclos(sinal))
        try:
            yield
        finally:
            # Comandos já pedidos terminam antes de parar (spec 015 §6.6).
            await orquestracao.aguardar_comandos_agendados()
            # Já terminada: o erro foi registrado por `_vigiar_ciclos`.
            if tarefa is not None and not tarefa.done():
                tarefa.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await tarefa

    app = FastAPI(
        title="Pesagem",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=ciclo_de_vida,
    )
    app.state.contexto = Contexto(
        configuracao, engine, relogio, orquestracao, distribuidor, simuladores_, sinal
    )
    registrar_tratadores(app)
    # Com hardware real, as rotas dos simuladores não existem (spec 011 §6.4).
    rotas = [
        operacao,
        diagnostico,
        *([simuladores] if simuladores_ is not None else []),
    ]
    for modulo in (
        *rotas,
        agendamentos,
        autoatendimento,
        faixas_horario,
        sessoes,
        usuarios,
        transportadoras,
        motoristas,
        pesagens,
        tipos_veiculo,
        veiculos,
        produtos,
    ):
        app.include_router(modulo.router)

    origens = configuracao.seguranca.origens_permitidas

    @app.middleware("http")
    async def conferir_origem(
        request: Request, seguinte: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """CSRF antes de sessão e permissão, inclusive no login (spec 012 §6.9)."""
        # O autoatendimento confere rede e bloqueio antes, e chama esta mesma regra
        # na ordem da spec 013 §6.2.
        if request.method in _MUDAM_ESTADO and not request.url.path.startswith(
            "/api/autoatendimento/"
        ):
            erro = conferir_csrf(request, origens)
            if erro is not None:
                return erro
        return await seguinte(request)

    @app.middleware("http")
    async def registrar_acesso(
        request: Request, seguinte: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        resposta = await seguinte(request)
        # Só método, caminho e status: sem query string, corpo nem cookie.
        _log_acesso.info(
            "%s %s %s", request.method, request.url.path, resposta.status_code
        )
        return resposta

    return app
