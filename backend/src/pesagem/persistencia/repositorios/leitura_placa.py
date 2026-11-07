"""Leituras de placa e a decisão tomada com elas (spec 015; RN-003, RF-022)."""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Connection, RowMapping, text

type Json = dict[str, Json] | list[Json] | str | int | float | bool | None


@dataclass(frozen=True)
class NovaLeituraPlaca:
    origem: str
    capturada_em: datetime
    decidida_em: datetime
    decisao: str
    leituras: Json
    pesagem_id: int | None = None
    agendamento_id: int | None = None
    motivo: str | None = None
    placa_lida: str | None = None
    placa_normalizada: str | None = None
    chave_comparacao: str | None = None
    formato: str | None = None
    correcoes: Json = None
    confianca: Decimal | None = None
    imagem_id: int | None = None


# Campos da LeituraPlaca (spec 009 §5.2) e as interpretações (spec 011 §5.2).
_RESUMO = (
    "id, decisao, motivo, placa_lida, placa_normalizada, confianca, pesagem_id, "
    "agendamento_id, imagem_id, capturada_em, decidida_em"
)
_FILTROS = {
    "data_inicio": "(decidida_em AT TIME ZONE :fuso)::date >= :data_inicio",
    "data_fim": "(decidida_em AT TIME ZONE :fuso)::date <= :data_fim",
    "decisao": "decisao = :decisao",
    "motivo": "motivo = :motivo",
    "pesagem_id": "pesagem_id = :pesagem_id",
    "chave_comparacao": "chave_comparacao = :chave_comparacao",
}


@dataclass(frozen=True)
class LeituraPlacaRegistrada:
    leitura_placa_id: int
    decisao: str
    pesagem_id: int | None
    agendamento_id: int | None


class RepositorioLeituraPlaca:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def registrar(self, leitura: NovaLeituraPlaca) -> int:
        campos = {
            **leitura.__dict__,
            "leituras": json.dumps(leitura.leituras),
            "correcoes": None
            if leitura.correcoes is None
            else json.dumps(leitura.correcoes),
        }
        id_criado: int = self._conexao.execute(
            text(
                "INSERT INTO leitura_placa (origem, capturada_em, decidida_em, decisao, "
                "leituras, pesagem_id, agendamento_id, motivo, placa_lida, "
                "placa_normalizada, chave_comparacao, formato, correcoes, confianca, imagem_id) "
                "VALUES "
                "(:origem, :capturada_em, :decidida_em, :decisao, CAST(:leituras AS JSONB), "
                ":pesagem_id, :agendamento_id, :motivo, :placa_lida, :placa_normalizada, :chave_comparacao, "
                ":formato, CAST(:correcoes AS JSONB), :confianca, :imagem_id) RETURNING id"
            ),
            campos,
        ).scalar_one()
        return id_criado

    def buscar(self, leitura_placa_id: int) -> LeituraPlacaRegistrada | None:
        linha = self._conexao.execute(
            text(
                "SELECT id, decisao, pesagem_id, agendamento_id FROM leitura_placa "
                "WHERE id = :id"
            ),
            {"id": leitura_placa_id},
        ).one_or_none()
        return None if linha is None else LeituraPlacaRegistrada(*linha)

    def ultima(self) -> RowMapping | None:
        """A mais recente registrada: a única que a liberação manual aceita (spec 009 §6.5)."""
        return (
            self._conexao.execute(
                text(
                    f"SELECT {_RESUMO} FROM leitura_placa ORDER BY decidida_em DESC, id DESC LIMIT 1"
                )
            )
            .mappings()
            .one_or_none()
        )

    def obter_detalhe(self, leitura_placa_id: int) -> RowMapping | None:
        return (
            self._conexao.execute(
                text(
                    f"SELECT {_RESUMO}, formato, correcoes, origem, leituras "
                    "FROM leitura_placa WHERE id = :id"
                ),
                {"id": leitura_placa_id},
            )
            .mappings()
            .one_or_none()
        )

    def listar(
        self, filtros: dict[str, Any], fuso: str, pagina: int, tamanho_pagina: int
    ) -> tuple[list[RowMapping], int]:
        """Spec 011 §5.1: da mais recente à mais antiga."""
        onde = " AND ".join(_FILTROS[nome] for nome in filtros) or "TRUE"
        parametros = {**filtros, "fuso": fuso}
        linhas = (
            self._conexao.execute(
                text(
                    f"SELECT {_RESUMO} FROM leitura_placa WHERE {onde} "
                    "ORDER BY decidida_em DESC, id DESC LIMIT :limite OFFSET :deslocamento"
                ),
                {
                    **parametros,
                    "limite": tamanho_pagina,
                    "deslocamento": (pagina - 1) * tamanho_pagina,
                },
            )
            .mappings()
            .all()
        )
        total = self._conexao.execute(
            text(f"SELECT count(*) FROM leitura_placa WHERE {onde}"), parametros
        ).scalar_one()
        return list(linhas), int(total)
