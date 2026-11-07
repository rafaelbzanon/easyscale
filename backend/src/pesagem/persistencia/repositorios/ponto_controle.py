"""Ponto de controle: uma balança por enquanto (RF-030; Q-12)."""

from sqlalchemy import Connection, text

from pesagem.persistencia.erros import ErroPersistencia


class RepositorioPontoControle:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def obter_unico(self) -> int:
        """Id do único ponto ativo; zero ou mais de um é erro, sem escolher sozinho."""
        ids = (
            self._conexao.execute(text("SELECT id FROM ponto_controle WHERE ativo"))
            .scalars()
            .all()
        )
        if len(ids) != 1:
            raise ErroPersistencia(f"pontos de controle ativos: {len(ids)}")
        return int(ids[0])
