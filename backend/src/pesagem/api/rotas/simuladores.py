"""Controle dos simuladores (spec 011 §4.2, §6.4). Só registrado com tudo em `SIMULADO`.

Nenhuma rota daqui cria operação, autoriza, aciona cancela ou registra peso:
só muda o que o simulador devolve na próxima leitura ou comando.
"""

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from pesagem.api.dependencias import Contexto, ContextoDep, exigir
from pesagem.api.erros import ErroApi
from pesagem.dispositivos.balanca.simulada import CenarioBalanca
from pesagem.dispositivos.cancela.simulada import CenarioCancela
from pesagem.dominio.operacao.maquina_estados import CancelaPedida
from pesagem.lpr.posicao.simulada import CenarioPosicao
from pesagem.lpr.resultado import TextoOcr
from pesagem.orquestracao.simuladores import Simuladores

router = APIRouter(
    prefix="/api/simuladores", dependencies=[Depends(exigir("CONTROLAR_SIMULADORES"))]
)
_COM_PESO = {
    CenarioBalanca.ESTAVEL,
    CenarioBalanca.INSTAVEL,
    CenarioBalanca.SEM_RESPOSTA_NA_PRIMEIRA,
}


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BalancaEntrada(_Entrada):
    cenario: CenarioBalanca
    peso_kg: Decimal | None
    amplitude_kg: Decimal | None


class CancelaEntrada(_Entrada):
    cenario: CenarioCancela


class PosicaoEntrada(_Entrada):
    cenario: CenarioPosicao


class TextoEntrada(_Entrada):
    texto: str
    confianca: Annotated[Decimal, Field(ge=0, le=1)]


class ChegadaEntrada(_Entrada):
    textos: list[TextoEntrada]


def _simuladores(contexto: Contexto) -> Simuladores:
    # As rotas só existem com simuladores (main.py); a checagem é defesa a mais.
    if contexto.simuladores is None:
        raise ErroApi(404, "NAO_ENCONTRADO")
    return contexto.simuladores


def _cenarios(simuladores: Simuladores) -> dict[str, Any]:
    estado = simuladores.estado()
    com_peso = estado.cenario_balanca in _COM_PESO
    instavel = estado.cenario_balanca is CenarioBalanca.INSTAVEL
    return {
        "balanca": {
            "cenario": estado.cenario_balanca.value,
            "peso_kg": str(estado.peso_kg) if com_peso else None,
            "amplitude_kg": str(estado.amplitude_kg) if instavel else None,
        },
        "cancelas": [
            {"cancela": c.value, "cenario": estado.cenario_cancelas[c].value}
            for c in (CancelaPedida.ENTRADA, CancelaPedida.SAIDA)
        ],
        "posicao": {"cenario": estado.cenario_posicao.value},
        "chegadas_na_fila": estado.chegadas_na_fila,
    }


@router.get("")
def cenarios(contexto: ContextoDep) -> dict[str, Any]:
    return _cenarios(_simuladores(contexto))


@router.post("/balanca")
def definir_balanca(entrada: BalancaEntrada, contexto: ContextoDep) -> dict[str, Any]:
    com_peso = entrada.cenario in _COM_PESO
    if (entrada.peso_kg is None) == com_peso or (
        entrada.peso_kg is not None and not entrada.peso_kg.is_finite()
    ):
        raise ErroApi(422, "CAMPO_INVALIDO", [("peso_kg", "CAMPO_INVALIDO")])
    instavel = entrada.cenario is CenarioBalanca.INSTAVEL
    amplitude = entrada.amplitude_kg
    if (amplitude is None) == instavel or (amplitude is not None and not amplitude > 0):
        raise ErroApi(422, "CAMPO_INVALIDO", [("amplitude_kg", "CAMPO_INVALIDO")])
    simuladores = _simuladores(contexto)
    simuladores.definir_balanca(
        entrada.cenario, entrada.peso_kg or Decimal("0"), amplitude or Decimal("0")
    )
    return _cenarios(simuladores)


@router.post("/cancelas/{cancela}")
def definir_cancela(
    cancela: str, entrada: CancelaEntrada, contexto: ContextoDep
) -> dict[str, Any]:
    if cancela not in ("entrada", "saida"):
        raise ErroApi(404, "NAO_ENCONTRADO")  # spec 011 §6.5
    simuladores = _simuladores(contexto)
    simuladores.definir_cancela(CancelaPedida(cancela.upper()), entrada.cenario)
    return _cenarios(simuladores)


@router.post("/posicao")
def definir_posicao(entrada: PosicaoEntrada, contexto: ContextoDep) -> dict[str, Any]:
    simuladores = _simuladores(contexto)
    simuladores.definir_posicao(entrada.cenario)
    return _cenarios(simuladores)


@router.post("/chegadas", status_code=202)
def simular_chegada(entrada: ChegadaEntrada, contexto: ContextoDep) -> dict[str, Any]:
    """Entra na fila; vira uma leitura sintética no próximo ciclo, pela decisão normal."""
    simuladores = _simuladores(contexto)
    simuladores.simular_chegada(
        [TextoOcr(t.texto, float(t.confianca)) for t in entrada.textos]
    )
    return _cenarios(simuladores)
