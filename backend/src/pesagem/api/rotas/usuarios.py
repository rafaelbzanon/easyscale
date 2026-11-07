"""Usuários e perfis (spec 012 §4.2, §6.5, §6.6; RF-032)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from pesagem.api.dependencias import ContextoDep, PaginacaoDep, exigir
from pesagem.api.erros import ErroApi
from pesagem.api.esquemas.comum import Pagina
from pesagem.api.esquemas.usuarios import (
    PerfilResposta,
    PerfisResposta,
    RedefinicaoSenha,
    UsuarioAlteracao,
    UsuarioCriacao,
    UsuarioResposta,
)
from pesagem.api.senha import gerar_hash_senha, resumo
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.repositorios.usuario import SessaoAtual, Usuario

router = APIRouter(prefix="/api")
Administrador = Annotated[SessaoAtual, Depends(exigir("GERENCIAR_USUARIOS"))]


def _resposta(u: Usuario) -> UsuarioResposta:
    return UsuarioResposta(
        id=u.id,
        nome=u.nome,
        login=u.login,
        perfil=u.perfil,
        ativo=u.ativo,
        criado_em=u.criado_em,
    )


@router.get("/usuarios")
def listar(
    _: Administrador,
    contexto: ContextoDep,
    paginacao: PaginacaoDep,
    ativo: bool | None = None,
    perfil: str | None = None,
    busca: str | None = None,
) -> Pagina[UsuarioResposta]:
    with transacao(contexto.engine) as t:
        itens, total = t.usuarios.listar_usuarios(
            ativo, perfil, busca, paginacao.pagina, paginacao.tamanho_pagina
        )
    return Pagina(
        itens=[_resposta(u) for u in itens],
        total=total,
        pagina=paginacao.pagina,
        tamanho_pagina=paginacao.tamanho_pagina,
    )


@router.get("/usuarios/{usuario_id}")
def obter(usuario_id: int, _: Administrador, contexto: ContextoDep) -> UsuarioResposta:
    with transacao(contexto.engine) as t:
        return _resposta(t.usuarios.obter_usuario(usuario_id))


@router.post("/usuarios", status_code=201)
def criar(
    entrada: UsuarioCriacao, sessao: Administrador, contexto: ContextoDep
) -> UsuarioResposta:
    agora = contexto.agora()
    senha_hash = gerar_hash_senha(entrada.senha)
    with transacao(contexto.engine) as t:
        usuario_id = t.usuarios.criar_usuario(
            entrada.nome, entrada.login, senha_hash, entrada.perfil
        )
        if usuario_id is None:
            raise ErroApi(422, "CAMPO_INVALIDO", [("perfil", "CAMPO_INVALIDO")])
        t.acesso.auditar(
            "USUARIO_CRIADO",
            agora,
            responsavel_id=sessao.usuario.id,
            usuario_afetado_id=usuario_id,
        )
        criado = t.usuarios.obter_usuario(usuario_id)
    return _resposta(criado)


@router.patch("/usuarios/{usuario_id}")
def alterar(
    usuario_id: int,
    entrada: UsuarioAlteracao,
    sessao: Administrador,
    contexto: ContextoDep,
) -> UsuarioResposta:
    if usuario_id == sessao.usuario.id and not entrada.ativo:
        raise ErroApi(409, "CONFLITO", [("ativo", "PROPRIO_USUARIO")])
    agora = contexto.agora()
    with transacao(contexto.engine) as t:
        antes = t.usuarios.obter_usuario(usuario_id)
        if antes.ativo != entrada.ativo:
            t.usuarios.alterar_ativo(usuario_id, entrada.ativo, agora)
            t.acesso.auditar(
                "USUARIO_REATIVADO" if entrada.ativo else "USUARIO_DESATIVADO",
                agora,
                responsavel_id=sessao.usuario.id,
                usuario_afetado_id=usuario_id,
            )
        depois = t.usuarios.obter_usuario(usuario_id)
    return _resposta(depois)


@router.post("/usuarios/{usuario_id}/redefinir-senha", status_code=204)
def redefinir_senha(
    usuario_id: int,
    entrada: RedefinicaoSenha,
    sessao: Administrador,
    contexto: ContextoDep,
) -> Response:
    agora = contexto.agora()
    senha_hash = gerar_hash_senha(entrada.nova_senha)
    with transacao(contexto.engine) as t:
        usuario = t.usuarios.obter_usuario(usuario_id)
        t.usuarios.redefinir_senha(usuario_id, senha_hash, agora)
        t.acesso.zerar("LOGIN", resumo(usuario.login.lower()))
        t.acesso.auditar(
            "SENHA_REDEFINIDA",
            agora,
            responsavel_id=sessao.usuario.id,
            usuario_afetado_id=usuario_id,
        )
    return Response(status_code=204)


@router.get("/perfis")
def listar_perfis(_: Administrador, contexto: ContextoDep) -> PerfisResposta:
    with transacao(contexto.engine) as t:
        perfis = t.usuarios.listar_perfis()
    return PerfisResposta(
        itens=[PerfilResposta(codigo=c, permissoes=list(p)) for c, p in perfis]
    )
