"""Faixas de horário (spec 008 §4.2, §5.2, §5.3, §6.7; RN-015, RN-024)."""

from dataclasses import dataclass
from datetime import date, time
from typing import Any

from sqlalchemy import Connection, RowMapping, text

from pesagem.persistencia.erros import ErroFaixaComAgendamentos, ErroNaoEncontrado

_COLUNAS = "id, hora_inicio, hora_fim, capacidade, ativo"


@dataclass(frozen=True)
class Disponibilidade:
    faixa_horario_id: int
    hora_inicio: time
    hora_fim: time
    capacidade: int
    vagas_ocupadas: int
    encerrada: bool


class RepositorioFaixaHorario:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def listar(
        self, ativo: bool | None, pagina: int, tamanho_pagina: int
    ) -> tuple[list[RowMapping], int]:
        onde = "CAST(:ativo AS BOOLEAN) IS NULL OR ativo = :ativo"
        linhas = (
            self._conexao.execute(
                text(
                    f"SELECT {_COLUNAS} FROM faixa_horario WHERE {onde} "
                    "ORDER BY hora_inicio, id LIMIT :limite OFFSET :deslocamento"
                ),
                {
                    "ativo": ativo,
                    "limite": tamanho_pagina,
                    "deslocamento": (pagina - 1) * tamanho_pagina,
                },
            )
            .mappings()
            .all()
        )
        total = self._conexao.execute(
            text(f"SELECT count(*) FROM faixa_horario WHERE {onde}"), {"ativo": ativo}
        ).scalar_one()
        return list(linhas), int(total)

    def obter(self, faixa_id: int) -> RowMapping:
        linha = (
            self._conexao.execute(
                text(f"SELECT {_COLUNAS} FROM faixa_horario WHERE id = :id"),
                {"id": faixa_id},
            )
            .mappings()
            .one_or_none()
        )
        if linha is None:
            raise ErroNaoEncontrado(str(faixa_id))
        return linha

    def criar(self, hora_inicio: time, hora_fim: time, capacidade: int) -> int:
        """Sobreposição entre ativas: restrição `ex_faixa_horario_sobreposta`."""
        return int(
            self._conexao.execute(
                text(
                    "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade) "
                    "VALUES (:i, :f, :c) RETURNING id"
                ),
                {"i": hora_inicio, "f": hora_fim, "c": capacidade},
            ).scalar_one()
        )

    def alterar(self, faixa_id: int, campos: dict[str, Any], hoje: date) -> None:
        """Horário não muda com agendamento ativo de hoje em diante (spec 008 §6.7)."""
        self.obter(faixa_id)
        if {"hora_inicio", "hora_fim"} & set(campos):
            ocupada = self._conexao.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM agendamento WHERE faixa_horario_id = :f "
                    "AND status IN ('AGENDADO', 'EM_ANDAMENTO') AND data_prevista >= :hoje)"
                ),
                {"f": faixa_id, "hoje": hoje},
            ).scalar_one()
            if ocupada:
                raise ErroFaixaComAgendamentos(str(faixa_id))
        if campos:
            atribuicoes = ", ".join(f"{nome} = :{nome}" for nome in campos)
            self._conexao.execute(
                text(f"UPDATE faixa_horario SET {atribuicoes} WHERE id = :id"),
                {**campos, "id": faixa_id},
            )

    def disponibilidade(
        self, data: date, hoje: date, hora_atual: time
    ) -> list[Disponibilidade]:
        linhas = self._conexao.execute(
            text(
                "SELECT f.id, f.hora_inicio, f.hora_fim, f.capacidade, "
                "count(a.id) FILTER (WHERE a.status IN ('AGENDADO', 'EM_ANDAMENTO', "
                "'CONCLUIDO')) FROM faixa_horario f LEFT JOIN agendamento a "
                "ON a.faixa_horario_id = f.id AND a.data_prevista = :d WHERE f.ativo "
                "GROUP BY f.id ORDER BY f.hora_inicio, f.id"
            ),
            {"d": data},
        ).all()
        return [
            Disponibilidade(
                faixa_id,
                inicio,
                fim,
                capacidade,
                int(ocupadas),
                encerrada=data == hoje and hora_atual >= fim,
            )
            for faixa_id, inicio, fim, capacidade, ocupadas in linhas
        ]
