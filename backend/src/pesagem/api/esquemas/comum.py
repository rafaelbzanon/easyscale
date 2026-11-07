"""Formas comuns da API (spec 007 §3)."""

from pydantic import BaseModel, ConfigDict


class Entrada(BaseModel):
    """Corpo de entrada: campo desconhecido ou somente leitura dá 422 (spec 007 §6.4)."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Pagina[T](BaseModel):
    itens: list[T]
    total: int
    pagina: int
    tamanho_pagina: int
