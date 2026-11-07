"""As quatro rotas comuns dos cinco cadastros (spec 007 §4.1, §6).

Cada arquivo de `rotas/` descreve o seu recurso com um `Recurso`; aqui ficam
as regras que valem para todos: lista paginada, item, criação e alteração só
dos campos enviados, referências ativas e cadastro ligado a operação aberta.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from pesagem.api.dependencias import ContextoDep, PaginacaoDep, exigir
from pesagem.api.erros import ErroApi
from pesagem.persistencia.banco import Transacao, transacao
from pesagem.persistencia.repositorios.usuario import SessaoAtual

Consultar = Annotated[SessaoAtual, Depends(exigir("CONSULTAR_CADASTROS"))]
Gerenciar = Annotated[SessaoAtual, Depends(exigir("GERENCIAR_CADASTROS"))]
Corpo = Annotated[dict[str, Any], Body()]
Linha = dict[str, Any]


class EntradaCadastro(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class Recurso:
    rota: str
    tabela: str
    colunas: tuple[str, ...]
    ordem: str
    criacao: type[EntradaCadastro]
    # Filtro da query string -> (condição SQL, parâmetros); levanta ErroApi se inválido.
    filtros: dict[str, Callable[[str], tuple[str, Linha]]]
    # Campo da entrada -> tabela que precisa ter o id ativo.
    referencias: dict[str, str] = field(default_factory=dict)
    # Ajusta os campos antes de gravar (ex.: placa normalizada); recebe o id na alteração.
    preparar: Callable[[Transacao, Linha, int | None], Linha] = lambda _t, c, _i: c
    # Ajusta a resposta; o booleano diz se o CPF completo pode aparecer (spec 007 §4.2).
    responder: Callable[[Linha, bool], Linha] = lambda linha, _cpf: linha


def filtro_ativo(valor: str) -> tuple[str, Linha]:
    if valor not in ("true", "false"):
        raise ErroApi(422, "CAMPO_INVALIDO", [("ativo", "CAMPO_INVALIDO")])
    return "ativo = :ativo", {"ativo": valor == "true"}


def filtro_id(coluna: str) -> Callable[[str], tuple[str, Linha]]:
    def filtrar(valor: str) -> tuple[str, Linha]:
        if not valor.isdigit():
            raise ErroApi(422, "CAMPO_INVALIDO", [(coluna, "CAMPO_INVALIDO")])
        return f"{coluna} = :{coluna}", {coluna: int(valor)}

    return filtrar


def filtro_busca(*colunas: str) -> Callable[[str], tuple[str, Linha]]:
    def filtrar(valor: str) -> tuple[str, Linha]:
        escapado = valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        condicao = " OR ".join(f"{c} ILIKE :busca" for c in colunas)
        return f"({condicao})", {"busca": f"%{escapado}%"}

    return filtrar


def _validar(modelo: type[BaseModel], corpo: Linha) -> Linha:
    try:
        return modelo.model_validate(corpo).model_dump(exclude_unset=True)
    except ValidationError as erro:
        raise RequestValidationError(
            [{**e, "loc": ("body", *e["loc"])} for e in erro.errors()]
        ) from None


def _texto_decimal(linha: Linha) -> Linha:
    """`Decimal` trafega como texto, sem perder casas (spec 007 §3.1)."""
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in linha.items()}


def registrar(router: APIRouter, recurso: Recurso) -> None:
    caminho = f"/api/{recurso.rota}"
    colunas = ", ".join(("id", *recurso.colunas, "ativo"))
    # Alteração: os mesmos campos, todos opcionais, mais `ativo`. Um `null` em campo
    # obrigatório continua inválido, porque o padrão `None` não é validado.
    campos_alteracao: dict[str, Any] = {
        nome: (
            Annotated[info.annotation, *info.metadata]
            if info.metadata
            else info.annotation,
            None,
        )
        for nome, info in recurso.criacao.model_fields.items()
    }
    alteracao = create_model(
        f"{recurso.criacao.__name__}Alteracao",
        __base__=EntradaCadastro,
        ativo=(bool, None),
        **campos_alteracao,
    )

    def responder(linha: Linha, cpf_completo: bool) -> Linha:
        return _texto_decimal(recurso.responder(dict(linha), cpf_completo))

    def conferir_referencias(t: Transacao, campos: Linha) -> None:
        for campo, tabela in recurso.referencias.items():
            if campos.get(campo) is not None and not t.cadastros.esta_ativo(
                tabela, campos[campo]
            ):
                raise ErroApi(422, "CAMPO_INVALIDO", [(campo, "CAMPO_INVALIDO")])

    @router.get(caminho)
    def listar(
        request: Request, _: Consultar, contexto: ContextoDep, paginacao: PaginacaoDep
    ) -> dict[str, Any]:
        condicoes: list[str] = []
        parametros: Linha = {}
        for nome, filtrar in recurso.filtros.items():
            if nome in request.query_params:
                condicao, valores = filtrar(request.query_params[nome])
                condicoes.append(condicao)
                parametros.update(valores)
        with transacao(contexto.engine) as t:
            linhas, total = t.cadastros.listar(
                recurso.tabela,
                colunas,
                condicoes,
                parametros,
                recurso.ordem,
                paginacao.pagina,
                paginacao.tamanho_pagina,
            )
        return {
            "itens": [responder(dict(linha), False) for linha in linhas],
            "total": total,
            "pagina": paginacao.pagina,
            "tamanho_pagina": paginacao.tamanho_pagina,
        }

    @router.get(caminho + "/{item_id}")
    def obter(item_id: int, sessao: Consultar, contexto: ContextoDep) -> Linha:
        with transacao(contexto.engine) as t:
            linha = t.cadastros.obter(recurso.tabela, colunas, item_id)
        return responder(dict(linha), "GERENCIAR_CADASTROS" in sessao.permissoes)

    @router.post(caminho, status_code=201)
    def criar(corpo: Corpo, _: Gerenciar, contexto: ContextoDep) -> Linha:
        campos = _validar(recurso.criacao, corpo)
        with transacao(contexto.engine) as t:
            conferir_referencias(t, campos)
            item_id = t.cadastros.inserir(
                recurso.tabela, recurso.preparar(t, campos, None)
            )
            linha = t.cadastros.obter(recurso.tabela, colunas, item_id)
        return responder(dict(linha), True)

    @router.patch(caminho + "/{item_id}")
    def alterar(
        item_id: int, corpo: Corpo, _: Gerenciar, contexto: ContextoDep
    ) -> Linha:
        campos = _validar(alteracao, corpo)
        with transacao(contexto.engine) as t:
            t.cadastros.obter(recurso.tabela, colunas, item_id)  # 404 antes de tudo
            conferir_referencias(t, campos)
            # Desativar com operação aberta dá 409 (spec 007 §6.3, RN-008).
            if (
                campos.get("ativo") is False
                and recurso.tabela in ("veiculo", "motorista", "transportadora")
                and t.cadastros.tem_operacao_aberta(recurso.tabela, item_id)
            ):
                raise ErroApi(409, "CONFLITO", [("ativo", "CONFLITO")])
            t.cadastros.alterar(
                recurso.tabela, item_id, recurso.preparar(t, campos, item_id)
            )
            linha = t.cadastros.obter(recurso.tabela, colunas, item_id)
        return responder(dict(linha), True)
