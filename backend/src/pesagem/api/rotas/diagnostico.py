"""Diagnóstico: leituras, imagens das decisões, imagem atual e dispositivos (spec 011 §4.1).

Imagens e placas são dados pessoais (RNF-013): nunca vão para log, e os bytes
saem com `Cache-Control: no-store`.
"""

from datetime import UTC, date
from email.utils import format_datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, StringConstraints

from pesagem.api.dependencias import ContextoDep, PaginacaoDep, exigir
from pesagem.api.erros import ErroApi
from pesagem.api.esquemas.operacao import (
    dispositivos_resposta,
    jsonavel,
    leitura_detalhe,
    leitura_resposta,
)
from pesagem.api.validacao import normalizar_placa_digitada
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.repositorios.usuario import SessaoAtual

router = APIRouter(prefix="/api")
ConsultarOperacao = Annotated[SessaoAtual, Depends(exigir("CONSULTAR_OPERACAO"))]
ConsultarImagens = Annotated[SessaoAtual, Depends(exigir("CONSULTAR_IMAGENS_DECISAO"))]
_SEM_CACHE = {"Cache-Control": "no-store"}
_DECISOES = {"AUTORIZADA", "RETORNO_ACEITO", "NAO_AUTORIZADA"}


class ExclusaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    # Só espaços não é motivo (RN-022, spec 011 §6.2).
    motivo: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]


def _invalido(campo: str, codigo: str = "CAMPO_INVALIDO") -> ErroApi:
    return ErroApi(422, "CAMPO_INVALIDO", [(campo, codigo)])


def _imagem_resposta(linha: Any) -> dict[str, Any]:
    dados = jsonavel(dict(linha))
    roi = {k: dados.pop(f"roi_{k}") for k in ("x", "y", "largura", "altura")}
    return {**dados, "roi": None if roi["x"] is None else roi}


@router.get("/leituras-placa")
def listar_leituras(
    request: Request,
    _: ConsultarOperacao,
    contexto: ContextoDep,
    paginacao: PaginacaoDep,
) -> dict[str, Any]:
    consulta = request.query_params
    filtros: dict[str, Any] = {}
    for nome in ("data_inicio", "data_fim"):
        if nome in consulta:
            try:
                filtros[nome] = date.fromisoformat(consulta[nome])
            except ValueError:
                raise _invalido(nome) from None
    if "decisao" in consulta:
        if consulta["decisao"] not in _DECISOES:
            raise _invalido("decisao")
        filtros["decisao"] = consulta["decisao"]
    if "motivo" in consulta:
        filtros["motivo"] = consulta["motivo"]
    if "pesagem_id" in consulta:
        if not consulta["pesagem_id"].isdigit():
            raise _invalido("pesagem_id")
        filtros["pesagem_id"] = int(consulta["pesagem_id"])
    if "placa" in consulta:
        placa = normalizar_placa_digitada(consulta["placa"])
        if placa is None:
            raise _invalido("placa", "PLACA_INVALIDA")
        filtros["chave_comparacao"] = placa.chave_comparacao
    with transacao(contexto.engine) as t:
        linhas, total = t.leituras_placa.listar(
            filtros,
            str(contexto.configuracao.patio_fuso),
            paginacao.pagina,
            paginacao.tamanho_pagina,
        )
    return {
        "itens": [leitura_resposta(linha) for linha in linhas],
        "total": total,
        "pagina": paginacao.pagina,
        "tamanho_pagina": paginacao.tamanho_pagina,
    }


@router.get("/leituras-placa/{leitura_placa_id}")
def obter_leitura(
    leitura_placa_id: int, _: ConsultarImagens, contexto: ContextoDep
) -> dict[str, Any]:
    with transacao(contexto.engine) as t:
        linha = t.leituras_placa.obter_detalhe(leitura_placa_id)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO")
    return leitura_detalhe(linha)


@router.get("/imagens-decisao/{imagem_id}")
def obter_imagem(
    imagem_id: int, _: ConsultarImagens, contexto: ContextoDep
) -> dict[str, Any]:
    with transacao(contexto.engine) as t:
        linha = t.imagens.obter(imagem_id)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO")
    return _imagem_resposta(linha)


@router.get("/imagens-decisao/{imagem_id}/conteudo")
def conteudo_imagem(
    imagem_id: int, _: ConsultarImagens, contexto: ContextoDep
) -> Response:
    with transacao(contexto.engine) as t:
        linha = t.imagens.obter(imagem_id)
        bytes_ = None if linha is None else t.imagens.conteudo(imagem_id)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO")
    if bytes_ is None:
        raise ErroApi(409, "CONFLITO", [("imagem_id", "IMAGEM_EXCLUIDA")])
    return Response(bytes_, media_type="image/jpeg", headers=_SEM_CACHE)


@router.post("/imagens-decisao/{imagem_id}/excluir")
def excluir_imagem(
    imagem_id: int,
    entrada: ExclusaoEntrada,
    sessao: Annotated[SessaoAtual, Depends(exigir("EXCLUIR_IMAGENS_DECISAO"))],
    contexto: ContextoDep,
) -> dict[str, Any]:
    """RN-022: apaga só os bytes e registra quem, quando e por quê."""
    with transacao(contexto.engine) as t:
        if t.imagens.obter(imagem_id) is None:
            raise ErroApi(404, "NAO_ENCONTRADO")
        if not t.imagens.excluir(
            imagem_id, sessao.usuario.id, entrada.motivo, contexto.agora()
        ):
            raise ErroApi(409, "CONFLITO", [("imagem_id", "IMAGEM_EXCLUIDA")])
        linha = t.imagens.obter(imagem_id)
    return _imagem_resposta(linha)


@router.get("/cameras/{camera}/imagem-atual")
def imagem_atual(
    camera: str,
    _: Annotated[SessaoAtual, Depends(exigir("CONSULTAR_IMAGENS_TEMPO_REAL"))],
    contexto: ContextoDep,
) -> Response:
    """A última imagem analisada daquela fonte; não é salva (ADR-0005 §4.8)."""
    if camera not in ("identificacao", "posicao"):
        raise ErroApi(404, "NAO_ENCONTRADO")
    atual = contexto.orquestracao.imagem_atual(camera)
    if atual is None:
        raise ErroApi(409, "CONFLITO", [("camera", "SEM_IMAGEM")])
    jpeg, capturada_em = atual
    return Response(
        jpeg,
        media_type="image/jpeg",
        headers={
            **_SEM_CACHE,
            "Last-Modified": format_datetime(capturada_em.astimezone(UTC), usegmt=True),
        },
    )


@router.get("/dispositivos")
def dispositivos(_: ConsultarOperacao, contexto: ContextoDep) -> dict[str, Any]:
    return {
        "gerado_em": contexto.agora_patio().isoformat(),
        "intervalo_imagem_ms": contexto.configuracao.operacao.intervalo_imagem_ms,
        "dispositivos": dispositivos_resposta(
            contexto.orquestracao.estado_dispositivos(), contexto.ciclos.parados
        ),
    }
