"""API de agendamentos e faixas contra o banco real (spec 008, CA-001 a CA-021).

O relógio dos testes começa em 2026-11-07 09:00 no fuso do pátio (America/Sao_Paulo).
"""

import logging
import threading

import pytest
from conftest import ORIGEM, Relogio, cadastrar, criar_usuario, entrar
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from pesagem.persistencia.banco import transacao

HOJE = "2026-11-07"


@pytest.fixture
def ids(banco: Engine) -> dict[str, int]:
    with transacao(banco) as t:
        ids = cadastrar(t.conexao, ("ABC1234", "DEF5678", "GHI9012"))
        ids["tarde"] = int(
            t.conexao.execute(
                text(
                    "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade) "
                    "VALUES ('13:00', '15:00', 1) RETURNING id"
                )
            ).scalar_one()
        )
        return ids


def cliente_de(cliente: TestClient, banco: Engine, perfil: str) -> TestClient:
    novo = TestClient(
        cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    )
    criar_usuario(banco, perfil.lower(), perfil)
    entrar(novo, perfil.lower())
    return novo


@pytest.fixture
def admin(banco: Engine, cliente: TestClient) -> TestClient:
    return cliente_de(cliente, banco, "ADMINISTRADOR")


def corpo(
    ids: dict[str, int], veiculo: str = "veiculo0", **extra: object
) -> dict[str, object]:
    return {
        "veiculo_id": ids[veiculo],
        "motorista_id": ids["motorista"],
        "produto_id": ids["produto"],
        "tipo_operacao": "CARGA",
        "data_prevista": HOJE,
        **extra,
    }


def test_rotas_e_permissoes(
    banco: Engine, cliente: TestClient, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-001 a CA-005."""
    assert cliente.get("/api/agendamentos").status_code == 401
    criado = admin.post("/api/agendamentos", json=corpo(ids))
    assert criado.status_code == 201
    item = criado.json()
    assert "cpf" not in criado.text and item["placa"] == "ABC1234"
    assert (item["origem"], item["status"], item["faixa_hora_inicio"]) == (
        "USUARIO",
        "AGENDADO",
        "08:00",
    )
    assert (
        admin.request("DELETE", f"/api/agendamentos/{item['id']}", json={}).status_code
        == 405
    )
    assert (
        admin.request(
            "DELETE", f"/api/faixas-horario/{ids['faixa']}", json={}
        ).status_code
        == 405
    )
    operador = cliente_de(cliente, banco, "OPERADOR")
    assert operador.get(f"/api/agendamentos/{item['id']}").status_code == 200
    assert (
        operador.post("/api/agendamentos", json=corpo(ids, "veiculo1")).status_code
        == 201
    )
    assert operador.patch(f"/api/agendamentos/{item['id']}", json={}).status_code == 403
    assert (
        operador.post(
            f"/api/agendamentos/{item['id']}/cancelar", json={"motivo": "x"}
        ).status_code
        == 403
    )
    assert operador.get("/api/faixas-horario").status_code == 200
    auditor = cliente_de(cliente, banco, "AUDITOR")
    assert auditor.get("/api/agendamentos").status_code == 200
    assert (
        auditor.post("/api/agendamentos", json=corpo(ids, "veiculo2")).status_code
        == 403
    )
    assert auditor.get("/api/faixas-horario").status_code == 403
    assert (
        auditor.get(
            "/api/faixas-horario/disponibilidade", params={"data": HOJE}
        ).status_code
        == 403
    )


def test_escolha_automatica_e_faixa_cheia(
    banco: Engine, admin: TestClient, ids: dict[str, int], relogio: Relogio
) -> None:
    """CA-006, CA-007 e CA-010."""
    with banco.begin() as conexao:
        conexao.execute(
            text("UPDATE faixa_horario SET capacidade = 1 WHERE hora_inicio = '08:00'")
        )
    primeiro = admin.post("/api/agendamentos", json=corpo(ids)).json()
    assert primeiro["faixa_horario_id"] == ids["faixa"]
    cheia = admin.post(
        "/api/agendamentos", json=corpo(ids, "veiculo1", faixa_horario_id=ids["faixa"])
    )
    assert cheia.status_code == 409
    assert cheia.json()["erro"]["campos"] == [
        {"campo": "faixa_horario_id", "codigo": "FAIXA_SEM_VAGA"}
    ]
    segundo = admin.post("/api/agendamentos", json=corpo(ids, "veiculo1")).json()
    assert segundo["faixa_horario_id"] == ids["tarde"]
    nenhuma = admin.post("/api/agendamentos", json=corpo(ids, "veiculo2"))
    assert nenhuma.json()["erro"]["campos"][0]["codigo"] == "SEM_FAIXA_DISPONIVEL"
    with banco.connect() as conexao:
        assert (
            conexao.execute(text("SELECT count(*) FROM agendamento")).scalar_one() == 2
        )
    relogio.avancar(3 * 3600)  # 12:00: a faixa da manhã já encerrou
    entrar(admin, "administrador")  # a sessão venceu pelo tempo sem uso
    with banco.begin() as conexao:
        conexao.execute(text("UPDATE faixa_horario SET capacidade = 9"))
    encerrada = admin.post(
        "/api/agendamentos", json=corpo(ids, "veiculo2", faixa_horario_id=ids["faixa"])
    )
    assert encerrada.json()["erro"]["campos"][0]["codigo"] == "FAIXA_ENCERRADA"
    futura = corpo(
        ids, "veiculo2", faixa_horario_id=ids["faixa"], data_prevista="2026-11-08"
    )
    assert admin.post("/api/agendamentos", json=futura).status_code == 201


def test_dois_pedidos_pela_ultima_vaga(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-008."""
    status: list[int] = []

    def pedir(veiculo: str) -> None:
        resposta = admin.post(
            "/api/agendamentos", json=corpo(ids, veiculo, faixa_horario_id=ids["tarde"])
        )
        status.append(resposta.status_code)

    pedidos = [
        threading.Thread(target=pedir, args=(v,)) for v in ("veiculo0", "veiculo1")
    ]
    for pedido in pedidos:
        pedido.start()
    for pedido in pedidos:
        pedido.join()
    assert sorted(status) == [201, 409]


def test_cancelar_libera_vaga_e_concluido_nao(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-009 e CA-014."""
    primeiro = admin.post(
        "/api/agendamentos", json=corpo(ids, faixa_horario_id=ids["tarde"])
    ).json()
    sem_motivo = admin.post(f"/api/agendamentos/{primeiro['id']}/cancelar", json={})
    assert sem_motivo.status_code == 422
    cancelado = admin.post(
        f"/api/agendamentos/{primeiro['id']}/cancelar", json={"motivo": "desistiu"}
    ).json()
    assert (cancelado["status"], cancelado["motivo_cancelamento"]) == (
        "CANCELADO",
        "desistiu",
    )
    assert (
        cancelado["cancelado_por"] is not None and cancelado["cancelado_em"] is not None
    )
    segundo = admin.post(
        "/api/agendamentos", json=corpo(ids, "veiculo1", faixa_horario_id=ids["tarde"])
    )
    assert segundo.status_code == 201
    with banco.begin() as conexao:
        conexao.execute(
            text("UPDATE agendamento SET status = 'CONCLUIDO' WHERE id = :id"),
            {"id": segundo.json()["id"]},
        )
    assert (
        admin.post(
            "/api/agendamentos",
            json=corpo(ids, "veiculo2", faixa_horario_id=ids["tarde"]),
        ).status_code
        == 409
    )
    vagas = admin.get(
        "/api/faixas-horario/disponibilidade", params={"data": HOJE}
    ).json()["itens"]
    assert [(v["vagas_ocupadas"], v["vagas_livres"]) for v in vagas] == [(0, 5), (1, 0)]


def test_data_passada_e_veiculo_ja_agendado(
    banco: Engine, admin: TestClient, ids: dict[str, int], relogio: Relogio
) -> None:
    """CA-011, CA-012 e CA-016."""
    passada = admin.post(
        "/api/agendamentos", json=corpo(ids, data_prevista="2026-11-06")
    )
    assert passada.json()["erro"]["campos"] == [
        {"campo": "data_prevista", "codigo": "DATA_NO_PASSADO"}
    ]
    admin.post("/api/agendamentos", json=corpo(ids))
    outro_dia = admin.post(
        "/api/agendamentos", json=corpo(ids, data_prevista="2026-11-09")
    )
    assert outro_dia.json()["erro"]["campos"] == [
        {"campo": "veiculo_id", "codigo": "VEICULO_JA_AGENDADO"}
    ]
    relogio.avancar(24 * 3600)  # o de ontem vence sem ser usado
    entrar(admin, "administrador")  # a sessão venceu pelo tempo sem uso
    lista = admin.get("/api/agendamentos", params={"status": "EXPIRADO"}).json()
    assert [a["status"] for a in lista["itens"]] == ["EXPIRADO"]
    assert (
        admin.get("/api/agendamentos", params={"status": "AGENDADO"}).json()["total"]
        == 0
    )
    assert (
        admin.post(
            "/api/agendamentos", json=corpo(ids, data_prevista="2026-11-08")
        ).status_code
        == 201
    )


def test_patch_e_status(banco: Engine, admin: TestClient, ids: dict[str, int]) -> None:
    """CA-013, CA-015 e CA-017."""
    criado = admin.post("/api/agendamentos", json=corpo(ids)).json()
    caminho = f"/api/agendamentos/{criado['id']}"
    alterado = admin.patch(caminho, json={"observacao": "portão 2"}).json()
    assert (alterado["observacao"], alterado["faixa_horario_id"]) == (
        "portão 2",
        ids["faixa"],
    )
    for invalido in (
        {"status": "CANCELADO"},
        {"cor": 1},
        {"faixa_horario_id": None},
        {"veiculo_id": None},
    ):
        assert admin.patch(caminho, json=invalido).status_code == 422
    nota = admin.patch(caminho, json={"codigo_nota": "123"})
    assert nota.json()["erro"]["campos"] == [
        {"campo": "codigo_nota", "codigo": "CODIGO_NOTA_NAO_PERMITIDO"}
    ]
    descarga = admin.patch(
        caminho, json={"tipo_operacao": "DESCARGA", "codigo_nota": "NF 9"}
    ).json()
    assert descarga["codigo_nota"] == "NF 9"
    voltar = admin.patch(caminho, json={"tipo_operacao": "CARGA"})  # sem limpar a nota
    assert voltar.status_code == 422
    carga_nota = admin.post(
        "/api/agendamentos", json=corpo(ids, "veiculo1", codigo_nota="X")
    )
    assert carga_nota.status_code == 422
    with banco.begin() as conexao:
        conexao.execute(
            text("UPDATE agendamento SET status = 'EM_ANDAMENTO' WHERE id = :id"),
            {"id": criado["id"]},
        )
    for pedido in (
        admin.patch(caminho, json={"observacao": "x"}),
        admin.post(f"{caminho}/cancelar", json={"motivo": "x"}),
    ):
        assert pedido.status_code == 409
        assert pedido.json()["erro"]["campos"] == [
            {"campo": "status", "codigo": "STATUS_NAO_PERMITE"}
        ]
    assert (
        admin.patch("/api/agendamentos/999", json={"observacao": "x"}).status_code
        == 404
    )


def test_patch_revalida_faixa_e_veiculo(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-015 (spec 008 §6.5): mudar faixa refaz as vagas, sem contar o próprio."""
    criado = admin.post(
        "/api/agendamentos", json=corpo(ids, faixa_horario_id=ids["tarde"])
    ).json()
    caminho = f"/api/agendamentos/{criado['id']}"
    assert (
        admin.patch(caminho, json={"faixa_horario_id": ids["tarde"]}).status_code == 200
    )
    admin.post("/api/agendamentos", json=corpo(ids, "veiculo1"))
    trocar_veiculo = admin.patch(caminho, json={"veiculo_id": ids["veiculo1"]})
    assert trocar_veiculo.status_code == 409
    manha = admin.patch(caminho, json={"faixa_horario_id": ids["faixa"]}).json()
    assert manha["faixa_hora_inicio"] == "08:00"
    tarde_ocupada = admin.post(
        "/api/agendamentos", json=corpo(ids, "veiculo2", faixa_horario_id=ids["tarde"])
    )
    assert tarde_ocupada.status_code == 201
    assert (
        admin.patch(caminho, json={"faixa_horario_id": ids["tarde"]}).status_code == 409
    )


def test_faixas(admin: TestClient, ids: dict[str, int]) -> None:
    """CA-018 e CA-019."""
    sobreposta = admin.post(
        "/api/faixas-horario",
        json={"hora_inicio": "09:30", "hora_fim": "11:00", "capacidade": 2},
    )
    assert sobreposta.json()["erro"]["campos"] == [
        {"campo": "hora_inicio", "codigo": "FAIXA_SOBREPOSTA"}
    ]
    vizinha = admin.post(
        "/api/faixas-horario",
        json={"hora_inicio": "10:00", "hora_fim": "11:00", "capacidade": 2},
    )
    assert vizinha.status_code == 201 and vizinha.json()["hora_inicio"] == "10:00"
    for invalida in (
        {"hora_inicio": "11:00", "hora_fim": "10:00", "capacidade": 1},
        {"hora_inicio": "25:00", "hora_fim": "26:00", "capacidade": 1},
        {"hora_inicio": "20:00", "hora_fim": "21:00", "capacidade": 0},
    ):
        assert admin.post("/api/faixas-horario", json=invalida).status_code == 422
    admin.post("/api/agendamentos", json=corpo(ids, faixa_horario_id=ids["tarde"]))
    mudar = admin.patch(
        f"/api/faixas-horario/{ids['tarde']}", json={"hora_fim": "16:00"}
    )
    assert mudar.json()["erro"]["campos"] == [
        {"campo": "hora_inicio", "codigo": "FAIXA_COM_AGENDAMENTOS"}
    ]
    reduzir = admin.patch(f"/api/faixas-horario/{ids['tarde']}", json={"capacidade": 1})
    assert reduzir.status_code == 200
    vagas = admin.get(
        "/api/faixas-horario/disponibilidade", params={"data": HOJE}
    ).json()
    tarde = next(v for v in vagas["itens"] if v["faixa_horario_id"] == ids["tarde"])
    assert (tarde["vagas_livres"], tarde["encerrada"]) == (0, False)
    assert (
        admin.patch(
            f"/api/faixas-horario/{ids['tarde']}", json={"ativo": False}
        ).json()["ativo"]
        is False
    )
    lista = admin.get("/api/faixas-horario", params={"ativo": "true"}).json()
    assert ids["tarde"] not in [f["id"] for f in lista["itens"]]


def test_hoje_segue_o_fuso_do_patio(
    banco: Engine, admin: TestClient, ids: dict[str, int], relogio: Relogio
) -> None:
    """CA-020: 2026-11-08 01:30 UTC ainda é dia 7 em São Paulo (22:30)."""
    relogio.avancar(13.5 * 3600)
    entrar(admin, "administrador")  # a sessão venceu pelo tempo sem uso
    with banco.begin() as conexao:
        conexao.execute(
            text("UPDATE faixa_horario SET hora_fim = '23:00' WHERE id = :id"),
            {"id": ids["tarde"]},
        )
    hoje_no_patio = admin.post(
        "/api/agendamentos", json=corpo(ids, faixa_horario_id=ids["tarde"])
    )
    assert hoje_no_patio.status_code == 201


def test_logs_sem_query_nota_nem_observacao(
    admin: TestClient, ids: dict[str, int], caplog: pytest.LogCaptureFixture
) -> None:
    """CA-021."""
    with caplog.at_level(logging.INFO):
        admin.post(
            "/api/agendamentos",
            json=corpo(
                ids,
                tipo_operacao="DESCARGA",
                codigo_nota="NF-SEGREDO",
                observacao="OBS-SEGREDO",
            ),
        )
        admin.get("/api/agendamentos", params={"placa": "ABC1234"})
    texto = "\n".join(r.getMessage() for r in caplog.records if r.name != "httpx")
    for segredo in ("NF-SEGREDO", "OBS-SEGREDO", "ABC1234"):
        assert segredo not in texto
