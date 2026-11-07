"""Login, usuário atual e logout (spec 012 §4.1, §6.1 a §6.8)."""

from fastapi import APIRouter, Request, Response

from pesagem.api.dependencias import COOKIE_SESSAO, ContextoDep, SessaoDep
from pesagem.api.erros import ErroApi
from pesagem.api.esquemas.usuarios import (
    LoginEntrada,
    UsuarioAtualResposta,
    UsuarioResumo,
)
from pesagem.api.senha import (
    HASH_FICTICIO,
    conferir_senha,
    novo_identificador_sessao,
    resumo,
)
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.repositorios.usuario import SessaoAtual

router = APIRouter(prefix="/api/sessoes")


def _resposta(sessao: SessaoAtual) -> UsuarioAtualResposta:
    u = sessao.usuario
    return UsuarioAtualResposta(
        usuario=UsuarioResumo(id=u.id, nome=u.nome, login=u.login, perfil=u.perfil),
        permissoes=list(sessao.permissoes),
    )


def _gravar_cookie(response: Response, valor: str) -> None:
    # Sem Max-Age nem Expires: quem decide o fim é o servidor (§6.1).
    response.set_cookie(
        COOKIE_SESSAO, valor, httponly=True, secure=True, samesite="strict", path="/api"
    )


@router.post("", status_code=201)
def entrar(
    entrada: LoginEntrada, response: Response, contexto: ContextoDep
) -> UsuarioAtualResposta:
    seguranca = contexto.configuracao.seguranca
    agora = contexto.agora()
    # A chave da tentativa é o resumo do login em minúsculas, exista ele ou não (§6.8).
    chave = resumo(entrada.login.lower())
    sessao: SessaoAtual | None = None
    identificador = ""
    with transacao(contexto.engine) as t:
        credencial = t.usuarios.buscar_credencial(entrada.login)
        usuario_id = None if credencial is None else credencial.usuario_id
        if t.acesso.esta_bloqueado("LOGIN", chave, agora):
            # Sem conferir a senha e sem prolongar o bloqueio.
            t.acesso.auditar("LOGIN_BLOQUEADO", agora, usuario_afetado_id=usuario_id)
            resultado = "BLOQUEADO"
        else:
            senha_certa = conferir_senha(
                entrada.senha,
                HASH_FICTICIO if credencial is None else credencial.senha_hash,
            )
            if credencial is not None and credencial.ativo and senha_certa:
                identificador = novo_identificador_sessao()
                t.acesso.zerar("LOGIN", chave)
                t.usuarios.criar_sessao(
                    credencial.usuario_id, resumo(identificador), agora
                )
                t.acesso.auditar("LOGIN_ACEITO", agora, usuario_afetado_id=usuario_id)
                sessao = t.usuarios.buscar_sessao_valida(
                    resumo(identificador),
                    agora,
                    seguranca.sessao_tempo_sem_uso_s,
                    False,
                )
                resultado = "ACEITO"
            else:
                t.acesso.registrar_falha(
                    "LOGIN",
                    chave,
                    seguranca.login_tentativas_maximas,
                    seguranca.login_bloqueio_s,
                    agora,
                )
                # Login inexistente: só que não existe, nunca o texto digitado (§6.11).
                t.acesso.auditar("LOGIN_RECUSADO", agora, usuario_afetado_id=usuario_id)
                resultado = "RECUSADO"
    # A falha fica gravada antes de responder; por isso a resposta sai fora da transação.
    if resultado == "BLOQUEADO":
        raise ErroApi(429, "LOGIN_BLOQUEADO")
    if sessao is None:
        raise ErroApi(401, "CREDENCIAIS_INVALIDAS")
    _gravar_cookie(response, identificador)
    return _resposta(sessao)


@router.get("/atual")
def atual(sessao: SessaoDep) -> UsuarioAtualResposta:
    return _resposta(sessao)


@router.delete("/atual", status_code=204)
def sair(request: Request, contexto: ContextoDep) -> Response:
    """Sem sessão válida, 204 do mesmo jeito (§6.4); as outras sessões continuam."""
    identificador = request.cookies.get(COOKIE_SESSAO)
    if identificador:
        agora = contexto.agora()
        with transacao(contexto.engine) as t:
            usuario_id = t.usuarios.encerrar_sessao(resumo(identificador), agora)
            if usuario_id is not None:
                t.acesso.auditar(
                    "LOGOUT",
                    agora,
                    responsavel_id=usuario_id,
                    usuario_afetado_id=usuario_id,
                )
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE_SESSAO, httponly=True, secure=True, samesite="strict", path="/api"
    )
    return response
