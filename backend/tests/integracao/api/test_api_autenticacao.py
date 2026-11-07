"""API de autenticação e usuários contra o banco real (spec 012, CA-001 a CA-020)."""

import logging
import threading

import pytest
from conftest import AMBIENTE_OPERACAO, ORIGEM, Relogio, criar_usuario, entrar
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from pesagem.api.criar_administrador import (
    ErroCriacaoAdministrador,
    criar_administrador,
    main,
)
from pesagem.config import ErroConfiguracao, ler_configuracao

SENHA_ERRADA = {"login": "maria", "senha": "errada"}


@pytest.fixture
def admin(banco: Engine, cliente: TestClient) -> int:
    usuario_id = criar_usuario(banco, "admin", "ADMINISTRADOR")
    entrar(cliente, "admin")
    return usuario_id


def test_login_grava_cookie_seguro_e_devolve_usuario(
    banco: Engine, cliente: TestClient
) -> None:
    """CA-001, CA-011 (lista de permissões do perfil)."""
    criar_usuario(banco, "maria", "AUDITOR")
    resposta = cliente.post(
        "/api/sessoes", json={"login": "MARIA", "senha": "senha-certa"}
    )
    assert resposta.status_code == 201
    cookie = resposta.headers["set-cookie"]
    for atributo in (
        "pesagem_sessao=",
        "HttpOnly",
        "Secure",
        "SameSite=strict",
        "Path=/api",
    ):
        assert atributo.lower() in cookie.lower()
    assert "max-age" not in cookie.lower() and "expires" not in cookie.lower()
    corpo = resposta.json()
    assert (
        corpo["usuario"]["login"] == "maria" and corpo["usuario"]["perfil"] == "AUDITOR"
    )
    assert corpo["permissoes"] == [
        "CONSULTAR_AGENDAMENTOS",
        "CONSULTAR_IMAGENS_DECISAO",
        "CONSULTAR_OPERACAO",
    ]
    identificador = cliente.cookies["pesagem_sessao"]
    assert identificador not in resposta.text
    assert cliente.get("/api/sessoes/atual").json() == corpo


def test_falhas_de_login_tem_resposta_identica(
    banco: Engine, cliente: TestClient
) -> None:
    """CA-002."""
    criar_usuario(banco, "maria", "OPERADOR")
    criar_usuario(banco, "jose", "OPERADOR")
    cliente.post("/api/sessoes", json={"login": "admin", "senha": "x"})  # aquece
    with banco.begin() as conexao:
        conexao.execute(text("UPDATE usuario SET ativo = FALSE WHERE login = 'jose'"))
    respostas = [
        cliente.post("/api/sessoes", json={"login": "ninguem", "senha": "senha-certa"}),
        cliente.post("/api/sessoes", json=SENHA_ERRADA),
        cliente.post("/api/sessoes", json={"login": "jose", "senha": "senha-certa"}),
    ]
    assert {r.status_code for r in respostas} == {401}
    assert len({r.text for r in respostas}) == 1
    assert respostas[0].json()["erro"]["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_bloqueio_por_tentativas(
    banco: Engine, cliente: TestClient, relogio: Relogio
) -> None:
    """CA-003 e CA-004."""
    criar_usuario(banco, "maria", "OPERADOR")
    for _ in range(2):
        assert cliente.post("/api/sessoes", json=SENHA_ERRADA).status_code == 401
    entrar(cliente, "maria")  # zera o contador (CA-004)
    for _ in range(3):
        assert cliente.post("/api/sessoes", json=SENHA_ERRADA).status_code == 401
    certa = {"login": "maria", "senha": "senha-certa"}
    bloqueada = cliente.post("/api/sessoes", json=certa)
    assert (bloqueada.status_code, bloqueada.json()["erro"]["codigo"]) == (
        429,
        "LOGIN_BLOQUEADO",
    )
    # Login inexistente é bloqueado do mesmo jeito.
    for _ in range(3):
        cliente.post("/api/sessoes", json={"login": "fantasma", "senha": "x"})
    assert (
        cliente.post(
            "/api/sessoes", json={"login": "Fantasma", "senha": "x"}
        ).status_code
        == 429
    )
    # Tentativas durante o bloqueio não o prolongam.
    relogio.avancar(299)
    assert cliente.post("/api/sessoes", json=certa).status_code == 429
    relogio.avancar(2)
    assert cliente.post("/api/sessoes", json=certa).status_code == 201


def test_sessao_sem_cookie_desconhecida_ou_encerrada(
    banco: Engine, cliente: TestClient
) -> None:
    """CA-005 e CA-017."""
    assert cliente.get("/api/sessoes/atual").status_code == 401
    cliente.cookies.set(
        "pesagem_sessao", "desconhecido", domain="pesagem.teste", path="/api"
    )
    assert cliente.get("/api/sessoes/atual").status_code == 401
    cliente.cookies.clear()
    sem_sessao = cliente.request("DELETE", "/api/sessoes/atual", json={})
    assert sem_sessao.status_code == 204
    assert "max-age=0" in sem_sessao.headers["set-cookie"].lower()
    criar_usuario(banco, "maria", "OPERADOR")
    entrar(cliente, "maria")
    outra = TestClient(
        cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    )
    entrar(outra, "maria")
    assert cliente.request("DELETE", "/api/sessoes/atual", json={}).status_code == 204
    assert cliente.get("/api/sessoes/atual").status_code == 401
    assert outra.get("/api/sessoes/atual").status_code == 200  # só aquela sessão


def test_tempo_sem_uso(banco: Engine, cliente: TestClient, relogio: Relogio) -> None:
    """CA-006."""
    criar_usuario(banco, "maria", "OPERADOR")
    entrar(cliente, "maria")
    relogio.avancar(590)
    assert cliente.get("/api/sessoes/atual").status_code == 200  # renova
    relogio.avancar(590)
    assert cliente.get("/api/sessoes/atual").status_code == 200
    relogio.avancar(601)
    assert cliente.get("/api/sessoes/atual").status_code == 401


def test_desativar_derruba_as_sessoes(
    banco: Engine, cliente: TestClient, admin: int
) -> None:
    """CA-007 e CA-009."""
    maria = criar_usuario(banco, "maria", "OPERADOR")
    dela = TestClient(
        cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    )
    entrar(dela, "maria")
    resposta = cliente.patch(f"/api/usuarios/{maria}", json={"ativo": False})
    assert resposta.status_code == 200 and resposta.json()["ativo"] is False
    assert dela.get("/api/sessoes/atual").status_code == 401
    proprio = cliente.patch(f"/api/usuarios/{admin}", json={"ativo": False})
    assert proprio.status_code == 409
    assert proprio.json()["erro"]["campos"] == [
        {"campo": "ativo", "codigo": "PROPRIO_USUARIO"}
    ]
    assert cliente.get("/api/sessoes/atual").status_code == 200


def test_redefinir_senha(banco: Engine, cliente: TestClient, admin: int) -> None:
    """CA-008."""
    maria = criar_usuario(banco, "maria", "OPERADOR")
    dela = TestClient(
        cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    )
    entrar(dela, "maria")
    resposta = cliente.post(
        f"/api/usuarios/{maria}/redefinir-senha", json={"nova_senha": "nova"}
    )
    assert resposta.status_code == 204
    assert dela.get("/api/sessoes/atual").status_code == 401
    antiga = dela.post("/api/sessoes", json={"login": "maria", "senha": "senha-certa"})
    assert antiga.status_code == 401
    entrar(dela, "maria", "nova")


@pytest.mark.parametrize("perfil", ["OPERADOR", "AUDITOR"])
def test_so_administrador_gerencia_usuarios(
    banco: Engine, cliente: TestClient, perfil: str
) -> None:
    """CA-010."""
    criar_usuario(banco, "maria", perfil)
    entrar(cliente, "maria")
    pedidos = [
        cliente.get("/api/usuarios"),
        cliente.get("/api/usuarios/1"),
        cliente.post("/api/usuarios", json={}),
        cliente.patch("/api/usuarios/1", json={"ativo": True}),
        cliente.post("/api/usuarios/1/redefinir-senha", json={"nova_senha": "x"}),
        cliente.get("/api/perfis"),
    ]
    assert [p.status_code for p in pedidos] == [403] * 6
    assert pedidos[0].json()["erro"]["codigo"] == "SEM_PERMISSAO"


def test_mudanca_no_perfil_vale_na_requisicao_seguinte(
    banco: Engine, cliente: TestClient
) -> None:
    """CA-011."""
    criar_usuario(banco, "maria", "AUDITOR")
    entrar(cliente, "maria")
    with banco.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO perfil_permissao SELECT id, 'GERENCIAR_USUARIOS' FROM perfil "
                "WHERE codigo = 'AUDITOR'"
            )
        )
    assert (
        "GERENCIAR_USUARIOS" in cliente.get("/api/sessoes/atual").json()["permissoes"]
    )
    assert cliente.get("/api/perfis").status_code == 200


def test_criar_listar_e_hash(banco: Engine, cliente: TestClient, admin: int) -> None:
    """CA-012, CA-015 (maiúsculas) e a lista da spec 007 §3.3."""
    novo = {"nome": "Maria", "login": "Maria", "perfil": "OPERADOR", "senha": "s3gr3d0"}
    criado = cliente.post("/api/usuarios", json=novo)
    assert criado.status_code == 201
    assert set(criado.json()) == {"id", "nome", "login", "perfil", "ativo", "criado_em"}
    repetido = cliente.post("/api/usuarios", json={**novo, "login": "MARIA"})
    assert repetido.status_code == 409
    assert repetido.json()["erro"]["campos"] == [
        {"campo": "login", "codigo": "CONFLITO"}
    ]
    sem_perfil = cliente.post(
        "/api/usuarios", json={**novo, "login": "ana", "perfil": "CHEFE"}
    )
    assert sem_perfil.status_code == 422
    with banco.connect() as conexao:
        senha_hash = conexao.execute(
            text("SELECT senha_hash FROM usuario WHERE login = 'Maria'")
        ).scalar_one()
    assert "s3gr3d0" not in senha_hash and senha_hash.startswith("scrypt$16384$8$5$")
    lista = cliente.get(
        "/api/usuarios", params={"busca": "mar", "tamanho_pagina": 5}
    ).json()
    assert [u["login"] for u in lista["itens"]] == ["Maria"]
    assert cliente.get("/api/usuarios").json()["tamanho_pagina"] == 2
    acima = cliente.get("/api/usuarios", params={"tamanho_pagina": 6})
    assert acima.status_code == 422
    for corpo in (criado.text, lista.__repr__(), cliente.get("/api/usuarios").text):
        assert "senha" not in corpo
    perfis = cliente.get("/api/perfis").json()["itens"]
    assert [p["codigo"] for p in perfis] == ["ADMINISTRADOR", "AUDITOR", "OPERADOR"]


def test_dois_pedidos_com_o_mesmo_login(
    banco: Engine, cliente: TestClient, admin: int
) -> None:
    """CA-015 com dois pedidos ao mesmo tempo: um 201 e um 409."""
    novo = {"nome": "Ana", "login": "ana", "perfil": "OPERADOR", "senha": "x"}
    status: list[int] = []
    pedidos = [
        threading.Thread(
            target=lambda: status.append(
                cliente.post("/api/usuarios", json=novo).status_code
            )
        )
        for _ in range(2)
    ]
    for pedido in pedidos:
        pedido.start()
    for pedido in pedidos:
        pedido.join()
    assert sorted(status) == [201, 409]


def test_origem_e_tipo_de_conteudo(banco: Engine, cliente: TestClient) -> None:
    """CA-013 e CA-014: conferidos antes de tudo, inclusive no login, sem efeito."""
    criar_usuario(banco, "maria", "OPERADOR")
    corpo = {"login": "maria", "senha": "senha-certa"}
    sem_origem = cliente.post("/api/sessoes", json=corpo, headers={"Origin": ""})
    outra = cliente.post(
        "/api/sessoes", json=corpo, headers={"Origin": "https://outro.site"}
    )
    formulario = cliente.post("/api/sessoes", data=corpo)
    assert [r.status_code for r in (sem_origem, outra, formulario)] == [403, 403, 415]
    assert sem_origem.json()["erro"]["codigo"] == "ORIGEM_NAO_PERMITIDA"
    assert formulario.json()["erro"]["codigo"] == "TIPO_CONTEUDO_INVALIDO"
    assert "set-cookie" not in sem_origem.headers
    with banco.connect() as conexao:
        assert conexao.execute(text("SELECT count(*) FROM sessao")).scalar_one() == 0
    assert (
        cliente.get("/api/sessoes/atual").status_code == 401
    )  # GET não confere origem


def test_patch_so_aceita_ativo(banco: Engine, cliente: TestClient, admin: int) -> None:
    """CA-016 e o corpo de erro da spec 007 §3.2 na validação automática."""
    maria = criar_usuario(banco, "maria", "OPERADOR")
    resposta = cliente.patch(
        f"/api/usuarios/{maria}", json={"ativo": False, "nome": "X"}
    )
    assert resposta.status_code == 422
    erro = resposta.json()["erro"]
    assert (
        erro["codigo"] == "CAMPO_INVALIDO"
        and {"campo": "nome", "codigo": "CAMPO_INVALIDO"} in erro["campos"]
    )
    assert cliente.get("/api/usuarios/999").json()["erro"]["codigo"] == "NAO_ENCONTRADO"
    metodo = cliente.request("DELETE", f"/api/usuarios/{maria}", json={})
    assert (metodo.status_code, metodo.json()["erro"]["codigo"]) == (
        405,
        "METODO_NAO_PERMITIDO",
    )


def test_partida_exige_todas_as_variaveis() -> None:
    """CA-018 (e PESAGEM_PATIO_FUSO, spec 008 §6.9)."""
    completo = {
        "PESAGEM_BANCO_HOST": "db",
        "PESAGEM_BANCO_PORTA": "5432",
        "PESAGEM_BANCO_NOME": "p",
        "PESAGEM_BANCO_USUARIO": "p",
        "PESAGEM_BANCO_SENHA": "s",
        "PESAGEM_PATIO_FUSO": "America/Sao_Paulo",
        "PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS": "https://a.b, https://c.d:8443",
        "PESAGEM_SEGURANCA_SESSAO_TEMPO_SEM_USO_S": "600",
        "PESAGEM_SEGURANCA_LOGIN_TENTATIVAS_MAXIMAS": "5",
        "PESAGEM_SEGURANCA_LOGIN_BLOQUEIO_S": "300",
        "PESAGEM_GERAL_TAMANHO_PAGINA_PADRAO": "50",
        "PESAGEM_GERAL_TAMANHO_PAGINA_MAXIMO": "200",
        **AMBIENTE_OPERACAO,
    }
    assert ler_configuracao(completo).seguranca.origens_permitidas == {
        "https://a.b",
        "https://c.d:8443",
    }
    for nome in completo:
        with pytest.raises(ErroConfiguracao, match=nome):
            ler_configuracao({**completo, nome: ""})
    invalidos = {
        "PESAGEM_PATIO_FUSO": "Lua/Base",
        "PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS": "https://a.b/caminho",
        "PESAGEM_SEGURANCA_SESSAO_TEMPO_SEM_USO_S": "0",
        "PESAGEM_SEGURANCA_LOGIN_TENTATIVAS_MAXIMAS": "x",
        "PESAGEM_GERAL_TAMANHO_PAGINA_PADRAO": "500",
    }
    for nome, valor in invalidos.items():
        with pytest.raises(ErroConfiguracao, match=nome):
            ler_configuracao({**completo, nome: valor})


def test_primeiro_administrador(banco: Engine) -> None:
    """CA-019."""
    assert main(["--senha", "x"]) == 2
    respostas = iter(["Admin", "admin"])
    senhas = iter(["s", "s"])
    usuario_id = criar_administrador(
        banco, lambda _: next(respostas), lambda _: next(senhas)
    )
    with banco.connect() as conexao:
        perfil = conexao.execute(
            text(
                "SELECT p.codigo FROM usuario u JOIN perfil p ON p.id = u.perfil_id WHERE u.id = :id"
            ),
            {"id": usuario_id},
        ).scalar_one()
    assert perfil == "ADMINISTRADOR"
    with pytest.raises(ErroCriacaoAdministrador, match="já existe"):
        criar_administrador(
            banco, lambda _: "Outro" if _ == "Nome: " else "outro", lambda _: "s"
        )
    with pytest.raises(ErroCriacaoAdministrador, match="não conferem"):
        senhas_diferentes = iter(["a", "b"])
        criar_administrador(banco, lambda _: "x", lambda _: next(senhas_diferentes))


def test_logs_e_auditoria_sem_segredos(
    banco: Engine, cliente: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """CA-020."""
    criar_usuario(banco, "maria", "OPERADOR")
    with caplog.at_level(logging.INFO):
        cliente.post(
            "/api/sessoes", json={"login": "senha-no-campo", "senha": "segredo1"}
        )
        cliente.post("/api/sessoes", json={"login": "maria", "senha": "senha-certa"})
        cliente.get("/api/usuarios", params={"busca": "placa-ABC1234"})
    identificador = cliente.cookies["pesagem_sessao"]
    # Só os registros do servidor: o do cliente de teste (httpx) não conta.
    texto = "\n".join(r.getMessage() for r in caplog.records if r.name != "httpx")
    for segredo in (
        "senha-no-campo",
        "segredo1",
        "senha-certa",
        identificador,
        "ABC1234",
    ):
        assert segredo not in texto
    assert "POST /api/sessoes 401" in texto
    with banco.connect() as conexao:
        auditoria = conexao.execute(
            text(
                "SELECT tipo, usuario_afetado_id IS NULL FROM registro_auditoria ORDER BY id"
            )
        ).all()
        tentativas = (
            conexao.execute(text("SELECT chave FROM tentativa_acesso")).scalars().all()
        )
    assert [tuple(a) for a in auditoria] == [
        ("LOGIN_RECUSADO", True),
        ("LOGIN_ACEITO", False),
    ]
    assert (
        all("senha" not in chave for chave in tentativas) and len(tentativas[0]) == 64
    )
