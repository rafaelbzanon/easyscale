"""Motoristas (spec 007 §5.2; CPF completo só para quem gerencia, §4.2)."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter
from pydantic import AfterValidator, StringConstraints

from pesagem.api.cadastros import (
    EntradaCadastro,
    Recurso,
    filtro_ativo,
    filtro_busca,
    filtro_id,
    registrar,
)
from pesagem.api.validacao import cpf_valido, mascarar_cpf, so_digitos

router = APIRouter()


def _cpf(valor: str) -> str:
    if not cpf_valido(valor):
        raise ValueError("CPF inválido")
    return valor


class MotoristaCriacao(EntradaCadastro):
    nome: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    cpf: Annotated[str, AfterValidator(_cpf)]
    transportadora_id: int | None = None
    cnh_numero: Annotated[str, StringConstraints(max_length=20)] | None = None
    cnh_categoria: Annotated[str, StringConstraints(max_length=2)] | None = None
    data_validade_cnh: date | None = None
    telefone: (
        Annotated[str, StringConstraints(max_length=15), AfterValidator(so_digitos)]
        | None
    ) = None


def _responder(linha: dict[str, Any], cpf_completo: bool) -> dict[str, Any]:
    cpf = linha["cpf"]
    return {
        **linha,
        "cpf": cpf if cpf_completo else None,
        "cpf_mascarado": mascarar_cpf(cpf),
    }


registrar(
    router,
    Recurso(
        rota="motoristas",
        tabela="motorista",
        colunas=(
            "nome",
            "cpf",
            "transportadora_id",
            "cnh_numero",
            "cnh_categoria",
            "data_validade_cnh",
            "telefone",
        ),
        ordem="nome, id",
        criacao=MotoristaCriacao,
        filtros={
            "ativo": filtro_ativo,
            "transportadora_id": filtro_id("transportadora_id"),
            "busca": filtro_busca("nome"),
        },
        referencias={"transportadora_id": "transportadora"},
        responder=_responder,
    ),
)
