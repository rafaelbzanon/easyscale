"""Comando de cancela com 0 tentativas (spec 010 §5.2, spec 004): o sensor sem
resposta impede o envio, e o registro mostra que nada foi enviado.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_RESTRICAO = """
ALTER TABLE evento_operacao DROP CONSTRAINT ck_evento_operacao_cancela_valores;
ALTER TABLE evento_operacao ADD CONSTRAINT ck_evento_operacao_cancela_valores CHECK (
  cancela IN ('ENTRADA', 'SAIDA') AND comando IN ('ABRIR', 'FECHAR')
  AND resultado IN ('CONFIRMADO', 'FALHA', 'SEM_CONFIRMACAO') AND tentativas >= {minimo});
"""


def upgrade() -> None:
    op.execute(_RESTRICAO.format(minimo=0))


def downgrade() -> None:
    op.execute(_RESTRICAO.format(minimo=1))
