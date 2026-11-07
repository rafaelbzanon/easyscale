"""Transportadoras (spec 007 §5.1)."""

from typing import Annotated

from fastapi import APIRouter
from pydantic import AfterValidator, StringConstraints

from pesagem.api.cadastros import (
    EntradaCadastro,
    Recurso,
    filtro_ativo,
    filtro_busca,
    registrar,
)
from pesagem.api.validacao import cnpj_valido, email_valido, so_digitos

router = APIRouter()


def _cnpj(valor: str) -> str:
    if not cnpj_valido(valor):
        raise ValueError("CNPJ inválido")
    return valor


class TransportadoraCriacao(EntradaCadastro):
    razao_social: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    nome_fantasia: Annotated[str, StringConstraints(max_length=100)] | None = None
    cnpj: Annotated[str, AfterValidator(_cnpj)]
    telefone: (
        Annotated[str, StringConstraints(max_length=15), AfterValidator(so_digitos)]
        | None
    ) = None
    email: (
        Annotated[str, StringConstraints(max_length=100), AfterValidator(email_valido)]
        | None
    ) = None


registrar(
    router,
    Recurso(
        rota="transportadoras",
        tabela="transportadora",
        colunas=("razao_social", "nome_fantasia", "cnpj", "telefone", "email"),
        ordem="razao_social, id",
        criacao=TransportadoraCriacao,
        filtros={
            "ativo": filtro_ativo,
            "busca": filtro_busca("razao_social", "nome_fantasia"),
        },
    ),
)
