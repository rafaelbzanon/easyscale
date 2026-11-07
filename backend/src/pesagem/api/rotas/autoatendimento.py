"""Autoatendimento do motorista, sem login (spec 013; RF-033, RN-021, ADR-0004 §4.4).

Cada pedido passa pelas barreiras na ordem da spec 013 §6.2. Nada aqui revela
se uma placa ou um CPF existe: toda falha de cadastro tem a mesma resposta.
"""

from datetime import date, datetime
from ipaddress import ip_address
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationError,
)

from pesagem.api.dependencias import Contexto, ContextoDep, PaginacaoDep, conferir_csrf
from pesagem.api.erros import ErroApi
from pesagem.api.rotas.faixas_horario import montar_disponibilidade
from pesagem.api.senha import resumo
from pesagem.api.validacao import cpf_valido, normalizar_placa_digitada
from pesagem.config import ConfiguracaoAutoatendimento
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.repositorios.agendamento import NovoAgendamento

router = APIRouter(prefix="/api/autoatendimento")


def _cpf(valor: str) -> str:
    if not cpf_valido(valor):
        raise ValueError("CPF inválido")
    return valor


class AutoagendamentoCriacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placa: str
    cpf: Annotated[str, AfterValidator(_cpf)]
    tipo_operacao: Literal["CARGA", "DESCARGA"]
    produto_id: int
    data_prevista: date
    faixa_horario_id: int | None = None
    codigo_nota: Annotated[str, StringConstraints(max_length=100)] | None = None


def _origem(request: Request) -> str:
    # O endereço real do cliente; atrás de proxy, só o repasse do proxy da INT-001 vale.
    return request.client.host if request.client else ""


def _barreira_rede(
    request: Request, contexto: ContextoDep
) -> ConfiguracaoAutoatendimento:
    """Sem redes configuradas, as rotas não existem (404); fora delas, 403 (§6.1)."""
    configuracao = contexto.configuracao.autoatendimento
    if configuracao is None:
        raise ErroApi(404, "NAO_ENCONTRADO")
    try:
        endereco = ip_address(_origem(request))
    except ValueError:
        raise ErroApi(403, "REDE_NAO_PERMITIDA") from None
    if not any(endereco in rede for rede in configuracao.redes):
        raise ErroApi(403, "REDE_NAO_PERMITIDA")
    return configuracao


Rede = Annotated[ConfiguracaoAutoatendimento, Depends(_barreira_rede)]


@router.get("/produtos")
def produtos(
    _: Rede, contexto: ContextoDep, paginacao: PaginacaoDep, busca: str | None = None
) -> dict[str, Any]:
    condicoes = ["ativo"]
    parametros: dict[str, Any] = {}
    if busca is not None:
        escapado = busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        condicoes.append("(codigo ILIKE :busca OR descricao ILIKE :busca)")
        parametros["busca"] = f"%{escapado}%"
    with transacao(contexto.engine) as t:
        linhas, total = t.cadastros.listar(
            "produto",
            "id, codigo, descricao",
            condicoes,
            parametros,
            "descricao, id",
            paginacao.pagina,
            paginacao.tamanho_pagina,
        )
    return {
        "itens": [dict(linha) for linha in linhas],
        "total": total,
        "pagina": paginacao.pagina,
        "tamanho_pagina": paginacao.tamanho_pagina,
    }


@router.get("/disponibilidade")
def disponibilidade(
    _: Rede, contexto: ContextoDep, data: Annotated[date, Query()]
) -> dict[str, Any]:
    return montar_disponibilidade(contexto, data)


@router.post("/agendamentos", status_code=201, response_model=None)
async def criar(
    request: Request, rede: Rede, contexto: ContextoDep
) -> dict[str, Any] | JSONResponse:
    chave = resumo(_origem(request))
    agora = contexto.agora()
    if await run_in_threadpool(_bloqueado, contexto, chave):
        raise ErroApi(429, "AUTOATENDIMENTO_BLOQUEADO")
    erro_csrf = conferir_csrf(
        request, contexto.configuracao.seguranca.origens_permitidas
    )
    if erro_csrf is not None:
        return erro_csrf
    try:
        entrada = AutoagendamentoCriacao.model_validate(await request.json())
    except ValidationError as erro:
        raise RequestValidationError(
            [{**e, "loc": ("body", *e["loc"])} for e in erro.errors()]
        ) from None
    except ValueError:  # corpo que não é JSON
        raise ErroApi(422, "CAMPO_INVALIDO", [("body", "CAMPO_INVALIDO")]) from None
    placa = normalizar_placa_digitada(entrada.placa)
    if placa is None:
        raise ErroApi(422, "CAMPO_INVALIDO", [("placa", "PLACA_INVALIDA")])
    return await run_in_threadpool(
        _criar,
        contexto,
        rede,
        entrada,
        placa.chave_comparacao,
        chave,
        _origem(request),
        agora,
    )


def _bloqueado(contexto: Contexto, chave: str) -> bool:
    with transacao(contexto.engine) as t:
        return t.acesso.esta_bloqueado("AUTOATENDIMENTO", chave, contexto.agora())


def _criar(
    contexto: Contexto,
    rede: ConfiguracaoAutoatendimento,
    entrada: AutoagendamentoCriacao,
    chave_placa: str,
    chave_origem: str,
    endereco: str,
    agora: datetime,
) -> dict[str, Any]:
    patio = contexto.agora_patio()
    with transacao(contexto.engine) as t:
        veiculo = t.veiculos.buscar_ativos_por_placa_e_cpf(chave_placa, entrada.cpf)
        if veiculo is None:
            t.acesso.registrar_falha(
                "AUTOATENDIMENTO",
                chave_origem,
                rede.tentativas_maximas,
                rede.bloqueio_s,
                agora,
            )
            # Só a origem e o instante, nunca o que foi digitado (§6.6).
            t.acesso.auditar(
                "AUTOATENDIMENTO_RECUSADO", agora, endereco_origem=endereco
            )
    # A falha fica gravada antes de responder; por isso a resposta sai fora da transação.
    if veiculo is None:
        raise ErroApi(422, "DADOS_NAO_CONFEREM")
    if entrada.data_prevista < patio.date():
        raise ErroApi(422, "CAMPO_INVALIDO", [("data_prevista", "DATA_NO_PASSADO")])
    if entrada.tipo_operacao == "CARGA" and entrada.codigo_nota is not None:
        raise ErroApi(
            422, "CAMPO_INVALIDO", [("codigo_nota", "CODIGO_NOTA_NAO_PERMITIDO")]
        )
    if entrada.tipo_operacao == "DESCARGA" and not (entrada.codigo_nota or "").strip():
        raise ErroApi(
            422, "CAMPO_INVALIDO", [("codigo_nota", "CODIGO_NOTA_OBRIGATORIO")]
        )
    with transacao(contexto.engine) as t:
        for campo, tabela in (
            ("produto_id", "produto"),
            ("faixa_horario_id", "faixa_horario"),
        ):
            valor = getattr(entrada, campo)
            if valor is not None and not t.cadastros.esta_ativo(tabela, valor):
                raise ErroApi(422, "CAMPO_INVALIDO", [(campo, "CAMPO_INVALIDO")])
        veiculo_id, motorista_id = veiculo
        criado = t.agendamentos.criar_agendamento(
            NovoAgendamento(
                veiculo_id=veiculo_id,
                motorista_id=motorista_id,
                transportadora_id=None,
                produto_id=entrada.produto_id,
                tipo_operacao=entrada.tipo_operacao,
                data_prevista=entrada.data_prevista,
                faixa_horario_id=entrada.faixa_horario_id,
                codigo_nota=entrada.codigo_nota,
                observacao=None,
                origem="AUTOATENDIMENTO",
                criado_por=None,
            ),
            patio.date(),
            patio.time(),
        )
        t.acesso.zerar("AUTOATENDIMENTO", chave_origem)
        linha = t.agendamentos.obter_agendamento(criado.agendamento_id, patio.date())
    # Só o necessário para o motorista conferir, sem dado de cadastro (§5.1).
    return {
        "agendamento_id": linha["id"],
        "tipo_operacao": linha["tipo_operacao"],
        "data_prevista": linha["data_prevista"],
        "faixa_hora_inicio": linha["faixa_hora_inicio"].strftime("%H:%M"),
        "faixa_hora_fim": linha["faixa_hora_fim"].strftime("%H:%M"),
    }
