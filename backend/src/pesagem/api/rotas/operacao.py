"""Operação em tempo real e intervenções manuais (spec 009; spec 006 §5.3, §9).

Nenhuma rota abre ou fecha cancela direto nem recebe peso: toda ação vai à
máquina de estados pela orquestração (RN-007, RN-004). Quem decide é o backend.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, StringConstraints

from pesagem.api.dependencias import Contexto, ContextoDep, buscar_sessao, exigir
from pesagem.api.erros import ErroApi
from pesagem.api.esquemas.operacao import (
    cancela_resposta,
    dispositivos_resposta,
    jsonavel,
    leitura_do_evento,
    leitura_resposta,
    liberacao_resposta,
)
from pesagem.api.esquemas.pesagens import pesagem_resposta
from pesagem.dominio.operacao.maquina_estados import (
    AcaoManual,
    Operacao,
    TipoAcaoManual,
    TransicaoAplicada,
)
from pesagem.orquestracao.erros import ErroLiberacaoEntrada, ErroOperacaoNaoOcupaBalanca
from pesagem.orquestracao.eventos import (
    Evento,
    EventoCancela,
    EventoLeituraPlaca,
    EventoLiberacaoCaminhao,
    EventoOperacao,
    EventoPesoLido,
)
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.erros import ErroLeituraJaUsada, ErroOperacaoAberta
from pesagem.persistencia.repositorios.usuario import SessaoAtual

router = APIRouter()
# Só espaços não é motivo (RN-011, spec 009 §6.3, CA-014).
_Motivo = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
_CAMPO_DA_LIBERACAO = {
    "LEITURA_DESATUALIZADA": "leitura_placa_id",
    "LEITURA_NAO_LIBERAVEL": "leitura_placa_id",
    "MOTIVO_NAO_SUBSTITUIVEL": "leitura_placa_id",
}
_NOME_EVENTO = {
    "EventoOperacao": "pesagem",
    "EventoLeituraPlaca": "leitura_placa",
    "EventoPesoLido": "peso_lido",
    "EventoBalanca": "balanca",
    "EventoCancela": "cancela",
    "EventoPosicao": "posicao",
    "EventoIdentificacao": "identificacao",
    "EventoLiberacaoCaminhao": "liberacao_caminhao",
}


class AcaoEntrada(BaseModel):
    """Sem campo de peso nem de responsável (spec 009 §6.3)."""

    model_config = ConfigDict(extra="forbid", strict=True)
    versao: int
    motivo: _Motivo


class MotivoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    motivo: _Motivo


class LiberacaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    agendamento_id: int
    motivo: _Motivo


def _pesagem_da_transicao(
    contexto: Contexto, pesagem_id: int, operacao: Operacao
) -> dict[str, Any]:
    """A Pesagem como a transição a gravou, antes do resultado do comando (spec 009
    §6.3: 200 quer dizer transição gravada, não cancela movida)."""
    with transacao(contexto.engine) as t:
        linha = dict(t.pesagens.obter_resumo(pesagem_id, contexto.agora_patio().date()))
    campos = (
        "versao",
        "situacao",
        "situacao_anterior",
        "motivo_intervencao",
        "peso_inicial_kg",
        "peso_inicial_em",
        "peso_final_kg",
        "peso_final_em",
        "peso_liquido_kg",
        "classificacao",
        "liberacao_manual",
    )
    return pesagem_resposta({**linha, **{c: getattr(operacao, c) for c in campos}})


def _pesagem(contexto: Contexto, pesagem_id: int) -> dict[str, Any]:
    with transacao(contexto.engine) as t:
        return pesagem_resposta(
            t.pesagens.obter_resumo(pesagem_id, contexto.agora_patio().date())
        )


# ------------------------------------------------------------------ consulta


@router.get("/api/operacao/estado")
def estado(
    _: Annotated[SessaoAtual, Depends(exigir("CONSULTAR_OPERACAO"))],
    contexto: ContextoDep,
) -> dict[str, Any]:
    """Spec 009 §5.5: a verdade vem daqui; o canal só avisa (ADR-0005)."""
    agora = contexto.agora_patio()
    with transacao(contexto.engine) as t:
        abertas, _total = t.pesagens.listar_historico(
            {"aberta": True},
            str(contexto.configuracao.patio_fuso),
            agora.date(),
            1,
            10_000,
        )
        liberacoes = t.pesagens.listar_liberacoes_pendentes()
        ultima = t.leituras_placa.ultima()
    operacao = contexto.configuracao.operacao
    return {
        "gerado_em": agora.isoformat(),
        "tempo_real": {
            "intervalo_heartbeat_ms": operacao.heartbeat_ms,
            "limite_sem_heartbeat_ms": operacao.limite_sem_heartbeat_ms,
        },
        # Ordem de chegada: a lista do histórico vem do mais recente ao mais antigo.
        "pesagens_abertas": [pesagem_resposta(p) for p in reversed(abertas)],
        "liberacoes_caminhao": [liberacao_resposta(item) for item in liberacoes],
        "ultima_leitura_placa": None if ultima is None else leitura_resposta(ultima),
        "dispositivos": dispositivos_resposta(
            contexto.orquestracao.estado_dispositivos(), contexto.ciclos.parados
        ),
    }


@router.get("/api/pesagens/{pesagem_id}")
def obter(
    pesagem_id: int,
    _: Annotated[SessaoAtual, Depends(exigir("CONSULTAR_OPERACAO"))],
    contexto: ContextoDep,
) -> dict[str, Any]:
    return _pesagem(contexto, pesagem_id)


def _dados_do_evento(contexto: Contexto, evento: Evento) -> Any:
    match evento:
        case EventoOperacao():
            return _pesagem(contexto, evento.operacao.pesagem_id)
        case EventoLeituraPlaca():
            return leitura_do_evento(evento.leitura_placa_id, evento.leitura)
        case EventoPesoLido():
            return jsonavel({"peso_kg": evento.peso_kg, "lida_em": evento.lida_em})
        case EventoLiberacaoCaminhao():
            liberacao = jsonavel(evento.liberacao)
            nome = None
            if evento.liberacao.pedido_por is not None:
                with transacao(contexto.engine) as t:
                    nome = t.usuarios.obter_usuario(evento.liberacao.pedido_por).nome
            return {**liberacao, "pedido_por_nome": nome}
        case EventoCancela():
            return cancela_resposta(evento.estado)
        case _:
            return jsonavel(evento.estado)


def _mensagem(nome: str, dados: Any) -> str:
    linha = json.dumps(jsonavel(dados), separators=(",", ":"))
    return f"event: {nome}\ndata: {linha}\n\n"


@router.get("/api/operacao/eventos")
async def eventos(request: Request, contexto: ContextoDep) -> StreamingResponse:
    """SSE só de leitura (spec 009 §6.1). Não renova a sessão e fecha quando ela acaba."""
    sessao = await run_in_threadpool(buscar_sessao, request, contexto, False)
    if sessao is None:
        raise ErroApi(401, "NAO_AUTENTICADO")
    if "CONSULTAR_OPERACAO" not in sessao.permissoes:
        raise ErroApi(403, "SEM_PERMISSAO")
    intervalo = contexto.configuracao.operacao.heartbeat_ms / 1000
    fila = contexto.distribuidor.assinar()

    async def gerar() -> AsyncIterator[str]:
        try:
            ultimo_heartbeat = -intervalo
            while True:
                agora = time.monotonic()
                if agora - ultimo_heartbeat >= intervalo:
                    # A cada heartbeat: cliente ainda ligado e sessão ainda válida.
                    if (
                        await request.is_disconnected()
                        or await run_in_threadpool(
                            buscar_sessao, request, contexto, False
                        )
                        is None
                    ):
                        return
                    yield _mensagem(
                        "heartbeat", {"enviado_em": contexto.agora().isoformat()}
                    )
                    ultimo_heartbeat = agora
                espera = max(0.0, intervalo - (time.monotonic() - ultimo_heartbeat))
                try:
                    evento = await asyncio.wait_for(fila.get(), timeout=espera)
                except TimeoutError:
                    continue
                dados = await run_in_threadpool(_dados_do_evento, contexto, evento)
                yield _mensagem(_NOME_EVENTO[type(evento).__name__], dados)
        finally:
            contexto.distribuidor.cancelar(fila)

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------- ações


def _rota_acao(caminho: str, tipo: TipoAcaoManual, permissao: str) -> None:
    @router.post(f"/api/pesagens/{{pesagem_id}}/{caminho}", name=caminho)
    async def acao(
        pesagem_id: int,
        entrada: AcaoEntrada,
        sessao: Annotated[SessaoAtual, Depends(exigir(permissao))],
        contexto: ContextoDep,
    ) -> dict[str, Any]:
        usuario = sessao.usuario
        resultado = await contexto.orquestracao.aplicar_acao_manual(
            pesagem_id,
            entrada.versao,
            AcaoManual(tipo, responsavel=str(usuario.id), motivo=entrada.motivo),
            usuario.id,
        )
        if not isinstance(resultado, TransicaoAplicada):
            raise ErroApi(409, "CONFLITO", [("situacao", "TRANSICAO_REJEITADA")])
        return await run_in_threadpool(
            _pesagem_da_transicao, contexto, pesagem_id, resultado.operacao
        )


for _caminho, _tipo, _permissao in (
    ("tentar-novamente", TipoAcaoManual.TENTAR_NOVAMENTE, "TENTAR_NOVAMENTE"),
    ("confirmar-posicao", TipoAcaoManual.CONFIRMAR_POSICAO_MANUAL, "INTERVIR_OPERACAO"),
    (
        "confirmar-balanca-vazia",
        TipoAcaoManual.CONFIRMAR_BALANCA_VAZIA_MANUAL,
        "INTERVIR_OPERACAO",
    ),
    ("liberar-retorno", TipoAcaoManual.LIBERAR_RETORNO_MANUAL, "INTERVIR_OPERACAO"),
    ("aceitar-peso-final", TipoAcaoManual.ACEITAR_PESO_FINAL, "INTERVIR_OPERACAO"),
    ("cancelar", TipoAcaoManual.CANCELAR, "INTERVIR_OPERACAO"),
):
    _rota_acao(_caminho, _tipo, _permissao)


@router.post("/api/pesagens/{pesagem_id}/liberar-caminhao")
async def liberar_caminhao(
    pesagem_id: int,
    entrada: MotivoEntrada,
    sessao: Annotated[SessaoAtual, Depends(exigir("LIBERAR_CAMINHAO_CANCELADO"))],
    contexto: ContextoDep,
) -> dict[str, Any]:
    """RN-020 (spec 009 §6.6): a orquestração comanda a saída e informa as etapas."""
    try:
        await contexto.orquestracao.liberar_caminhao_cancelado(
            pesagem_id, sessao.usuario.id, entrada.motivo
        )
    except ErroOperacaoNaoOcupaBalanca:
        raise ErroApi(
            409, "CONFLITO", [("pesagem_id", "OPERACAO_NAO_OCUPA_BALANCA")]
        ) from None
    return await run_in_threadpool(_pesagem, contexto, pesagem_id)


@router.post("/api/leituras-placa/{leitura_placa_id}/liberar-entrada", status_code=201)
async def liberar_entrada(
    leitura_placa_id: int,
    entrada: LiberacaoEntrada,
    sessao: Annotated[SessaoAtual, Depends(exigir("INTERVIR_OPERACAO"))],
    contexto: ContextoDep,
) -> dict[str, Any]:
    """RN-016 (spec 009 §6.5): só substitui a identificação e o horário da faixa."""

    def existe() -> bool:
        with transacao(contexto.engine) as t:
            return t.leituras_placa.buscar(leitura_placa_id) is not None

    if not await run_in_threadpool(existe):
        raise ErroApi(404, "NAO_ENCONTRADO")
    try:
        criada = await contexto.orquestracao.liberar_entrada_manual(
            leitura_placa_id, entrada.agendamento_id, sessao.usuario.id, entrada.motivo
        )
    except ErroLiberacaoEntrada as erro:
        campo = _CAMPO_DA_LIBERACAO.get(erro.codigo, "agendamento_id")
        raise ErroApi(409, "CONFLITO", [(campo, erro.codigo)]) from None
    except ErroLeituraJaUsada:
        raise ErroApi(
            409, "CONFLITO", [("leitura_placa_id", "LEITURA_NAO_LIBERAVEL")]
        ) from None
    except ErroOperacaoAberta:
        raise ErroApi(
            409, "CONFLITO", [("agendamento_id", "OPERACAO_JA_ABERTA")]
        ) from None
    return await run_in_threadpool(_pesagem, contexto, criada.pesagem_id)
