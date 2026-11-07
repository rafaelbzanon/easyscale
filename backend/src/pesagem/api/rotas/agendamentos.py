"""Agendamentos (spec 008 §4.1, §5.1, §6; RN-001, RN-013 a RN-015, RN-023, RN-024).

A criação é sempre manual (RN-001): a escolha automática da faixa só acontece
dentro de um pedido de criação feito por uma pessoa.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, StringConstraints

from pesagem.api.dependencias import ContextoDep, PaginacaoDep, exigir
from pesagem.api.erros import ErroApi
from pesagem.api.validacao import normalizar_placa_digitada
from pesagem.persistencia.banco import Transacao, transacao
from pesagem.persistencia.repositorios.agendamento import NovoAgendamento
from pesagem.persistencia.repositorios.usuario import SessaoAtual

router = APIRouter(prefix="/api/agendamentos")
Consultar = Annotated[SessaoAtual, Depends(exigir("CONSULTAR_AGENDAMENTOS"))]
Criar = Annotated[SessaoAtual, Depends(exigir("CRIAR_AGENDAMENTO"))]
Gerenciar = Annotated[SessaoAtual, Depends(exigir("GERENCIAR_AGENDAMENTOS"))]
_Nota = Annotated[str, StringConstraints(max_length=100)]
_Observacao = Annotated[str, StringConstraints(max_length=200)]
_REFERENCIAS = {
    "veiculo_id": "veiculo",
    "motorista_id": "motorista",
    "transportadora_id": "transportadora",
    "produto_id": "produto",
    "faixa_horario_id": "faixa_horario",
}


class AgendamentoCriacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    veiculo_id: int
    motorista_id: int
    transportadora_id: int | None = None
    produto_id: int
    tipo_operacao: Literal["CARGA", "DESCARGA"]
    data_prevista: date
    faixa_horario_id: int | None = None
    codigo_nota: _Nota | None = None
    observacao: _Observacao | None = None


class AgendamentoAlteracao(BaseModel):
    """Os padrões `None` não são validados: um `null` em campo obrigatório dá 422,
    inclusive `faixa_horario_id: null` (spec 008 §6.5)."""

    model_config = ConfigDict(extra="forbid")
    veiculo_id: int = None  # type: ignore[assignment]
    motorista_id: int = None  # type: ignore[assignment]
    transportadora_id: int | None = None
    produto_id: int = None  # type: ignore[assignment]
    tipo_operacao: Literal["CARGA", "DESCARGA"] = None  # type: ignore[assignment]
    data_prevista: date = None  # type: ignore[assignment]
    faixa_horario_id: int = None  # type: ignore[assignment]
    codigo_nota: _Nota | None = None
    observacao: _Observacao | None = None


class Cancelamento(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    # Só espaços não é motivo (RN-013, spec 008 §6.5).
    motivo: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]


def resposta(linha: Any) -> dict[str, Any]:
    """Sem CPF (RNF-013); horas em `HH:MM`."""
    dados = dict(linha)
    for campo in ("faixa_hora_inicio", "faixa_hora_fim"):
        dados[campo] = dados[campo].strftime("%H:%M")
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in dados.items()}


def conferir_entrada(t: Transacao, campos: dict[str, Any], hoje: date) -> None:
    if "data_prevista" in campos and campos["data_prevista"] < hoje:
        raise ErroApi(422, "CAMPO_INVALIDO", [("data_prevista", "DATA_NO_PASSADO")])
    for campo, tabela in _REFERENCIAS.items():
        if campos.get(campo) is not None and not t.cadastros.esta_ativo(
            tabela, campos[campo]
        ):
            raise ErroApi(422, "CAMPO_INVALIDO", [(campo, "CAMPO_INVALIDO")])


@router.get("")
def listar(
    request: Request, _: Consultar, contexto: ContextoDep, paginacao: PaginacaoDep
) -> dict[str, Any]:
    consulta = request.query_params
    filtros: dict[str, Any] = {}
    try:
        for nome in ("data_inicio", "data_fim"):
            if nome in consulta:
                filtros[nome] = date.fromisoformat(consulta[nome])
    except ValueError:
        raise ErroApi(422, "CAMPO_INVALIDO", [(nome, "CAMPO_INVALIDO")]) from None
    for nome in ("status", "tipo_operacao", "origem"):
        if nome in consulta:
            filtros[nome] = consulta[nome]
    if "placa" in consulta:
        placa = normalizar_placa_digitada(consulta["placa"])
        if placa is None:
            raise ErroApi(422, "CAMPO_INVALIDO", [("placa", "PLACA_INVALIDA")])
        filtros["chave_comparacao"] = placa.chave_comparacao
    with transacao(contexto.engine) as t:
        linhas, total = t.agendamentos.listar_agendamentos(
            filtros,
            contexto.agora_patio().date(),
            paginacao.pagina,
            paginacao.tamanho_pagina,
        )
    return {
        "itens": [resposta(linha) for linha in linhas],
        "total": total,
        "pagina": paginacao.pagina,
        "tamanho_pagina": paginacao.tamanho_pagina,
    }


@router.get("/{agendamento_id}")
def obter(agendamento_id: int, _: Consultar, contexto: ContextoDep) -> dict[str, Any]:
    with transacao(contexto.engine) as t:
        linha = t.agendamentos.obter_agendamento(
            agendamento_id, contexto.agora_patio().date()
        )
    return resposta(linha)


@router.post("", status_code=201)
def criar(
    entrada: AgendamentoCriacao, sessao: Criar, contexto: ContextoDep
) -> dict[str, Any]:
    agora = contexto.agora_patio()
    hoje = agora.date()
    if entrada.tipo_operacao == "CARGA" and entrada.codigo_nota is not None:
        raise ErroApi(
            422, "CAMPO_INVALIDO", [("codigo_nota", "CODIGO_NOTA_NAO_PERMITIDO")]
        )
    with transacao(contexto.engine) as t:
        conferir_entrada(t, entrada.model_dump(), hoje)
        criado = t.agendamentos.criar_agendamento(
            NovoAgendamento(
                **entrada.model_dump(), origem="USUARIO", criado_por=sessao.usuario.id
            ),
            hoje,
            agora.time(),
        )
        linha = t.agendamentos.obter_agendamento(criado.agendamento_id, hoje)
    return resposta(linha)


@router.patch("/{agendamento_id}")
def alterar(
    agendamento_id: int,
    entrada: AgendamentoAlteracao,
    sessao: Gerenciar,
    contexto: ContextoDep,
) -> dict[str, Any]:
    agora = contexto.agora_patio()
    campos = entrada.model_dump(exclude_unset=True)
    with transacao(contexto.engine) as t:
        conferir_entrada(t, campos, agora.date())
        t.agendamentos.alterar_agendamento(
            agendamento_id, campos, agora.date(), agora.time(), sessao.usuario.id, agora
        )
        linha = t.agendamentos.obter_agendamento(agendamento_id, agora.date())
    return resposta(linha)


@router.post("/{agendamento_id}/cancelar")
def cancelar(
    agendamento_id: int, entrada: Cancelamento, sessao: Gerenciar, contexto: ContextoDep
) -> dict[str, Any]:
    agora = contexto.agora_patio()
    with transacao(contexto.engine) as t:
        t.agendamentos.obter_agendamento(
            agendamento_id, agora.date()
        )  # 404 antes do 409
        t.agendamentos.cancelar_agendamento(
            agendamento_id, sessao.usuario.id, entrada.motivo, agora.date(), agora
        )
        linha = t.agendamentos.obter_agendamento(agendamento_id, agora.date())
    return resposta(linha)
