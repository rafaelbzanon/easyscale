"""Tipos de veículo (spec 007 §5.3)."""

from typing import Annotated

from fastapi import APIRouter
from pydantic import StringConstraints

from pesagem.api.cadastros import EntradaCadastro, Recurso, filtro_ativo, registrar

router = APIRouter()


class TipoVeiculoCriacao(EntradaCadastro):
    # Único sem diferenciar maiúsculas: garantido no banco (ux_tipo_veiculo_descricao).
    descricao: Annotated[str, StringConstraints(min_length=1, max_length=100)]


registrar(
    router,
    Recurso(
        rota="tipos-veiculo",
        tabela="tipo_veiculo",
        colunas=("descricao",),
        ordem="descricao, id",
        criacao=TipoVeiculoCriacao,
        filtros={"ativo": filtro_ativo},
    ),
)
