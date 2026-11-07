"""Esquemas de sessão, usuários e perfis (spec 012 §5)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from pesagem.api.esquemas.comum import Entrada


class LoginEntrada(Entrada):
    login: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    senha: Annotated[str, StringConstraints(min_length=1)]


class UsuarioResumo(BaseModel):
    id: int
    nome: str
    login: str
    perfil: str


class UsuarioAtualResposta(BaseModel):
    usuario: UsuarioResumo
    permissoes: list[str]


class UsuarioResposta(BaseModel):
    id: int
    nome: str
    login: str
    perfil: str
    ativo: bool
    criado_em: datetime


class UsuarioCriacao(Entrada):
    nome: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    login: Annotated[
        str, StringConstraints(min_length=1, max_length=50, pattern=r"^\S+$")
    ]
    perfil: Annotated[str, StringConstraints(min_length=1)]
    senha: Annotated[str, StringConstraints(min_length=1)]


class UsuarioAlteracao(Entrada):
    """Só `ativo` (spec 012 §6.5, P-1)."""

    ativo: bool


class RedefinicaoSenha(Entrada):
    nova_senha: Annotated[str, StringConstraints(min_length=1)]


class PerfilResposta(BaseModel):
    codigo: str
    permissoes: list[str]


class PerfisResposta(BaseModel):
    itens: list[PerfilResposta]
