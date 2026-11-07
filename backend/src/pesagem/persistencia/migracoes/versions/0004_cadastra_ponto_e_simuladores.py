"""Ponto de controle único e permissão dos simuladores.

O backend não parte sem exatamente um ponto de controle ativo (spec 015,
`obter_unico`), e nenhum contrato cadastra equipamentos. Como os perfis
(ADR-0004 P-A), o ponto vem por migração: uma balança (RF-030) e as cancelas
de entrada e de saída (spec 006). O modo e a comunicação de cada equipamento
vêm das variáveis de ambiente (C-002 item 7). `CONTROLAR_SIMULADORES` é só do
administrador (spec 011 §4.2).

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
INSERT INTO balanca (descricao) VALUES ('Balança');
INSERT INTO cancela (descricao) VALUES ('Cancela de entrada'), ('Cancela de saída');
INSERT INTO ponto_controle (nome, balanca_id, cancela_entrada_id, cancela_saida_id)
SELECT 'Ponto de pesagem', b.id, e.id, s.id FROM balanca b, cancela e, cancela s
WHERE b.descricao = 'Balança' AND e.descricao = 'Cancela de entrada'
  AND s.descricao = 'Cancela de saída';
INSERT INTO perfil_permissao (perfil_id, permissao)
SELECT id, 'CONTROLAR_SIMULADORES' FROM perfil WHERE codigo = 'ADMINISTRADOR';
""")


def downgrade() -> None:
    op.execute("""
DELETE FROM perfil_permissao WHERE permissao = 'CONTROLAR_SIMULADORES';
DELETE FROM ponto_controle WHERE nome = 'Ponto de pesagem';
DELETE FROM cancela WHERE descricao IN ('Cancela de entrada', 'Cancela de saída');
DELETE FROM balanca WHERE descricao = 'Balança';
""")
