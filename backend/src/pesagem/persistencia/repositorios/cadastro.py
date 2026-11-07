"""Cadastros simples: transportadora, motorista, tipo de veículo, veículo e produto (spec 007).

Tabelas e colunas vêm de constantes do código (`api/cadastros.py`), nunca de
fora; os valores vão sempre como parâmetro.
"""

from typing import Any

from sqlalchemy import Connection, RowMapping, text

from pesagem.persistencia.erros import ErroNaoEncontrado

TABELAS = frozenset(
    {"transportadora", "motorista", "tipo_veiculo", "veiculo", "produto"}
)

# Cadastro ligado a uma operação aberta (spec 007 §6.3, RN-008).
_OPERACAO_ABERTA = {
    "veiculo": "p.veiculo_id = :id",
    "motorista": "p.motorista_id = :id",
    "transportadora": "a.transportadora_id = :id",
}


class RepositorioCadastro:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def listar(
        self,
        tabela: str,
        colunas: str,
        condicoes: list[str],
        parametros: dict[str, Any],
        ordem: str,
        pagina: int,
        tamanho_pagina: int,
    ) -> tuple[list[RowMapping], int]:
        assert tabela in TABELAS
        onde = " AND ".join(condicoes) or "TRUE"
        linhas = (
            self._conexao.execute(
                text(
                    f"SELECT {colunas} FROM {tabela} WHERE {onde} ORDER BY {ordem} "
                    "LIMIT :limite OFFSET :deslocamento"
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
            text(f"SELECT count(*) FROM {tabela} WHERE {onde}"), parametros
        ).scalar_one()
        return list(linhas), int(total)

    def obter(self, tabela: str, colunas: str, item_id: int) -> RowMapping:
        assert tabela in TABELAS
        linha = (
            self._conexao.execute(
                text(f"SELECT {colunas} FROM {tabela} WHERE id = :id"), {"id": item_id}
            )
            .mappings()
            .one_or_none()
        )
        if linha is None:
            raise ErroNaoEncontrado(f"{tabela} {item_id}")
        return linha

    def inserir(self, tabela: str, campos: dict[str, Any]) -> int:
        assert tabela in TABELAS
        nomes = ", ".join(campos)
        valores = ", ".join(f":{n}" for n in campos)
        return int(
            self._conexao.execute(
                text(f"INSERT INTO {tabela} ({nomes}) VALUES ({valores}) RETURNING id"),
                campos,
            ).scalar_one()
        )

    def alterar(self, tabela: str, item_id: int, campos: dict[str, Any]) -> None:
        assert tabela in TABELAS
        if campos:
            atribuicoes = ", ".join(f"{n} = :{n}" for n in campos)
            self._conexao.execute(
                text(f"UPDATE {tabela} SET {atribuicoes} WHERE id = :id"),
                {**campos, "id": item_id},
            )

    def esta_ativo(self, tabela: str, item_id: int) -> bool:
        """Existe e está ativo.

        Sem `FOR SHARE`: a criação do agendamento trava a faixa com `FOR UPDATE`, e
        subir de uma trava para a outra em dois pedidos ao mesmo tempo dá impasse.
        """
        assert tabela in TABELAS or tabela == "faixa_horario"
        ativo = self._conexao.execute(
            text(f"SELECT ativo FROM {tabela} WHERE id = :id"),
            {"id": item_id},
        ).scalar_one_or_none()
        return bool(ativo)

    def tem_operacao_aberta(self, tabela: str, item_id: int) -> bool:
        return bool(
            self._conexao.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pesagem p JOIN agendamento a "
                    f"ON a.id = p.agendamento_id WHERE {_OPERACAO_ABERTA[tabela]} "
                    "AND p.situacao NOT IN ('FINALIZADA', 'CANCELADA'))"
                ),
                {"id": item_id},
            ).scalar_one()
        )
