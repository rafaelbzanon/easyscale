"""API de cadastros contra o banco real (spec 007, CA-001 a CA-016)."""

import logging
import threading

import pytest
from conftest import ORIGEM, criar_usuario, entrar
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from pesagem.api.validacao import cnpj_valido

RECURSOS = ["transportadoras", "motoristas", "tipos-veiculo", "veiculos", "produtos"]


@pytest.fixture
def admin(banco: Engine, cliente: TestClient) -> TestClient:
    criar_usuario(banco, "admin", "ADMINISTRADOR")
    entrar(cliente, "admin")
    return cliente


def outro_cliente(cliente: TestClient, banco: Engine, perfil: str) -> TestClient:
    novo = TestClient(
        cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    )
    criar_usuario(banco, perfil.lower(), perfil)
    entrar(novo, perfil.lower())
    return novo


def criar(
    cliente: TestClient, recurso: str, corpo: dict[str, object]
) -> dict[str, object]:
    resposta = cliente.post(f"/api/{recurso}", json=corpo)
    assert resposta.status_code == 201, resposta.text
    dados: dict[str, object] = resposta.json()
    return dados


def tipo(admin: TestClient) -> object:
    return criar(admin, "tipos-veiculo", {"descricao": "Truck"})["id"]


def test_rotas_existem_e_nao_aceitam_delete(admin: TestClient) -> None:
    """CA-001."""
    for recurso in RECURSOS:
        assert admin.get(f"/api/{recurso}").status_code == 200
        apagar = admin.request("DELETE", f"/api/{recurso}/1", json={})
        assert apagar.status_code == 405


def test_sem_sessao_e_sem_permissao(banco: Engine, cliente: TestClient) -> None:
    """CA-002 e CA-003."""
    assert cliente.get("/api/veiculos").status_code == 401
    operador = outro_cliente(cliente, banco, "OPERADOR")
    auditor = outro_cliente(cliente, banco, "AUDITOR")
    for recurso in RECURSOS:
        assert operador.get(f"/api/{recurso}").status_code == 200
        assert operador.post(f"/api/{recurso}", json={}).status_code == 403
        assert operador.patch(f"/api/{recurso}/1", json={}).status_code == 403
        assert auditor.get(f"/api/{recurso}").status_code == 403
        assert auditor.get(f"/api/{recurso}/1").status_code == 403


def test_cpf_completo_so_para_administrador(
    banco: Engine, cliente: TestClient, admin: TestClient
) -> None:
    """CA-004."""
    criado = criar(admin, "motoristas", {"nome": "Ana", "cpf": "52998224725"})
    assert (criado["cpf"], criado["cpf_mascarado"]) == ("52998224725", "***.982.247-**")
    assert admin.get(f"/api/motoristas/{criado['id']}").json()["cpf"] == "52998224725"
    assert admin.get("/api/motoristas").json()["itens"][0]["cpf"] is None
    operador = outro_cliente(cliente, banco, "OPERADOR")
    item = operador.get(f"/api/motoristas/{criado['id']}").json()
    assert (item["cpf"], item["cpf_mascarado"]) == (None, "***.982.247-**")


def test_lista_paginada_e_erros_no_corpo_comum(admin: TestClient) -> None:
    """CA-005 e CA-006."""
    for codigo in ("P1", "P2", "P3"):
        criar(admin, "produtos", {"codigo": codigo, "descricao": f"Produto {codigo}"})
    pagina = admin.get("/api/produtos", params={"pagina": 2}).json()
    assert (pagina["total"], pagina["pagina"], pagina["tamanho_pagina"]) == (3, 2, 2)
    assert [p["codigo"] for p in pagina["itens"]] == ["P3"]
    assert pagina["itens"][0]["unidade"] == "KG"
    acima = admin.get("/api/produtos", params={"tamanho_pagina": 6})
    assert acima.status_code == 422
    sem_campo = admin.post("/api/produtos", json={"codigo": "X"})
    erro = sem_campo.json()["erro"]
    assert (sem_campo.status_code, erro["codigo"]) == (422, "CAMPO_INVALIDO")
    assert {"campo": "descricao", "codigo": "CAMPO_INVALIDO"} in erro["campos"]
    assert set(erro) == {"codigo", "mensagem", "campos"}


def test_placa_normalizada_e_sem_correcao_de_ocr(admin: TestClient) -> None:
    """CA-007, CA-008 e CA-009."""
    criado = criar(
        admin, "veiculos", {"placa": "abc-1d23", "tipo_veiculo_id": tipo(admin)}
    )
    assert (criado["placa"], criado["formato_placa"]) == ("ABC1D23", "MERCOSUL")
    corrigida = admin.post(
        "/api/veiculos", json={"placa": "ABCO123", "tipo_veiculo_id": 1}
    )
    assert corrigida.status_code == 422
    assert corrigida.json()["erro"]["campos"] == [
        {"campo": "placa", "codigo": "PLACA_INVALIDA"}
    ]
    criar(admin, "veiculos", {"placa": "XYZ1234", "tipo_veiculo_id": 1})
    mesma = admin.post("/api/veiculos", json={"placa": "XYZ1C34", "tipo_veiculo_id": 1})
    assert mesma.status_code == 409
    assert mesma.json()["erro"]["campos"] == [{"campo": "placa", "codigo": "CONFLITO"}]
    filtrada = admin.get("/api/veiculos", params={"placa": "xyz-1c34"}).json()
    assert [v["placa"] for v in filtrada["itens"]] == ["XYZ1234"]


def test_cpf_e_cnpj(admin: TestClient) -> None:
    """CA-010, inclusive o CNPJ alfanumérico."""
    assert cnpj_valido("12ABC34501DE35") and not cnpj_valido("12ABC34501DE36")
    assert (
        admin.post(
            "/api/motoristas", json={"nome": "A", "cpf": "52998224726"}
        ).status_code
        == 422
    )
    criar(admin, "motoristas", {"nome": "A", "cpf": "52998224725"})
    assert (
        admin.post(
            "/api/motoristas", json={"nome": "B", "cpf": "52998224725"}
        ).status_code
        == 409
    )
    base = {"razao_social": "T"}
    assert (
        admin.post(
            "/api/transportadoras", json={**base, "cnpj": "11222333000182"}
        ).status_code
        == 422
    )
    criar(admin, "transportadoras", {**base, "cnpj": "12ABC34501DE35"})
    criar(admin, "transportadoras", {**base, "cnpj": "11222333000181"})
    assert (
        admin.post(
            "/api/transportadoras", json={**base, "cnpj": "11222333000181"}
        ).status_code
        == 409
    )


def test_referencia_inexistente_ou_inativa(admin: TestClient) -> None:
    """CA-011."""
    inativo = criar(admin, "tipos-veiculo", {"descricao": "Velho"})
    admin.patch(f"/api/tipos-veiculo/{inativo['id']}", json={"ativo": False})
    for tipo_id in (inativo["id"], 999):
        resposta = admin.post(
            "/api/veiculos", json={"placa": "ABC1234", "tipo_veiculo_id": tipo_id}
        )
        assert resposta.status_code == 422
        assert resposta.json()["erro"]["campos"] == [
            {"campo": "tipo_veiculo_id", "codigo": "CAMPO_INVALIDO"}
        ]


def test_patch_altera_so_o_enviado(admin: TestClient) -> None:
    """CA-012 e CA-014."""
    criado = criar(
        admin,
        "veiculos",
        {
            "placa": "ABC1234",
            "tipo_veiculo_id": tipo(admin),
            "marca": "Volvo",
            "tara_kg": "15000.125",
        },
    )
    assert criado["tara_kg"] == "15000.125"
    alterado = admin.patch(
        f"/api/veiculos/{criado['id']}", json={"modelo": "FH"}
    ).json()
    assert (alterado["marca"], alterado["modelo"], alterado["tara_kg"]) == (
        "Volvo",
        "FH",
        "15000.125",
    )
    for corpo in (
        {"id": 5},
        {"formato_placa": "ANTIGO"},
        {"cor": "azul"},
        {"placa": None},
    ):
        assert (
            admin.patch(f"/api/veiculos/{criado['id']}", json=corpo).status_code == 422
        )
    assert admin.patch("/api/veiculos/999", json={"modelo": "X"}).status_code == 404


def test_desativar_com_operacao_aberta(banco: Engine, admin: TestClient) -> None:
    """CA-013."""
    veiculo = criar(
        admin, "veiculos", {"placa": "ABC1234", "tipo_veiculo_id": tipo(admin)}
    )
    motorista = criar(admin, "motoristas", {"nome": "Ana", "cpf": "52998224725"})
    produto = criar(admin, "produtos", {"codigo": "S", "descricao": "Soja"})
    with banco.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade) VALUES ('08:00', '18:00', 9); "
                "INSERT INTO agendamento (veiculo_id, motorista_id, produto_id, tipo_operacao, "
                f"data_prevista, faixa_horario_id, origem, criado_por, status) VALUES ({veiculo['id']}, "
                f"{motorista['id']}, {produto['id']}, 'CARGA', '2026-11-07', 1, 'USUARIO', 1, 'EM_ANDAMENTO'); "
                "INSERT INTO pesagem (agendamento_id, ponto_controle_id, veiculo_id, motorista_id, placa, "
                "chave_comparacao, tipo_operacao, situacao, versao, situacao_desde) "
                f"SELECT 1, id, {veiculo['id']}, {motorista['id']}, 'ABC1234', 'ABC1C34', "
                "'CARGA', 'AUTORIZADA', 1, now() FROM ponto_controle"
            )
        )
    for recurso, item in (("veiculos", veiculo), ("motoristas", motorista)):
        assert (
            admin.patch(
                f"/api/{recurso}/{item['id']}", json={"ativo": False}
            ).status_code
            == 409
        )
    assert (
        admin.patch(
            f"/api/veiculos/{veiculo['id']}", json={"placa": "ABC1C35"}
        ).status_code
        == 409
    )
    with banco.begin() as conexao:
        conexao.execute(
            text(
                "UPDATE pesagem SET situacao = 'FINALIZADA', peso_inicial_kg = 1, "
                "peso_inicial_em = now(), peso_final_kg = 2, peso_final_em = now(), "
                "peso_liquido_kg = 1, classificacao = 'COM_MOVIMENTACAO'"
            )
        )
    desativado = admin.patch(f"/api/veiculos/{veiculo['id']}", json={"ativo": False})
    assert desativado.status_code == 200 and desativado.json()["ativo"] is False
    assert admin.get(f"/api/veiculos/{veiculo['id']}").status_code == 200


def test_logs_sem_query_string_nem_cpf(
    admin: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """CA-015."""
    with caplog.at_level(logging.INFO):
        admin.post("/api/motoristas", json={"nome": "Ana", "cpf": "52998224725"})
        admin.get("/api/veiculos", params={"placa": "ABC1234"})
    texto = "\n".join(r.getMessage() for r in caplog.records if r.name != "httpx")
    assert "52998224725" not in texto and "ABC1234" not in texto
    assert "GET /api/veiculos 200" in texto


def test_dois_posts_com_a_mesma_placa(admin: TestClient) -> None:
    """CA-016."""
    tipo_id = tipo(admin)
    status: list[int] = []

    def postar() -> None:
        corpo = {"placa": "ABC1234", "tipo_veiculo_id": tipo_id}
        status.append(admin.post("/api/veiculos", json=corpo).status_code)

    pedidos = [threading.Thread(target=postar) for _ in range(2)]
    for pedido in pedidos:
        pedido.start()
    for pedido in pedidos:
        pedido.join()
    assert sorted(status) == [201, 409]
