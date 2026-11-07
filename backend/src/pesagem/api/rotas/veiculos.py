"""Veículos (spec 007 §5.4 e §6.1)."""

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter
from pydantic import Field, StringConstraints

from pesagem.api.cadastros import (
    EntradaCadastro,
    Recurso,
    filtro_ativo,
    filtro_id,
    registrar,
)
from pesagem.api.erros import ErroApi
from pesagem.api.validacao import normalizar_placa_digitada
from pesagem.dominio.placa.normalizacao import normalizar_placa
from pesagem.persistencia.banco import Transacao

router = APIRouter()
_Peso = Annotated[Decimal, Field(max_digits=12, decimal_places=3)]


class VeiculoCriacao(EntradaCadastro):
    placa: str
    tipo_veiculo_id: int
    transportadora_id: int | None = None
    motorista_padrao_id: int | None = None
    marca: Annotated[str, StringConstraints(max_length=30)] | None = None
    modelo: Annotated[str, StringConstraints(max_length=30)] | None = None
    eixos: Annotated[int, Field(gt=0)] | None = None
    # Informativa: nunca substitui um peso medido (RN-006).
    tara_kg: Annotated[_Peso, Field(ge=0)] | None = None
    capacidade_kg: Annotated[_Peso, Field(gt=0)] | None = None


def _placa_invalida() -> ErroApi:
    return ErroApi(422, "CAMPO_INVALIDO", [("placa", "PLACA_INVALIDA")])


def _preparar(
    t: Transacao, campos: dict[str, Any], item_id: int | None
) -> dict[str, Any]:
    if "placa" not in campos:
        return campos
    placa = normalizar_placa_digitada(campos["placa"])
    if placa is None:
        raise _placa_invalida()
    if item_id is not None:
        atual = t.cadastros.obter("veiculo", "placa", item_id)["placa"]
        # Mudar a placa com operação aberta dá 409 (spec 007 §6.3).
        if atual != placa.placa_normalizada and t.cadastros.tem_operacao_aberta(
            "veiculo", item_id
        ):
            raise ErroApi(409, "CONFLITO", [("placa", "CONFLITO")])
    return {
        **campos,
        "placa": placa.placa_normalizada,
        "chave_comparacao": placa.chave_comparacao,
    }


def _filtro_placa(valor: str) -> tuple[str, dict[str, Any]]:
    placa = normalizar_placa_digitada(valor)
    if placa is None:
        raise _placa_invalida()
    return "chave_comparacao = :chave", {"chave": placa.chave_comparacao}


def _responder(linha: dict[str, Any], _cpf: bool) -> dict[str, Any]:
    resultado = normalizar_placa(linha["placa"])
    formato = getattr(resultado, "formato", None)
    return {**linha, "formato_placa": None if formato is None else formato.value}


registrar(
    router,
    Recurso(
        rota="veiculos",
        tabela="veiculo",
        colunas=(
            "placa",
            "tipo_veiculo_id",
            "transportadora_id",
            "motorista_padrao_id",
            "marca",
            "modelo",
            "eixos",
            "tara_kg",
            "capacidade_kg",
        ),
        ordem="placa, id",
        criacao=VeiculoCriacao,
        filtros={
            "ativo": filtro_ativo,
            "transportadora_id": filtro_id("transportadora_id"),
            "placa": _filtro_placa,
        },
        referencias={
            "tipo_veiculo_id": "tipo_veiculo",
            "transportadora_id": "transportadora",
            "motorista_padrao_id": "motorista",
        },
        preparar=_preparar,
        responder=_responder,
    ),
)
