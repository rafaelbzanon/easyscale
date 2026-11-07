"""Migração e restrições do esquema (spec 014: CA-001, CA-002, CA-010, CA-013, CA-014, CA-015)."""

import pytest
from alembic import command
from conftest import cadastrar, configuracao_alembic
from sqlalchemy import Engine, text

from pesagem.persistencia.banco import transacao
from pesagem.persistencia.erros import (
    ErroDuplicidade,
    ErroFaixaSobreposta,
    ErroPersistencia,
)


def test_migracao_desfaz_e_refaz_o_esquema(banco: Engine) -> None:
    """CA-001."""
    with banco.begin() as conexao:
        command.downgrade(configuracao_alembic(conexao), "base")
        assert (
            conexao.execute(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename <> 'alembic_version'"
                )
            ).scalar_one()
            == 0
        )
        command.upgrade(configuracao_alembic(conexao), "head")
        assert conexao.execute(text("SELECT count(*) FROM pesagem")).scalar_one() == 0


def test_perfis_e_permissoes_do_adr_0004(banco: Engine) -> None:
    """CA-002."""
    with banco.connect() as conexao:
        linhas = conexao.execute(
            text(
                "SELECT p.codigo, count(*) FROM perfil p JOIN perfil_permissao pp "
                "ON pp.perfil_id = p.id GROUP BY p.codigo"
            )
        ).all()
        auditor = (
            conexao.execute(
                text(
                    "SELECT permissao FROM perfil_permissao pp JOIN perfil p "
                    "ON p.id = pp.perfil_id WHERE p.codigo = 'AUDITOR' ORDER BY 1"
                )
            )
            .scalars()
            .all()
        )
    assert dict(linhas) == {"ADMINISTRADOR": 14, "OPERADOR": 8, "AUDITOR": 3}
    assert auditor == [
        "CONSULTAR_AGENDAMENTOS",
        "CONSULTAR_IMAGENS_DECISAO",
        "CONSULTAR_OPERACAO",
    ]


@pytest.mark.parametrize(
    ("sql", "restricao"),
    [
        (
            "INSERT INTO motorista (nome, cpf) VALUES ('Outro', '52998224725')",
            "ux_motorista_cpf",
        ),
        (
            "INSERT INTO transportadora (razao_social, cnpj) VALUES ('X', '11222333000181')",
            "ux_transportadora_cnpj",
        ),
        (
            "INSERT INTO veiculo (placa, chave_comparacao, tipo_veiculo_id) "
            "SELECT 'ABC1C34', 'ABC1C34', id FROM tipo_veiculo",
            "ux_veiculo_chave_comparacao",
        ),
        (
            "INSERT INTO usuario (nome, login, senha_hash, perfil_id) "
            "SELECT 'Outro', 'ADMIN', 'x', id FROM perfil LIMIT 1",
            "ux_usuario_login",
        ),
        (
            "INSERT INTO tipo_veiculo (descricao) VALUES ('TRUCK')",
            "ux_tipo_veiculo_descricao",
        ),
    ],
)
def test_recusa_cadastro_repetido(banco: Engine, sql: str, restricao: str) -> None:
    """CA-015 (login e descrição sem diferenciar maiúsculas)."""
    with transacao(banco) as t:
        cadastrar(t.conexao)
    with pytest.raises(ErroDuplicidade) as erro, transacao(banco) as t:
        t.conexao.execute(text(sql))
    assert erro.value.restricao == restricao


def test_faixas_ativas_nao_se_sobrepoem(banco: Engine) -> None:
    """CA-010: vizinha e inativa são aceitas; sobreposta não."""
    with transacao(banco) as t:
        cadastrar(t.conexao)  # faixa 08:00-10:00
        t.conexao.execute(
            text(
                "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade, ativo) VALUES "
                "('10:00', '12:00', 1, TRUE), ('09:00', '11:00', 1, FALSE)"
            )
        )
    with pytest.raises(ErroFaixaSobreposta), transacao(banco) as t:
        t.conexao.execute(
            text(
                "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade) "
                "VALUES ('09:30', '10:30', 1)"
            )
        )


_PESAGEM = (
    "INSERT INTO pesagem (agendamento_id, ponto_controle_id, veiculo_id, motorista_id, "
    "placa, chave_comparacao, tipo_operacao, situacao, situacao_anterior, "
    "motivo_intervencao, versao, peso_inicial_kg, peso_inicial_em, peso_final_kg, "
    "peso_final_em, peso_liquido_kg, classificacao, situacao_desde) "
    "SELECT a.id, :ponto, a.veiculo_id, a.motorista_id, 'ABC1234', 'ABC1234', 'CARGA', "
    ":situacao, :anterior, :motivo, 1, 1000, now(), 1500, now(), :liquido, "
    ":classificacao, now() FROM agendamento a"
)


@pytest.mark.parametrize(
    ("situacao", "anterior", "motivo", "liquido", "classificacao"),
    [
        ("PESO_FINAL_OK", None, None, 400, "COM_MOVIMENTACAO"),  # 1500 − 1000 = 500
        ("INEXISTENTE", None, None, None, None),
        ("AGUARDANDO_INTERVENCAO", None, "TEMPO_ESGOTADO", None, None),
        ("AGUARDANDO_INTERVENCAO", "POSICIONADA_FINAL", None, None, None),
        ("PESO_FINAL_OK", None, None, 500, None),
        ("FINALIZADA", None, None, None, None),
    ],
)
def test_banco_recusa_pesagem_incoerente(
    banco: Engine,
    situacao: str,
    anterior: str | None,
    motivo: str | None,
    liquido: int | None,
    classificacao: str | None,
) -> None:
    """CA-013."""
    with transacao(banco) as t:
        ids = cadastrar(t.conexao)
        t.conexao.execute(
            text(
                "INSERT INTO agendamento (veiculo_id, motorista_id, produto_id, tipo_operacao, "
                "data_prevista, faixa_horario_id, origem, criado_por) VALUES "
                f"({ids['veiculo0']}, {ids['motorista']}, {ids['produto']}, 'CARGA', "
                f"'2026-11-07', {ids['faixa']}, 'USUARIO', {ids['usuario']})"
            )
        )
    with pytest.raises(ErroPersistencia) as erro, transacao(banco) as t:
        t.conexao.execute(
            text(_PESAGEM),
            {
                "ponto": ids["ponto"],
                "situacao": situacao,
                "anterior": anterior,
                "motivo": motivo,
                "liquido": liquido,
                "classificacao": classificacao,
            },
        )
    assert str(erro.value).startswith("ck_pesagem_")


def test_excecao_desfaz_a_transacao(banco: Engine) -> None:
    """CA-014."""

    class Falha(Exception):
        pass

    with pytest.raises(Falha), transacao(banco) as t:
        cadastrar(t.conexao)
        raise Falha
    with banco.connect() as conexao:
        assert conexao.execute(text("SELECT count(*) FROM veiculo")).scalar_one() == 0
