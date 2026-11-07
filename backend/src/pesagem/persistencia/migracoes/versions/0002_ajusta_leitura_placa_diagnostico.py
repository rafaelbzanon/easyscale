"""Ajustes do contrato 011 (diagnóstico) em leitura_placa e imagem_decisao.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Filtro por placa pela chave de comparação (spec 003), gravada pela orquestração.
    op.execute("""
ALTER TABLE leitura_placa ADD COLUMN chave_comparacao VARCHAR(7);
CREATE INDEX ix_leitura_placa_chave_comparacao ON leitura_placa (chave_comparacao);
ALTER TABLE imagem_decisao ALTER COLUMN motivo_exclusao TYPE VARCHAR(200);
""")


def downgrade() -> None:
    op.execute("""
ALTER TABLE imagem_decisao ALTER COLUMN motivo_exclusao TYPE VARCHAR(500);
DROP INDEX ix_leitura_placa_chave_comparacao;
ALTER TABLE leitura_placa DROP COLUMN chave_comparacao;
""")
