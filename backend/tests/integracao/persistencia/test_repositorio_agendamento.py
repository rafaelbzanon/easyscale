"""Agendamento, veículo, ponto e imagem (spec 014: CA-007 a CA-011, CA-021)."""

import threading
from dataclasses import replace
from datetime import UTC, date, datetime, time

import pytest
from conftest import cadastrar, criar_operacao, esperar_bloqueio
from sqlalchemy import Engine, text

from pesagem.persistencia.banco import transacao
from pesagem.persistencia.erros import (
    ErroFaixaEncerrada,
    ErroFaixaSemVaga,
    ErroPersistencia,
    ErroSemFaixaDisponivel,
    ErroStatusAgendamento,
    ErroVeiculoJaAgendado,
)
from pesagem.persistencia.repositorios.agendamento import NovoAgendamento

HOJE = date(2026, 11, 7)
EM = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)
CEDO = time(7, 0)


@pytest.fixture
def ids(banco: Engine) -> dict[str, int]:
    with transacao(banco) as t:
        ids = cadastrar(t.conexao, ("ABC1234", "DEF5678", "GHI9012"))
        # Faixa da manhã com uma vaga só, para as corridas.
        t.conexao.execute(text("UPDATE faixa_horario SET capacidade = 1"))
        ids["tarde"] = int(
            t.conexao.execute(
                text(
                    "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade) "
                    "VALUES ('13:00', '15:00', 1) RETURNING id"
                )
            ).scalar_one()
        )
        return ids


def novo(
    ids: dict[str, int], veiculo: str, faixa: int | None = None
) -> NovoAgendamento:
    return NovoAgendamento(
        veiculo_id=ids[veiculo],
        motorista_id=ids["motorista"],
        transportadora_id=None,
        produto_id=ids["produto"],
        tipo_operacao="CARGA",
        data_prevista=HOJE,
        faixa_horario_id=faixa,
        codigo_nota=None,
        observacao=None,
        origem="USUARIO",
        criado_por=ids["usuario"],
    )


def test_faixa_cheia_e_cancelamento_libera_a_vaga(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-007: cancelar libera a vaga; CONCLUIDO não."""
    with transacao(banco) as t:
        primeiro = t.agendamentos.criar_agendamento(
            novo(ids, "veiculo0", ids["faixa"]), HOJE, CEDO
        )
    with pytest.raises(ErroFaixaSemVaga), transacao(banco) as t:
        t.agendamentos.criar_agendamento(
            novo(ids, "veiculo1", ids["faixa"]), HOJE, CEDO
        )
    with transacao(banco) as t:
        t.agendamentos.cancelar_agendamento(
            primeiro.agendamento_id, ids["usuario"], "erro", HOJE, EM
        )
        segundo = t.agendamentos.criar_agendamento(
            novo(ids, "veiculo1", ids["faixa"]), HOJE, CEDO
        )
        t.conexao.execute(
            text("UPDATE agendamento SET status = 'CONCLUIDO' WHERE id = :id"),
            {"id": segundo.agendamento_id},
        )
    with pytest.raises(ErroFaixaSemVaga), transacao(banco) as t:
        t.agendamentos.criar_agendamento(
            novo(ids, "veiculo2", ids["faixa"]), HOJE, CEDO
        )
    with banco.connect() as conexao:
        auditoria = conexao.execute(
            text("SELECT tipo, agendamento_id FROM registro_auditoria")
        ).one()
    assert tuple(auditoria) == ("AGENDAMENTO_CANCELADO", primeiro.agendamento_id)


def test_dois_pedidos_pela_ultima_vaga(banco: Engine, ids: dict[str, int]) -> None:
    """CA-007 com duas transações ao mesmo tempo: uma cria, a outra recebe ErroFaixaSemVaga."""
    erros: list[Exception] = []

    def segundo() -> None:
        try:
            with transacao(banco) as t2:
                t2.agendamentos.criar_agendamento(
                    novo(ids, "veiculo1", ids["faixa"]), HOJE, CEDO
                )
        except ErroFaixaSemVaga as erro:
            erros.append(erro)

    with transacao(banco) as t:
        t.agendamentos.criar_agendamento(
            novo(ids, "veiculo0", ids["faixa"]), HOJE, CEDO
        )
        outro = threading.Thread(target=segundo)
        outro.start()
        esperar_bloqueio(banco)
    outro.join()
    assert len(erros) == 1


def test_um_agendamento_aberto_por_veiculo(banco: Engine, ids: dict[str, int]) -> None:
    """CA-008: em outro dia também; o vencido vira EXPIRADO e não impede."""
    with transacao(banco) as t:
        t.agendamentos.criar_agendamento(novo(ids, "veiculo0"), HOJE, CEDO)
    amanha = replace(novo(ids, "veiculo0"), data_prevista=date(2026, 11, 8))
    with pytest.raises(ErroVeiculoJaAgendado), transacao(banco) as t:
        t.agendamentos.criar_agendamento(amanha, HOJE, CEDO)
    # No dia seguinte, o de hoje venceu sem ser usado.
    with transacao(banco) as t:
        t.agendamentos.criar_agendamento(amanha, date(2026, 11, 8), CEDO)
    with banco.connect() as conexao:
        status = (
            conexao.execute(text("SELECT status FROM agendamento ORDER BY id"))
            .scalars()
            .all()
        )
    assert status == ["EXPIRADO", "AGENDADO"]


def test_dois_pedidos_simultaneos_para_o_mesmo_veiculo(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-008 com duas transações: faixas diferentes, mesmo veículo."""
    erros: list[Exception] = []

    def segundo() -> None:
        try:
            with transacao(banco) as t2:
                t2.agendamentos.criar_agendamento(
                    novo(ids, "veiculo0", ids["tarde"]), HOJE, CEDO
                )
        except ErroVeiculoJaAgendado as erro:
            erros.append(erro)

    with transacao(banco) as t:
        t.agendamentos.criar_agendamento(
            novo(ids, "veiculo0", ids["faixa"]), HOJE, CEDO
        )
        outro = threading.Thread(target=segundo)
        outro.start()
        esperar_bloqueio(banco)
    outro.join()
    assert len(erros) == 1


def test_escolha_automatica_da_faixa(banco: Engine, ids: dict[str, int]) -> None:
    """CA-009: primeira ativa, não encerrada e com vaga; depois, nenhuma."""
    with transacao(banco) as t:
        manha = t.agendamentos.criar_agendamento(novo(ids, "veiculo0"), HOJE, CEDO)
        # Às 11h a faixa da manhã já encerrou: vai para a da tarde.
        tarde = t.agendamentos.criar_agendamento(
            novo(ids, "veiculo1"), HOJE, time(11, 0)
        )
    assert (manha.faixa_horario_id, tarde.faixa_horario_id) == (
        ids["faixa"],
        ids["tarde"],
    )
    with pytest.raises(ErroSemFaixaDisponivel), transacao(banco) as t:
        t.agendamentos.criar_agendamento(novo(ids, "veiculo2"), HOJE, CEDO)
    with banco.connect() as conexao:
        assert (
            conexao.execute(text("SELECT count(*) FROM agendamento")).scalar_one() == 2
        )


def test_faixa_encerrada_hoje_e_aceita_em_dia_futuro(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-009 (spec 008 P-3)."""
    with pytest.raises(ErroFaixaEncerrada), transacao(banco) as t:
        t.agendamentos.criar_agendamento(
            novo(ids, "veiculo0", ids["faixa"]), HOJE, time(10, 0)
        )
    futuro = replace(
        novo(ids, "veiculo0", ids["faixa"]), data_prevista=date(2026, 11, 9)
    )
    with transacao(banco) as t:
        t.agendamentos.criar_agendamento(futuro, HOJE, time(10, 0))


def test_so_cancela_agendado(banco: Engine, ids: dict[str, int]) -> None:
    """CA-011: EM_ANDAMENTO e AGENDADO vencido não são cancelados."""
    with transacao(banco) as t:
        criado = t.agendamentos.criar_agendamento(novo(ids, "veiculo0"), HOJE, CEDO)
        criar_operacao(t, criado.agendamento_id, ids["ponto"], EM)
    with pytest.raises(ErroStatusAgendamento), transacao(banco) as t:
        t.agendamentos.cancelar_agendamento(
            criado.agendamento_id, ids["usuario"], "x", HOJE, EM
        )
    with transacao(banco) as t:
        vencido = t.agendamentos.criar_agendamento(novo(ids, "veiculo1"), HOJE, CEDO)
    with pytest.raises(ErroStatusAgendamento), transacao(banco) as t:
        t.agendamentos.cancelar_agendamento(
            vencido.agendamento_id, ids["usuario"], "x", date(2026, 11, 8), EM
        )


def test_retrato_do_veiculo_para_autorizacao(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-021 (spec 015, consulta da RN-002)."""
    with transacao(banco) as t:
        assert t.veiculos.buscar_situacao_por_chave("ZZZ9999") is None
        criado = t.agendamentos.criar_agendamento(novo(ids, "veiculo0"), HOJE, CEDO)
        situacao = t.veiculos.buscar_situacao_por_chave("ABC1C34")
    assert situacao is not None
    assert (situacao.veiculo_id, situacao.ativo, situacao.operacao_aberta) == (
        ids["veiculo0"],
        True,
        None,
    )
    (agendamento,) = situacao.agendamentos
    assert (
        agendamento.agendamento_id,
        agendamento.faixa_hora_inicio,
        agendamento.motorista_ativo,
    ) == (
        criado.agendamento_id,
        time(8, 0),
        True,
    )
    with transacao(banco) as t:
        operacao = criar_operacao(t, criado.agendamento_id, ids["ponto"], EM)
        situacao = t.veiculos.buscar_situacao_por_chave("ABC1C34")
    assert situacao is not None and situacao.operacao_aberta is not None
    assert situacao.operacao_aberta.pesagem_id == operacao.pesagem_id
    with transacao(banco) as t:
        assert (
            t.veiculos.buscar_situacao_por_agendamento(criado.agendamento_id)
            == situacao
        )
        assert t.veiculos.buscar_situacao_por_agendamento(999) is None


def test_ponto_de_controle_unico(banco: Engine, ids: dict[str, int]) -> None:
    """RF-030: com mais de um ponto ativo, não escolhe sozinho."""

    class Desfazer(Exception):
        """Desfaz o segundo ponto, que fica fora da limpeza entre testes."""

    with pytest.raises(Desfazer), transacao(banco) as t:
        assert t.pontos_controle.obter_unico() == ids["ponto"]
        t.conexao.execute(
            text(
                "INSERT INTO balanca (descricao) VALUES ('B2');"
                "INSERT INTO ponto_controle (nome, balanca_id, cancela_entrada_id, cancela_saida_id) "
                f"SELECT 'P2', max(id), {ids['entrada']}, {ids['saida']} FROM balanca"
            )
        )
        with pytest.raises(ErroPersistencia):
            t.pontos_controle.obter_unico()
        raise Desfazer


def test_imagem_da_decisao_fica_no_banco(banco: Engine, ids: dict[str, int]) -> None:
    """RN-022 (spec 014 §10): os bytes voltam iguais."""
    with transacao(banco) as t:
        imagem = t.imagens.salvar(b"\xff\xd8jpeg", "superior", EM, (1, 2, 30, 40))
    with banco.connect() as conexao:
        linha = conexao.execute(
            text("SELECT conteudo, roi_largura FROM imagem_decisao WHERE id = :id"),
            {"id": imagem},
        ).one()
    assert (bytes(linha.conteudo), linha.roi_largura) == (b"\xff\xd8jpeg", 30)
