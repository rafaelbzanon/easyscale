"""Repositório da operação (spec 014: CA-003 a CA-006, CA-011, CA-012, CA-018 a CA-020)."""

import threading
from dataclasses import replace
from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
from conftest import cadastrar, criar_operacao, esperar_bloqueio
from sqlalchemy import Engine, text

from pesagem.dominio.operacao.maquina_estados import (
    AcaoManual,
    EventoAutomatico,
    MotivoIntervencao,
    PesoAceito,
    SituacaoOperacao,
    TipoAcaoManual,
    TipoEvento,
)
from pesagem.dominio.pesagem.calculo_peso import ClassificacaoPesoLiquido
from pesagem.persistencia.banco import Transacao, transacao
from pesagem.persistencia.erros import (
    ErroBalancaOcupada,
    ErroConflitoVersao,
    ErroLeituraJaUsada,
    ErroLiberacaoIndisponivel,
    ErroOperacaoAberta,
    ErroStatusAgendamento,
)
from pesagem.persistencia.repositorios.agendamento import NovoAgendamento
from pesagem.persistencia.repositorios.leitura_placa import NovaLeituraPlaca
from pesagem.persistencia.repositorios.pesagem import OperacaoRegistrada

HOJE = date(2026, 11, 7)
EM = datetime(2026, 11, 7, 11, 0, tzinfo=UTC)
S = SituacaoOperacao
BALANCA = EventoAutomatico(TipoEvento.BALANCA_DISPONIVEL)


def agendar(t: Transacao, ids: dict[str, int], veiculo: str = "veiculo0") -> int:
    return t.agendamentos.criar_agendamento(
        NovoAgendamento(
            veiculo_id=ids[veiculo],
            motorista_id=ids["motorista"],
            transportadora_id=None,
            produto_id=ids["produto"],
            tipo_operacao="CARGA",
            data_prevista=HOJE,
            faixa_horario_id=None,
            codigo_nota=None,
            observacao=None,
            origem="USUARIO",
            criado_por=ids["usuario"],
        ),
        HOJE,
        time(7, 0),
    ).agendamento_id


def mover(
    t: Transacao, registrada: OperacaoRegistrada, situacao: S, **campos: object
) -> OperacaoRegistrada:
    nova = replace(registrada.operacao, situacao=situacao, **campos)  # type: ignore[arg-type]
    t.pesagens.gravar_transicao(
        registrada.pesagem_id, registrada.operacao.versao, nova, BALANCA, None, HOJE, EM
    )
    return t.pesagens.obter_operacao(registrada.pesagem_id)


def status_agendamento(banco: Engine, agendamento_id: int) -> str:
    with banco.connect() as conexao:
        return str(
            conexao.execute(
                text("SELECT status FROM agendamento WHERE id = :id"),
                {"id": agendamento_id},
            ).scalar_one()
        )


@pytest.fixture
def ids(banco: Engine) -> dict[str, int]:
    with transacao(banco) as t:
        return cadastrar(t.conexao, ("ABC1234", "DEF5678"))


def test_criar_operacao_muda_agendamento_e_registra_criacao(
    banco: Engine, ids: dict[str, int]
) -> None:
    with transacao(banco) as t:
        agendamento = agendar(t, ids)
        registrada = criar_operacao(t, agendamento, ids["ponto"], EM)
    assert registrada.operacao.situacao is S.AGUARDANDO_BALANCA_INICIAL
    assert registrada.operacao.versao == 1
    assert status_agendamento(banco, agendamento) == "EM_ANDAMENTO"
    with banco.connect() as conexao:
        evento = conexao.execute(
            text("SELECT evento, situacao_destino FROM evento_operacao")
        ).one()
    assert tuple(evento) == ("CRIACAO", "AGUARDANDO_BALANCA_INICIAL")


def test_segunda_gravacao_com_a_mesma_versao_e_recusada(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-003."""
    with transacao(banco) as t:
        registrada = criar_operacao(t, agendar(t, ids), ids["ponto"], EM)
    with transacao(banco) as t:
        mover(t, registrada, S.AUTORIZADA)
    with pytest.raises(ErroConflitoVersao), transacao(banco) as t:
        mover(t, registrada, S.CANCELADA)
    with transacao(banco) as t:
        atual = t.pesagens.obter_operacao(registrada.pesagem_id).operacao
    assert (atual.situacao, atual.versao) == (S.AUTORIZADA, 2)


def test_gravacoes_simultaneas_so_uma_vence(banco: Engine, ids: dict[str, int]) -> None:
    """CA-003 com duas transações ao mesmo tempo."""
    with transacao(banco) as t:
        registrada = criar_operacao(t, agendar(t, ids), ids["ponto"], EM)
    erros: list[Exception] = []

    def segunda() -> None:
        try:
            with transacao(banco) as t2:
                mover(t2, registrada, S.CANCELADA)
        except ErroConflitoVersao as erro:
            erros.append(erro)

    with transacao(banco) as t:
        mover(t, registrada, S.AUTORIZADA)
        outra = threading.Thread(target=segunda)
        outra.start()
        esperar_bloqueio(banco)
    outra.join()
    assert len(erros) == 1


def test_reserva_unica_da_balanca(banco: Engine, ids: dict[str, int]) -> None:
    """CA-004."""
    with transacao(banco) as t:
        primeira = criar_operacao(t, agendar(t, ids), ids["ponto"], EM)
        segunda = criar_operacao(t, agendar(t, ids, "veiculo1"), ids["ponto"], EM)
        primeira = mover(t, primeira, S.AUTORIZADA)
    with pytest.raises(ErroBalancaOcupada), transacao(banco) as t:
        mover(t, segunda, S.AUTORIZADA)
    # Parada para intervenção a partir de uma situação que reserva: continua reservada.
    with transacao(banco) as t:
        primeira = mover(
            t,
            primeira,
            S.AGUARDANDO_INTERVENCAO,
            situacao_anterior=S.AUTORIZADA,
            motivo_intervencao=MotivoIntervencao.CANCELA_FALHA,
        )
    with pytest.raises(ErroBalancaOcupada), transacao(banco) as t:
        mover(t, segunda, S.RETORNO_AUTORIZADO)
    # Em carga ou descarga, a balança fica livre.
    with transacao(banco) as t:
        mover(
            t,
            primeira,
            S.EM_CARGA_DESCARGA,
            situacao_anterior=None,
            motivo_intervencao=None,
        )
        assert mover(t, segunda, S.AUTORIZADA).operacao.situacao is S.AUTORIZADA


def test_uma_operacao_aberta_por_veiculo_e_por_agendamento(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-005 e CA-006: nova pesagem para o mesmo agendamento só depois de CANCELADA."""
    with transacao(banco) as t:
        agendamento = agendar(t, ids)
        registrada = criar_operacao(t, agendamento, ids["ponto"], EM)
    with banco.begin() as conexao:  # força o agendamento de volta para tentar de novo
        conexao.execute(text("UPDATE agendamento SET status = 'AGENDADO'"))
    with pytest.raises(ErroOperacaoAberta), transacao(banco) as t:
        criar_operacao(t, agendamento, ids["ponto"], EM)
    with transacao(banco) as t:
        mover(t, registrada, S.CANCELADA)
        criar_operacao(t, agendamento, ids["ponto"], EM)


def test_criar_operacao_exige_agendamento_agendado(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-011 (lado da entrada)."""
    with transacao(banco) as t:
        agendamento = agendar(t, ids)
        t.agendamentos.cancelar_agendamento(
            agendamento, ids["usuario"], "erro", HOJE, EM
        )
    with pytest.raises(ErroStatusAgendamento), transacao(banco) as t:
        criar_operacao(t, agendamento, ids["ponto"], EM)


@pytest.mark.parametrize(
    ("destino", "hoje", "esperado"),
    [
        (S.FINALIZADA, HOJE, "CONCLUIDO"),
        (S.CANCELADA, HOJE, "AGENDADO"),
        (S.CANCELADA, date(2026, 11, 8), "EXPIRADO"),
    ],
)
def test_efeito_no_agendamento_na_mesma_transacao(
    banco: Engine, ids: dict[str, int], destino: S, hoje: date, esperado: str
) -> None:
    """CA-012."""
    pesos: dict[str, object] = {}
    if destino is S.FINALIZADA:
        pesos = {
            "peso_inicial_kg": Decimal("1000.000"),
            "peso_inicial_em": EM,
            "peso_final_kg": Decimal("1500.000"),
            "peso_final_em": EM,
            "peso_liquido_kg": Decimal("500.000"),
            "classificacao": ClassificacaoPesoLiquido.COM_MOVIMENTACAO,
        }
    with transacao(banco) as t:
        agendamento = agendar(t, ids)
        registrada = criar_operacao(t, agendamento, ids["ponto"], EM)
        nova = replace(registrada.operacao, situacao=destino, **pesos)  # type: ignore[arg-type]
        t.pesagens.gravar_transicao(
            registrada.pesagem_id, 1, nova, BALANCA, None, hoje, EM
        )
    assert status_agendamento(banco, agendamento) == esperado


def test_historico_guarda_peso_e_liquido_descartado(
    banco: Engine, ids: dict[str, int]
) -> None:
    """CA-020 (spec 006 §6.1): TENTAR_NOVAMENTE limpa o final; o histórico guarda o descartado."""
    final = {
        "peso_inicial_kg": Decimal("1000.000"),
        "peso_inicial_em": EM,
        "peso_final_kg": Decimal("900.000"),
        "peso_final_em": EM,
        "peso_liquido_kg": Decimal("-100.000"),
        "classificacao": ClassificacaoPesoLiquido.NEGATIVO_FORA_TOLERANCIA,
    }
    with transacao(banco) as t:
        registrada = criar_operacao(t, agendar(t, ids), ids["ponto"], EM)
        parada = replace(
            registrada.operacao,
            situacao=S.AGUARDANDO_INTERVENCAO,
            situacao_anterior=S.POSICIONADA_FINAL,
            motivo_intervencao=MotivoIntervencao.LIQUIDO_NEGATIVO,
            **final,  # type: ignore[arg-type]
        )
        t.pesagens.gravar_transicao(
            registrada.pesagem_id,
            1,
            parada,
            PesoAceito(Decimal("900.000"), EM),
            None,
            HOJE,
            EM,
        )
        de_novo = replace(
            parada,
            situacao=S.POSICIONADA_FINAL,
            situacao_anterior=None,
            motivo_intervencao=None,
            peso_final_kg=None,
            peso_final_em=None,
            peso_liquido_kg=None,
            classificacao=None,
        )
        acao = AcaoManual(TipoAcaoManual.TENTAR_NOVAMENTE, "admin", "nova leitura")
        t.pesagens.gravar_transicao(
            registrada.pesagem_id, 2, de_novo, acao, ids["usuario"], HOJE, EM
        )
    with banco.connect() as conexao:
        linhas = conexao.execute(
            text(
                "SELECT evento, peso_kg, peso_liquido_kg, classificacao, responsavel_id, motivo "
                "FROM evento_operacao WHERE evento <> 'CRIACAO' ORDER BY id"
            )
        ).all()
    assert [tuple(linha) for linha in linhas] == [
        (
            "PESO_ACEITO",
            Decimal("900.000"),
            Decimal("-100.000"),
            "NEGATIVO_FORA_TOLERANCIA",
            None,
            None,
        ),
        (
            "TENTAR_NOVAMENTE",
            Decimal("900.000"),
            Decimal("-100.000"),
            "NEGATIVO_FORA_TOLERANCIA",
            ids["usuario"],
            "nova leitura",
        ),
    ]


def test_leitura_gera_uma_pesagem_so(banco: Engine, ids: dict[str, int]) -> None:
    """CA-018 (spec 009 §6.5): dois pedidos com a mesma leitura, um vence."""
    leitura = NovaLeituraPlaca(
        origem="frente",
        capturada_em=EM,
        decidida_em=EM,
        decisao="NAO_AUTORIZADA",
        motivo="CONFIANCA_BAIXA",
        leituras=[{"roi": [1, 2, 3, 4], "textos": []}],
    )
    with transacao(banco) as t:
        leitura_id = t.leituras_placa.registrar(leitura)
        agendamentos = (agendar(t, ids), agendar(t, ids, "veiculo1"))
    with transacao(banco) as t:
        criar_operacao(
            t,
            agendamentos[0],
            ids["ponto"],
            EM,
            leitura_id,
            True,
            ids["usuario"],
            "placa suja",
        )
    with pytest.raises(ErroLeituraJaUsada), transacao(banco) as t:
        criar_operacao(
            t,
            agendamentos[1],
            ids["ponto"],
            EM,
            leitura_id,
            True,
            ids["usuario"],
            "placa suja",
        )
    with transacao(banco) as t:
        assert (registrada := t.leituras_placa.buscar(leitura_id)) is not None
        assert registrada.pesagem_id is not None


def test_liberacao_do_caminhao_cancelado(banco: Engine, ids: dict[str, int]) -> None:
    """CA-019 (spec 009 §6.6, spec 006 §6.4): um pedido por vez; CONCLUIDA solta a balança."""
    with transacao(banco) as t:
        registrada = criar_operacao(t, agendar(t, ids), ids["ponto"], EM)
        nova = replace(registrada.operacao, situacao=S.CANCELADA)
        cancelar = AcaoManual(TipoAcaoManual.CANCELAR, "admin", "desistiu")
        t.pesagens.gravar_transicao(
            registrada.pesagem_id,
            1,
            nova,
            cancelar,
            ids["usuario"],
            HOJE,
            EM,
            aguarda_liberacao_balanca=True,
        )
    with transacao(banco) as t:
        assert [
            o.pesagem_id for o in t.pesagens.listar_aguardando_liberacao_balanca()
        ] == [registrada.pesagem_id]
        t.pesagens.pedir_liberacao_caminhao(
            registrada.pesagem_id, ids["usuario"], "liberar", EM
        )
    with pytest.raises(ErroLiberacaoIndisponivel), transacao(banco) as t:
        t.pesagens.pedir_liberacao_caminhao(
            registrada.pesagem_id, ids["usuario"], "de novo", EM
        )
    with transacao(banco) as t:
        t.pesagens.registrar_comando_cancela(
            registrada.pesagem_id,
            "SAIDA",
            "ABRIR",
            "CONFIRMADO",
            1,
            EM,
            ids["usuario"],
            "liberar",
        )
        t.pesagens.atualizar_liberacao_caminhao(registrada.pesagem_id, "CONCLUIDA", EM)
        assert t.pesagens.listar_aguardando_liberacao_balanca() == []
        liberacao = t.pesagens.buscar_liberacao_caminhao(registrada.pesagem_id)
    assert liberacao is not None and liberacao.etapa == "CONCLUIDA"


def test_operacao_nao_nasce_para_outro_veiculo(
    banco: Engine, ids: dict[str, int]
) -> None:
    """Regressão (Lynx BAIXO 7): um PATCH trocou o veículo depois da decisão."""
    with transacao(banco) as t:
        agendamento = agendar(t, ids)
    with pytest.raises(ErroStatusAgendamento), transacao(banco) as t:
        t.pesagens.criar_operacao(
            agendamento, ids["ponto"], EM, veiculo_id=ids["veiculo1"]
        )
    assert status_agendamento(banco, agendamento) == "AGENDADO"
    with transacao(banco) as t:
        t.pesagens.criar_operacao(
            agendamento, ids["ponto"], EM, veiculo_id=ids["veiculo0"]
        )
    assert status_agendamento(banco, agendamento) == "EM_ANDAMENTO"
