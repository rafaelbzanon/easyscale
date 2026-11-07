"""Faixas de horário e vagas do dia (spec 008 §4.2, §5.2, §5.3, §6.7)."""

from datetime import date, time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from pesagem.api.dependencias import Contexto, ContextoDep, PaginacaoDep, exigir
from pesagem.api.erros import ErroApi
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.repositorios.usuario import SessaoAtual

router = APIRouter(prefix="/api/faixas-horario")
Consultar = Annotated[SessaoAtual, Depends(exigir("CONSULTAR_CADASTROS"))]
Gerenciar = Annotated[SessaoAtual, Depends(exigir("GERENCIAR_CADASTROS"))]
Criar = Annotated[SessaoAtual, Depends(exigir("CRIAR_AGENDAMENTO"))]
_Hora = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
_Capacidade = Annotated[int, Field(gt=0)]


class FaixaCriacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hora_inicio: _Hora
    hora_fim: _Hora
    capacidade: _Capacidade


class FaixaAlteracao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hora_inicio: _Hora = None  # type: ignore[assignment]
    hora_fim: _Hora = None  # type: ignore[assignment]
    capacidade: _Capacidade = None  # type: ignore[assignment]
    ativo: bool = None  # type: ignore[assignment]


def _hora(texto: str) -> time:
    return time.fromisoformat(texto)


def _texto(hora: time) -> str:
    return hora.strftime("%H:%M")


def _resposta(linha: Any) -> dict[str, Any]:
    return {
        **dict(linha),
        "hora_inicio": _texto(linha["hora_inicio"]),
        "hora_fim": _texto(linha["hora_fim"]),
    }


def _conferir_horas(inicio: time, fim: time) -> None:
    # Fim maior que início; faixa não cruza a meia-noite (P-5).
    if fim <= inicio:
        raise ErroApi(422, "CAMPO_INVALIDO", [("hora_fim", "CAMPO_INVALIDO")])


@router.get("")
def listar(
    _: Consultar,
    contexto: ContextoDep,
    paginacao: PaginacaoDep,
    ativo: bool | None = None,
) -> dict[str, Any]:
    with transacao(contexto.engine) as t:
        linhas, total = t.faixas.listar(
            ativo, paginacao.pagina, paginacao.tamanho_pagina
        )
    return {
        "itens": [_resposta(linha) for linha in linhas],
        "total": total,
        "pagina": paginacao.pagina,
        "tamanho_pagina": paginacao.tamanho_pagina,
    }


# Antes de `/{faixa_horario_id}`, para "disponibilidade" não ser lido como id.
@router.get("/disponibilidade")
def disponibilidade(
    _: Criar, contexto: ContextoDep, data: Annotated[date, Query()]
) -> dict[str, Any]:
    return montar_disponibilidade(contexto, data)


def montar_disponibilidade(contexto: Contexto, data: date) -> dict[str, Any]:
    """Também usada pelo autoatendimento (spec 013 §4)."""
    agora = contexto.agora_patio()
    with transacao(contexto.engine) as t:
        faixas = t.faixas.disponibilidade(data, agora.date(), agora.time())
    return {
        "data": data,
        "itens": [
            {
                "faixa_horario_id": f.faixa_horario_id,
                "hora_inicio": _texto(f.hora_inicio),
                "hora_fim": _texto(f.hora_fim),
                "capacidade": f.capacidade,
                "vagas_ocupadas": f.vagas_ocupadas,
                "vagas_livres": max(0, f.capacidade - f.vagas_ocupadas),
                "encerrada": f.encerrada,
            }
            for f in faixas
        ],
    }


@router.get("/{faixa_horario_id}")
def obter(faixa_horario_id: int, _: Consultar, contexto: ContextoDep) -> dict[str, Any]:
    with transacao(contexto.engine) as t:
        return _resposta(t.faixas.obter(faixa_horario_id))


@router.post("", status_code=201)
def criar(entrada: FaixaCriacao, _: Gerenciar, contexto: ContextoDep) -> dict[str, Any]:
    inicio, fim = _hora(entrada.hora_inicio), _hora(entrada.hora_fim)
    _conferir_horas(inicio, fim)
    with transacao(contexto.engine) as t:
        faixa_id = t.faixas.criar(inicio, fim, entrada.capacidade)
        linha = t.faixas.obter(faixa_id)
    return _resposta(linha)


@router.patch("/{faixa_horario_id}")
def alterar(
    faixa_horario_id: int, entrada: FaixaAlteracao, _: Gerenciar, contexto: ContextoDep
) -> dict[str, Any]:
    campos: dict[str, Any] = entrada.model_dump(exclude_unset=True)
    for nome in ("hora_inicio", "hora_fim"):
        if nome in campos:
            campos[nome] = _hora(campos[nome])
    with transacao(contexto.engine) as t:
        atual = t.faixas.obter(faixa_horario_id)
        _conferir_horas(
            campos.get("hora_inicio", atual["hora_inicio"]),
            campos.get("hora_fim", atual["hora_fim"]),
        )
        t.faixas.alterar(faixa_horario_id, campos, contexto.agora_patio().date())
        linha = t.faixas.obter(faixa_horario_id)
    return _resposta(linha)
