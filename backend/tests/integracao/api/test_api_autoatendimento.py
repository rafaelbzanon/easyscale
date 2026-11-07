"""API de autoatendimento contra o banco real (spec 013, CA-001 a CA-014)."""

import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from ipaddress import ip_network

import pytest
from conftest import AMBIENTE_OPERACAO, ORIGEM, Relogio, cadastrar, configuracao_api
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from pesagem.config import (
    ConfiguracaoAutoatendimento,
    ConfiguracaoBanco,
    ErroConfiguracao,
    ler_configuracao,
)
from pesagem.main import criar_aplicacao
from pesagem.persistencia.banco import transacao

ROTA = "/api/autoatendimento/agendamentos"
DENTRO, FORA = ("10.20.0.7", 40000), ("192.168.9.9", 40000)
AUTOATENDIMENTO = ConfiguracaoAutoatendimento(
    redes=(ip_network("10.20.0.0/16"),), tentativas_maximas=2, bloqueio_s=120
)

Fabrica = Callable[..., TestClient]


@pytest.fixture
def ids(banco: Engine) -> dict[str, int]:
    with transacao(banco) as t:
        ids = cadastrar(t.conexao, ("ABC1234", "DEF5678"))
        ids["tarde"] = int(
            t.conexao.execute(
                text(
                    "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade) "
                    "VALUES ('13:00', '15:00', 1) RETURNING id"
                )
            ).scalar_one()
        )
        return ids


@pytest.fixture
def fabrica(
    banco: Engine, configuracao_banco: ConfiguracaoBanco, relogio: Relogio
) -> Fabrica:
    def criar(
        endereco: tuple[str, int] = DENTRO,
        autoatendimento: ConfiguracaoAutoatendimento | None = AUTOATENDIMENTO,
    ) -> TestClient:
        configuracao = replace(
            configuracao_api(configuracao_banco), autoatendimento=autoatendimento
        )
        return TestClient(
            criar_aplicacao(configuracao, banco, relogio, executar_ciclos=False),
            base_url="https://pesagem.teste",
            headers={"Origin": ORIGEM},
            client=endereco,
        )

    return criar


def pedido(ids: dict[str, int], **extra: object) -> dict[str, object]:
    return {
        "placa": "abc-1234",
        "cpf": "52998224725",
        "tipo_operacao": "CARGA",
        "produto_id": ids["produto"],
        "data_prevista": "2026-11-07",
        **extra,
    }


def contar(banco: Engine) -> int:
    with banco.connect() as conexao:
        return int(
            conexao.execute(text("SELECT count(*) FROM agendamento")).scalar_one()
        )


def test_desligado_sem_redes_e_fora_da_rede(
    fabrica: Fabrica, ids: dict[str, int], banco: Engine
) -> None:
    """CA-001 e CA-002."""
    desligado = fabrica(autoatendimento=None)
    for resposta in (
        desligado.get("/api/autoatendimento/produtos"),
        desligado.get(
            "/api/autoatendimento/disponibilidade", params={"data": "2026-11-07"}
        ),
        desligado.post(ROTA, json=pedido(ids)),
    ):
        assert resposta.status_code == 404
    fora = fabrica(FORA)
    for resposta in (
        fora.get("/api/autoatendimento/produtos"),
        fora.get("/api/autoatendimento/disponibilidade", params={"data": "2026-11-07"}),
        fora.post(ROTA, json=pedido(ids)),
    ):
        assert (resposta.status_code, resposta.json()["erro"]["codigo"]) == (
            403,
            "REDE_NAO_PERMITIDA",
        )
    assert contar(banco) == 0


def test_cria_com_resposta_minima(
    fabrica: Fabrica, ids: dict[str, int], banco: Engine
) -> None:
    """CA-003 e CA-009, e as consultas da §4."""
    cliente = fabrica()
    produtos = cliente.get("/api/autoatendimento/produtos").json()
    assert [set(p) for p in produtos["itens"]] == [{"id", "codigo", "descricao"}]
    vagas = cliente.get(
        "/api/autoatendimento/disponibilidade", params={"data": "2026-11-07"}
    ).json()
    assert [v["hora_inicio"] for v in vagas["itens"]] == ["08:00", "13:00"]
    resposta = cliente.post(ROTA, json=pedido(ids))
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert set(corpo) == {
        "agendamento_id",
        "tipo_operacao",
        "data_prevista",
        "faixa_hora_inicio",
        "faixa_hora_fim",
    }
    assert (corpo["faixa_hora_inicio"], corpo["faixa_hora_fim"]) == ("08:00", "10:00")
    with banco.connect() as conexao:
        linha = conexao.execute(
            text(
                "SELECT origem, criado_por, transportadora_id, status FROM agendamento"
            )
        ).one()
    assert tuple(linha) == ("AUTOATENDIMENTO", None, None, "AGENDADO")


def test_cadastro_que_nao_confere_tem_resposta_identica(
    fabrica: Fabrica, ids: dict[str, int], banco: Engine
) -> None:
    """CA-004."""
    with banco.begin() as conexao:
        conexao.execute(
            text("UPDATE veiculo SET ativo = FALSE WHERE placa = 'DEF5678'")
        )
        conexao.execute(
            text(
                "INSERT INTO motorista (nome, cpf, ativo) VALUES ('Inativo', '11144477735', FALSE)"
            )
        )
    cliente = fabrica()
    casos = [
        pedido(ids, placa="ZZZ9999"),
        pedido(ids, cpf="39053344705"),
        pedido(ids, placa="DEF5678"),
        pedido(ids, cpf="11144477735"),
    ]
    respostas = []
    for caso in casos:
        respostas.append(cliente.post(ROTA, json=caso))
        with banco.begin() as conexao:  # o limite de tentativas não entra neste teste
            conexao.execute(text("DELETE FROM tentativa_acesso"))
    assert {r.status_code for r in respostas} == {422}
    assert len({r.text for r in respostas}) == 1
    assert respostas[0].json()["erro"] == {
        "codigo": "DADOS_NAO_CONFEREM",
        "mensagem": "Placa ou CPF não conferem com o cadastro.",
        "campos": [],
    }
    assert contar(banco) == 0


def test_limite_por_origem(
    fabrica: Fabrica, ids: dict[str, int], relogio: Relogio
) -> None:
    """CA-005 e CA-006."""
    cliente = fabrica()
    formato = cliente.post(ROTA, json=pedido(ids, cpf="52998224726"))
    assert formato.status_code == 422
    assert formato.json()["erro"]["campos"] == [
        {"campo": "cpf", "codigo": "CAMPO_INVALIDO"}
    ]
    placa = cliente.post(ROTA, json=pedido(ids, placa="ABCO123"))
    assert placa.json()["erro"]["campos"] == [
        {"campo": "placa", "codigo": "PLACA_INVALIDA"}
    ]
    for _ in range(2):
        assert cliente.post(ROTA, json=pedido(ids, placa="ZZZ9999")).status_code == 422
    bloqueado = cliente.post(ROTA, json=pedido(ids))
    assert (bloqueado.status_code, bloqueado.json()["erro"]["codigo"]) == (
        429,
        "AUTOATENDIMENTO_BLOQUEADO",
    )
    assert cliente.get("/api/autoatendimento/produtos").status_code == 200
    outra_origem = fabrica(("10.20.0.8", 40000))
    assert outra_origem.post(ROTA, json=pedido(ids)).status_code == 201
    relogio.avancar(121)
    assert cliente.post(ROTA, json=pedido(ids, placa="DEF5678")).status_code == 201


def test_regras_da_spec_008(
    fabrica: Fabrica, ids: dict[str, int], banco: Engine
) -> None:
    """CA-007 e CA-008."""
    cliente = fabrica()

    def campos(**extra: object) -> object:
        return cliente.post(ROTA, json=pedido(ids, **extra)).json()["erro"]["campos"]

    assert campos(data_prevista="2026-11-06") == [
        {"campo": "data_prevista", "codigo": "DATA_NO_PASSADO"}
    ]
    assert campos(tipo_operacao="DESCARGA") == [
        {"campo": "codigo_nota", "codigo": "CODIGO_NOTA_OBRIGATORIO"}
    ]
    assert campos(codigo_nota="NF 1") == [
        {"campo": "codigo_nota", "codigo": "CODIGO_NOTA_NAO_PERMITIDO"}
    ]
    descarga = cliente.post(
        ROTA, json=pedido(ids, tipo_operacao="DESCARGA", codigo_nota=" NF 77 ")
    )
    assert descarga.status_code == 201
    with banco.connect() as conexao:
        nota = conexao.execute(text("SELECT codigo_nota FROM agendamento")).scalar_one()
    assert nota == " NF 77 "  # guardado como enviado
    assert campos(placa="ABC1234") == [
        {"campo": "veiculo_id", "codigo": "VEICULO_JA_AGENDADO"}
    ]
    amanha = pedido(ids, placa="DEF5678", data_prevista="2026-11-08")
    assert cliente.post(ROTA, json=amanha).status_code == 201
    assert campos(placa="DEF5678", faixa_horario_id=ids["tarde"]) == [
        {"campo": "veiculo_id", "codigo": "VEICULO_JA_AGENDADO"}
    ]


def test_faixa_cheia_encerrada_e_sem_faixa(
    fabrica: Fabrica, ids: dict[str, int], banco: Engine, relogio: Relogio
) -> None:
    """CA-007 (faixas)."""
    with banco.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO agendamento (veiculo_id, motorista_id, produto_id, tipo_operacao, "
                "data_prevista, faixa_horario_id, origem) VALUES (:v, :m, :p, 'CARGA', "
                "'2026-11-07', :f, 'AUTOATENDIMENTO')"
            ),
            {
                "v": ids["veiculo1"],
                "m": ids["motorista"],
                "p": ids["produto"],
                "f": ids["tarde"],
            },
        )
    cliente = fabrica()
    cheia = cliente.post(ROTA, json=pedido(ids, faixa_horario_id=ids["tarde"]))
    assert cheia.json()["erro"]["campos"] == [
        {"campo": "faixa_horario_id", "codigo": "FAIXA_SEM_VAGA"}
    ]
    relogio.avancar(2 * 3600)  # 11:00: a faixa da manhã encerrou
    encerrada = cliente.post(ROTA, json=pedido(ids, faixa_horario_id=ids["faixa"]))
    assert encerrada.json()["erro"]["campos"] == [
        {"campo": "faixa_horario_id", "codigo": "FAIXA_ENCERRADA"}
    ]
    nenhuma = cliente.post(ROTA, json=pedido(ids))
    assert nenhuma.json()["erro"]["campos"] == [
        {"campo": "faixa_horario_id", "codigo": "SEM_FAIXA_DISPONIVEL"}
    ]


def test_dois_pedidos_pela_ultima_vaga(fabrica: Fabrica, ids: dict[str, int]) -> None:
    """CA-010."""
    cliente = fabrica()
    status: list[int] = []

    def pedir(placa: str) -> None:
        resposta = cliente.post(
            ROTA, json=pedido(ids, placa=placa, faixa_horario_id=ids["tarde"])
        )
        status.append(resposta.status_code)

    pedidos = [
        threading.Thread(target=pedir, args=(p,)) for p in ("ABC1234", "DEF5678")
    ]
    for p in pedidos:
        p.start()
    for p in pedidos:
        p.join()
    assert sorted(status) == [201, 409]


def test_csrf_e_rotas_protegidas(
    fabrica: Fabrica, ids: dict[str, int], banco: Engine
) -> None:
    """CA-011 e CA-012."""
    cliente = fabrica()
    sem_origem = cliente.post(
        ROTA, json=pedido(ids), headers={"Origin": "https://outro.site"}
    )
    formulario = cliente.post(ROTA, data={"placa": "ABC1234"})
    assert [sem_origem.status_code, formulario.status_code] == [403, 415]
    assert contar(banco) == 0
    for metodo, rota in (
        ("GET", "/api/agendamentos"),
        ("GET", "/api/agendamentos/1"),
        ("PATCH", "/api/agendamentos/1"),
        ("POST", "/api/agendamentos/1/cancelar"),
        ("GET", "/api/autoatendimento/agendamentos"),
    ):
        resposta = cliente.request(metodo, rota, json={})
        assert resposta.status_code in (401, 405), (metodo, rota)


def test_logs_sem_placa_cpf_nem_nota(
    fabrica: Fabrica,
    ids: dict[str, int],
    banco: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CA-013."""
    cliente = fabrica()
    with caplog.at_level(logging.INFO):
        cliente.post(ROTA, json=pedido(ids, placa="ZZZ9999"))
        cliente.post(
            ROTA, json=pedido(ids, tipo_operacao="DESCARGA", codigo_nota="NF-SEGREDO")
        )
    texto = "\n".join(r.getMessage() for r in caplog.records if r.name != "httpx")
    for segredo in ("ZZZ9999", "ABC1234", "52998224725", "NF-SEGREDO"):
        assert segredo not in texto
    with banco.connect() as conexao:
        auditoria = conexao.execute(
            text("SELECT tipo, endereco_origem FROM registro_auditoria")
        ).all()
    assert [tuple(a) for a in auditoria] == [("AUTOATENDIMENTO_RECUSADO", "10.20.0.7")]


def test_partida_com_redes_exige_o_limite() -> None:
    """CA-014."""
    base = {
        "PESAGEM_BANCO_HOST": "db",
        "PESAGEM_BANCO_PORTA": "5432",
        "PESAGEM_BANCO_NOME": "p",
        "PESAGEM_BANCO_USUARIO": "p",
        "PESAGEM_BANCO_SENHA": "s",
        "PESAGEM_PATIO_FUSO": "UTC",
        "PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS": ORIGEM,
        "PESAGEM_SEGURANCA_SESSAO_TEMPO_SEM_USO_S": "600",
        "PESAGEM_SEGURANCA_LOGIN_TENTATIVAS_MAXIMAS": "5",
        "PESAGEM_SEGURANCA_LOGIN_BLOQUEIO_S": "60",
        "PESAGEM_GERAL_TAMANHO_PAGINA_PADRAO": "10",
        "PESAGEM_GERAL_TAMANHO_PAGINA_MAXIMO": "50",
        **AMBIENTE_OPERACAO,
    }
    assert ler_configuracao(base).autoatendimento is None
    com_redes = {
        **base,
        "PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES": "10.0.0.0/8, fd00::/8",
    }
    for falta in ({}, {"PESAGEM_SEGURANCA_AUTOATENDIMENTO_TENTATIVAS_MAXIMAS": "0"}):
        with pytest.raises(ErroConfiguracao):
            ler_configuracao(
                {
                    **com_redes,
                    "PESAGEM_SEGURANCA_AUTOATENDIMENTO_BLOQUEIO_S": "60",
                    **falta,
                }
                if falta
                else com_redes
            )
    with pytest.raises(ErroConfiguracao, match="REDES"):
        ler_configuracao(
            {**com_redes, "PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES": "10.0.0.0/33"}
        )
    completo = {
        **com_redes,
        "PESAGEM_SEGURANCA_AUTOATENDIMENTO_TENTATIVAS_MAXIMAS": "3",
        "PESAGEM_SEGURANCA_AUTOATENDIMENTO_BLOQUEIO_S": "60",
    }
    autoatendimento = ler_configuracao(completo).autoatendimento
    assert autoatendimento is not None and len(autoatendimento.redes) == 2
