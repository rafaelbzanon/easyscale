"""Produtos (spec 007 §5.5)."""

from typing import Annotated

from fastapi import APIRouter
from pydantic import StringConstraints

from pesagem.api.cadastros import (
    EntradaCadastro,
    Recurso,
    filtro_ativo,
    filtro_busca,
    registrar,
)

router = APIRouter()


class ProdutoCriacao(EntradaCadastro):
    codigo: Annotated[str, StringConstraints(min_length=1, max_length=30)]
    descricao: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    unidade: Annotated[str, StringConstraints(min_length=1, max_length=5)] = "KG"


registrar(
    router,
    Recurso(
        rota="produtos",
        tabela="produto",
        colunas=("codigo", "descricao", "unidade"),
        ordem="descricao, id",
        criacao=ProdutoCriacao,
        filtros={"ativo": filtro_ativo, "busca": filtro_busca("codigo", "descricao")},
    ),
)
