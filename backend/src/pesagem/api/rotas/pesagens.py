"""Histórico das pesagens e eventos de cada uma (spec 010). Só consulta."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from pesagem.api.dependencias import ContextoDep, PaginacaoDep, exigir
from pesagem.api.erros import ErroApi
from pesagem.api.esquemas.pesagens import pesagem_resposta
from pesagem.api.validacao import normalizar_placa_digitada
from pesagem.dominio.operacao.maquina_estados import SituacaoOperacao
from pesagem.dominio.pesagem.calculo_peso import ClassificacaoPesoLiquido
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.repositorios.usuario import SessaoAtual

router = APIRouter(prefix="/api/pesagens")
Consultar = Annotated[SessaoAtual, Depends(exigir("CONSULTAR_OPERACAO"))]
_VALORES = {
    "situacao": {s.value for s in SituacaoOperacao},
    "tipo_operacao": {"CARGA", "DESCARGA"},
    "classificacao": {c.value for c in ClassificacaoPesoLiquido},
}


def _invalido(campo: str, codigo: str = "CAMPO_INVALIDO") -> ErroApi:
    return ErroApi(422, "CAMPO_INVALIDO", [(campo, codigo)])


def _filtros(consulta: Any) -> dict[str, Any]:
    filtros: dict[str, Any] = {}
    for nome in ("data_inicio", "data_fim"):
        if nome in consulta:
            try:
                filtros[nome] = date.fromisoformat(consulta[nome])
            except ValueError:
                raise _invalido(nome) from None
    if (
        "data_inicio" in filtros
        and filtros.get("data_fim", date.max) < filtros["data_inicio"]
    ):
        raise _invalido("data_fim")
    for nome in ("aberta", "liberacao_manual"):
        if nome in consulta:
            if consulta[nome] not in ("true", "false"):
                raise _invalido(nome)
            filtros[nome] = consulta[nome] == "true"
    for nome, aceitos in _VALORES.items():
        if nome in consulta:
            if consulta[nome] not in aceitos:
                raise _invalido(nome)
            filtros[nome] = consulta[nome]
    if "agendamento_id" in consulta:
        if not consulta["agendamento_id"].isdigit():
            raise _invalido("agendamento_id")
        filtros["agendamento_id"] = int(consulta["agendamento_id"])
    if "placa" in consulta:
        placa = normalizar_placa_digitada(consulta["placa"])
        if placa is None:
            raise _invalido("placa", "PLACA_INVALIDA")
        filtros["chave_comparacao"] = placa.chave_comparacao
    return filtros


@router.get("")
def listar(
    request: Request, _: Consultar, contexto: ContextoDep, paginacao: PaginacaoDep
) -> dict[str, Any]:
    filtros = _filtros(request.query_params)
    with transacao(contexto.engine) as t:
        linhas, total = t.pesagens.listar_historico(
            filtros,
            str(contexto.configuracao.patio_fuso),
            contexto.agora_patio().date(),
            paginacao.pagina,
            paginacao.tamanho_pagina,
        )
    return {
        "itens": [pesagem_resposta(linha) for linha in linhas],
        "total": total,
        "pagina": paginacao.pagina,
        "tamanho_pagina": paginacao.tamanho_pagina,
    }


@router.get("/{pesagem_id}/eventos")
def eventos(
    pesagem_id: int, _: Consultar, contexto: ContextoDep, paginacao: PaginacaoDep
) -> dict[str, Any]:
    with transacao(contexto.engine) as t:
        linhas, total = t.pesagens.listar_eventos(
            pesagem_id, paginacao.pagina, paginacao.tamanho_pagina
        )
    itens = []
    for linha in linhas:
        dados = {
            k: str(v) if isinstance(v, Decimal) else v for k, v in dict(linha).items()
        }
        responsavel_id, nome = (
            dados.pop("responsavel_id"),
            dados.pop("responsavel_nome"),
        )
        dados["responsavel"] = (
            None if responsavel_id is None else {"id": responsavel_id, "nome": nome}
        )
        if dados["tipo"] == "COMANDO_CANCELA":
            dados["evento"] = None  # spec 010 §5.2
        itens.append(dados)
    return {
        "itens": itens,
        "total": total,
        "pagina": paginacao.pagina,
        "tamanho_pagina": paginacao.tamanho_pagina,
    }
