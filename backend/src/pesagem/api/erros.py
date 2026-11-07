"""Todo erro vira o corpo da spec 007 §3.2, inclusive a validação automática."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from pesagem.persistencia.erros import (
    ErroCodigoNotaNaoPermitido,
    ErroConflitoVersao,
    ErroDuplicidade,
    ErroFaixaComAgendamentos,
    ErroFaixaEncerrada,
    ErroFaixaSemVaga,
    ErroFaixaSobreposta,
    ErroLiberacaoIndisponivel,
    ErroNaoEncontrado,
    ErroPersistencia,
    ErroSemFaixaDisponivel,
    ErroStatusAgendamento,
    ErroVeiculoJaAgendado,
)

_log = logging.getLogger("pesagem.api")

_MENSAGENS = {
    "NAO_AUTENTICADO": "Faça login para continuar.",
    "SEM_PERMISSAO": "Seu perfil não tem permissão para esta ação.",
    "NAO_ENCONTRADO": "Registro não encontrado.",
    "CONFLITO": "A ação conflita com o estado atual dos dados.",
    "CAMPO_INVALIDO": "Há campos inválidos.",
    "ERRO_INTERNO": "Erro interno. Tente de novo.",
    "METODO_NAO_PERMITIDO": "Método não permitido nesta rota.",
    "CREDENCIAIS_INVALIDAS": "Login ou senha inválidos.",
    "LOGIN_BLOQUEADO": "Muitas tentativas. Aguarde e tente de novo.",
    "ORIGEM_NAO_PERMITIDA": "Origem não permitida.",
    "TIPO_CONTEUDO_INVALIDO": "Envie o corpo em JSON.",
    "REDE_NAO_PERMITIDA": "Acesso permitido só pela rede do pátio.",
    "DADOS_NAO_CONFEREM": "Placa ou CPF não conferem com o cadastro.",
    "AUTOATENDIMENTO_BLOQUEADO": "Muitas tentativas. Aguarde e tente de novo.",
}

# Restrição do banco -> campo citado no 409 (spec 007 §3.2: `campos` indica a causa).
_CAMPO_POR_RESTRICAO = {
    "ux_usuario_login": "login",
    "ux_motorista_cpf": "cpf",
    "ux_transportadora_cnpj": "cnpj",
    "ux_veiculo_chave_comparacao": "placa",
    "ux_tipo_veiculo_descricao": "descricao",
    "ux_produto_codigo": "codigo",
}


# Erro da persistência -> (status, campo, código em `campos`) (spec 008 §6.10).
_REGRAS: dict[type[ErroPersistencia], tuple[int, str, str]] = {
    ErroFaixaSemVaga: (409, "faixa_horario_id", "FAIXA_SEM_VAGA"),
    ErroFaixaEncerrada: (409, "faixa_horario_id", "FAIXA_ENCERRADA"),
    ErroSemFaixaDisponivel: (409, "faixa_horario_id", "SEM_FAIXA_DISPONIVEL"),
    ErroVeiculoJaAgendado: (409, "veiculo_id", "VEICULO_JA_AGENDADO"),
    ErroStatusAgendamento: (409, "status", "STATUS_NAO_PERMITE"),
    ErroCodigoNotaNaoPermitido: (422, "codigo_nota", "CODIGO_NOTA_NAO_PERMITIDO"),
    ErroFaixaSobreposta: (409, "hora_inicio", "FAIXA_SOBREPOSTA"),
    ErroFaixaComAgendamentos: (409, "hora_inicio", "FAIXA_COM_AGENDAMENTOS"),
    ErroConflitoVersao: (409, "versao", "VERSAO_DESATUALIZADA"),
    ErroLiberacaoIndisponivel: (409, "pesagem_id", "LIBERACAO_EM_CURSO"),
}


class ErroApi(Exception):
    def __init__(
        self, status: int, codigo: str, campos: list[tuple[str, str]] | None = None
    ) -> None:
        super().__init__(codigo)
        self.status = status
        self.codigo = codigo
        self.campos = campos or []


def resposta_erro(
    status: int, codigo: str, campos: list[tuple[str, str]] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "erro": {
                "codigo": codigo,
                "mensagem": _MENSAGENS.get(codigo, "Não foi possível concluir a ação."),
                "campos": [{"campo": c, "codigo": k} for c, k in campos or []],
            }
        },
    )


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroApi)
    async def _api(_: Request, erro: ErroApi) -> JSONResponse:
        return resposta_erro(erro.status, erro.codigo, erro.campos)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        campos = []
        for item in erro.errors():
            local = [str(p) for p in item["loc"][1:]] or [str(item["loc"][0])]
            campos.append((".".join(local), "CAMPO_INVALIDO"))
        return resposta_erro(422, "CAMPO_INVALIDO", campos)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, erro: HTTPException) -> JSONResponse:
        codigo = {404: "NAO_ENCONTRADO", 405: "METODO_NAO_PERMITIDO"}.get(
            erro.status_code, "ERRO_INTERNO"
        )
        return resposta_erro(
            erro.status_code if codigo != "ERRO_INTERNO" else 500, codigo
        )

    @app.exception_handler(ErroDuplicidade)
    async def _duplicidade(_: Request, erro: ErroDuplicidade) -> JSONResponse:
        campo = _CAMPO_POR_RESTRICAO.get(erro.restricao, erro.restricao)
        return resposta_erro(409, "CONFLITO", [(campo, "CONFLITO")])

    @app.exception_handler(ErroNaoEncontrado)
    async def _nao_encontrado(_: Request, erro: ErroNaoEncontrado) -> JSONResponse:
        return resposta_erro(404, "NAO_ENCONTRADO")

    @app.exception_handler(ErroPersistencia)
    async def _persistencia(_: Request, erro: ErroPersistencia) -> JSONResponse:
        if type(erro) in _REGRAS:
            status, campo, codigo = _REGRAS[type(erro)]
            geral = "CONFLITO" if status == 409 else "CAMPO_INVALIDO"
            return resposta_erro(status, geral, [(campo, codigo)])
        # Banco indisponível ou restrição não prevista: nada foi gravado (spec 007 §6.4).
        _log.error("falha de persistência: %s", type(erro).__name__)
        return resposta_erro(500, "ERRO_INTERNO")

    # Fronteira com o framework: qualquer outra exceção vira 500 com o corpo
    # comum, só o tipo vai para o log, e nada é engolido (CONVENCOES §4.5).
    @app.exception_handler(Exception)
    async def _inesperado(_: Request, erro: Exception) -> JSONResponse:
        _log.error("erro inesperado: %s", type(erro).__name__)
        return resposta_erro(500, "ERRO_INTERNO")
