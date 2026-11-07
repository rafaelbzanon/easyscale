"""Ambiente do Alembic (ADR-0006). Só modo online: as migrações rodam num banco."""

import os

from alembic import context
from sqlalchemy import Connection

from pesagem.config import ler_configuracao_banco
from pesagem.persistencia.banco import criar_engine


def _migrar(conexao: Connection) -> None:
    context.configure(connection=conexao)
    with context.begin_transaction():
        context.run_migrations()


# Os testes passam a conexão; na linha de comando, valem as PESAGEM_BANCO_*.
_conexao = context.config.attributes.get("connection")
if _conexao is not None:
    _migrar(_conexao)
else:
    with criar_engine(ler_configuracao_banco(os.environ)).connect() as conexao:
        _migrar(conexao)
