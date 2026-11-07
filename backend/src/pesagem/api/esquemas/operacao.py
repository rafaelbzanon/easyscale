"""Formas da operação em tempo real (spec 009 §5.2, §5.4, §5.6) e do diagnóstico (011)."""

import dataclasses
from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Any

from pesagem.orquestracao.eventos import EstadoCancelaConhecido, EstadoDispositivos
from pesagem.persistencia.repositorios.leitura_placa import NovaLeituraPlaca

_CAMPOS_LEITURA = (
    "decisao",
    "motivo",
    "placa_lida",
    "placa_normalizada",
    "confianca",
    "pesagem_id",
    "agendamento_id",
    "imagem_id",
    "capturada_em",
    "decidida_em",
)


def jsonavel(valor: Any) -> Any:
    """Decimal como texto (spec 007 §3.1), instante em ISO 8601, enum pelo valor."""
    if dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        return {
            c.name: jsonavel(getattr(valor, c.name)) for c in dataclasses.fields(valor)
        }
    if isinstance(valor, dict):
        return {k: jsonavel(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [jsonavel(v) for v in valor]
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, date | time):  # inclui datetime
        return valor.isoformat()
    if isinstance(valor, Enum):
        return valor.value
    return valor


def _objeto(valor: dict[str, Any]) -> dict[str, Any]:
    convertido: dict[str, Any] = jsonavel(valor)
    return convertido


def leitura_resposta(linha: Any) -> dict[str, Any]:
    """`LeituraPlaca` da spec 009 §5.2."""
    return _objeto({"id": linha["id"], **{c: linha[c] for c in _CAMPOS_LEITURA}})


def leitura_detalhe(linha: Any) -> dict[str, Any]:
    """Spec 011 §5.2: mais as interpretações; `correcoes` vazia sem placa."""
    return {
        **leitura_resposta(linha),
        "formato": linha["formato"],
        "correcoes": linha["correcoes"] or [],
        "origem": linha["origem"],
        "leituras": linha["leituras"],
    }


def leitura_do_evento(
    leitura_placa_id: int, leitura: NovaLeituraPlaca
) -> dict[str, Any]:
    return _objeto(
        {"id": leitura_placa_id, **{c: getattr(leitura, c) for c in _CAMPOS_LEITURA}}
    )


def liberacao_resposta(linha: Any) -> dict[str, Any]:
    """`LiberacaoCaminhao` da spec 009 §5.6."""
    return _objeto(dict(linha))


def cancela_resposta(
    estado: EstadoCancelaConhecido, parado: bool = False
) -> dict[str, Any]:
    """Sem leitura do sensor, o estado é `DESCONHECIDO` (spec 009 §5.4), nunca nulo."""
    dados = _objeto(dataclasses.asdict(estado))
    if parado or dados["estado"] is None:
        dados["estado"] = "DESCONHECIDO"
    return dados


def dispositivos_resposta(estado: EstadoDispositivos, parado: bool) -> dict[str, Any]:
    """Spec 009 §5.4. Com os ciclos parados (main.py), nada pode parecer em ordem:
    balança e cancelas `DESCONHECIDO`, posição `INCONCLUSIVA` (fail-safe)."""
    dados = _objeto(dataclasses.asdict(estado))
    dados["cancelas"] = [cancela_resposta(c, parado) for c in estado.cancelas]
    if parado:
        dados["balanca"] = {
            **dados["balanca"],
            "comunicacao": "DESCONHECIDO",
            "motivo_falha": None,
        }
        dados["posicao"] = {**dados["posicao"], "resultado": "INCONCLUSIVA"}
    return dados
