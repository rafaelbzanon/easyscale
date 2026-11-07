"""Dependências das rotas: contexto, sessão, permissão e paginação (ADR-0004; spec 012 §6.2)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.responses import JSONResponse

from pesagem.api.erros import ErroApi, resposta_erro
from pesagem.api.senha import resumo
from pesagem.config import Configuracao
from pesagem.orquestracao.eventos import DistribuidorEventos
from pesagem.orquestracao.operacao import Orquestracao
from pesagem.orquestracao.simuladores import Simuladores
from pesagem.persistencia.banco import Engine, transacao
from pesagem.persistencia.repositorios.usuario import SessaoAtual

COOKIE_SESSAO = "pesagem_sessao"


@dataclass
class SinalCiclos:
    """Marcado quando a tarefa dos ciclos termina sem ter sido cancelada (main.py)."""

    parados: bool = False


@dataclass(frozen=True)
class Contexto:
    configuracao: Configuracao
    engine: Engine
    relogio: Callable[[], datetime]
    orquestracao: Orquestracao
    distribuidor: DistribuidorEventos
    # `None` com qualquer dispositivo em `REAL`: as rotas da spec 011 §4.2 não existem.
    simuladores: Simuladores | None
    ciclos: SinalCiclos = field(default_factory=SinalCiclos)

    def agora(self) -> datetime:
        return self.relogio()

    def agora_patio(self) -> datetime:
        """Data e hora no fuso do pátio (spec 008 §6.1)."""
        return self.relogio().astimezone(self.configuracao.patio_fuso)


def obter_contexto(request: Request) -> Contexto:
    contexto: Contexto = request.app.state.contexto
    return contexto


ContextoDep = Annotated[Contexto, Depends(obter_contexto)]


def buscar_sessao(
    request: Request, contexto: Contexto, renovar: bool
) -> SessaoAtual | None:
    """Sessão aberta, no prazo e de usuário ativo; o canal de eventos não renova (§6.3)."""
    identificador = request.cookies.get(COOKIE_SESSAO)
    if not identificador:
        return None
    with transacao(contexto.engine) as t:
        return t.usuarios.buscar_sessao_valida(
            resumo(identificador),
            contexto.agora(),
            contexto.configuracao.seguranca.sessao_tempo_sem_uso_s,
            renovar=renovar,
        )


def obter_sessao(request: Request, contexto: ContextoDep) -> SessaoAtual:
    """401 sem cookie, com sessão encerrada, vencida ou de usuário inativo.

    Banco indisponível sobe como erro: na dúvida, sem acesso (spec 012 §6.13).
    """
    sessao = buscar_sessao(request, contexto, renovar=True)
    if sessao is None:
        raise ErroApi(401, "NAO_AUTENTICADO")
    return sessao


SessaoDep = Annotated[SessaoAtual, Depends(obter_sessao)]


def exigir(permissao: str) -> Callable[[SessaoAtual], SessaoAtual]:
    """Cada rota declara uma permissão do catálogo (ADR-0004 §4.2)."""

    def verificar(sessao: SessaoDep) -> SessaoAtual:
        if permissao not in sessao.permissoes:
            raise ErroApi(403, "SEM_PERMISSAO")
        return sessao

    return verificar


@dataclass(frozen=True)
class Paginacao:
    pagina: int
    tamanho_pagina: int


def obter_paginacao(
    contexto: ContextoDep,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho_pagina: Annotated[int | None, Query(ge=1)] = None,
) -> Paginacao:
    """Acima do máximo configurado dá 422 (spec 007 §3.3)."""
    configuracao = contexto.configuracao
    tamanho = (
        configuracao.tamanho_pagina_padrao if tamanho_pagina is None else tamanho_pagina
    )
    if tamanho > configuracao.tamanho_pagina_maximo:
        raise ErroApi(422, "CAMPO_INVALIDO", [("tamanho_pagina", "CAMPO_INVALIDO")])
    return Paginacao(pagina, tamanho)


PaginacaoDep = Annotated[Paginacao, Depends(obter_paginacao)]


def conferir_csrf(request: Request, origens: frozenset[str]) -> JSONResponse | None:
    """`Origin` permitido e corpo JSON, antes de sessão e permissão (spec 012 §6.9)."""
    if request.headers.get("origin") not in origens:
        return resposta_erro(403, "ORIGEM_NAO_PERMITIDA")
    tipo = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if tipo != "application/json":
        return resposta_erro(415, "TIPO_CONTEUDO_INVALIDO")
    return None
