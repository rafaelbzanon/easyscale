"""Apoio dos testes de ponta a ponta (spec 028).

Os fixtures do PostgreSQL em contêiner, do relógio e do cliente HTTP são os de
`tests/integracao/conftest.py`, carregados pelo caminho: um segundo `conftest.py`
com o mesmo nome quebraria o `from conftest import` dos testes de integração.
Só a API HTTP é usada; os ciclos da orquestração são chamados pelo teste, como na
integração do Keel, para o resultado não depender do tempo.
"""

import importlib.util
import sys
from collections.abc import Awaitable, Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from pesagem.api.dependencias import Contexto

_CAMINHO = Path(__file__).resolve().parents[1] / "integracao" / "conftest.py"
_especificacao = importlib.util.spec_from_file_location("conftest_integracao", _CAMINHO)
assert _especificacao is not None and _especificacao.loader is not None
_base = importlib.util.module_from_spec(_especificacao)
sys.modules["conftest_integracao"] = _base
_especificacao.loader.exec_module(_base)

ORIGEM = _base.ORIGEM
Relogio = _base.Relogio
configuracao_banco = _base.configuracao_banco
engine = _base.engine
banco = _base.banco
relogio = _base.relogio
cliente = _base.cliente
criar_usuario = _base.criar_usuario
entrar = _base.entrar

HOJE = "2026-11-07"  # o relógio dos testes começa às 09:00 no fuso do pátio
Ids = dict[str, int]


def contexto(cliente: TestClient) -> Contexto:
    ctx: Contexto = cliente.app.state.contexto  # type: ignore[attr-defined]
    return ctx


def rodar(cliente: TestClient, ciclo: Callable[[], Awaitable[None]]) -> None:
    cliente.portal.call(ciclo)  # type: ignore[union-attr]


def usuario(cliente: TestClient, banco: Engine, perfil: str) -> TestClient:
    """Cliente logado pela API com outro perfil (o administrador cria os usuários)."""
    novo = TestClient(
        cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    )
    # Sem isto cada requisição roda num laço novo, que morre com ela e leva junto a
    # tarefa do comando agendado pela ação manual (spec 009 §6.3).
    novo.portal = cliente.portal
    criar_usuario(banco, perfil.lower(), perfil)
    entrar(novo, perfil.lower())
    return novo


@pytest.fixture
def admin(banco: Engine, cliente: TestClient) -> TestClient:
    # O primeiro administrador nasce pelo comando de instalação (spec 012 §6.10);
    # o resto do cadastro e o login seguem pela API.
    criar_usuario(banco, "chefe", "ADMINISTRADOR")
    resposta = cliente.post(
        "/api/sessoes", json={"login": "chefe", "senha": "senha-certa"}
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["usuario"]["perfil"] == "ADMINISTRADOR"
    return cliente


def criar(cliente: TestClient, rota: str, corpo: dict[str, Any]) -> dict[str, Any]:
    resposta = cliente.post(rota, json=corpo)
    assert resposta.status_code == 201, resposta.text
    criado: dict[str, Any] = resposta.json()
    return criado


def cadastrar_pela_api(cliente: TestClient, placas: tuple[str, ...]) -> Ids:
    """Cadastros das specs 007 e 008, só pelas rotas. Um veículo por placa."""
    ids: Ids = {
        "transportadora": criar(
            cliente,
            "/api/transportadoras",
            {"razao_social": "Transportes Serra", "cnpj": "11222333000181"},
        )["id"],
        "motorista": criar(
            cliente, "/api/motoristas", {"nome": "Ana Lima", "cpf": "52998224725"}
        )["id"],
        "tipo": criar(cliente, "/api/tipos-veiculo", {"descricao": "Truck"})["id"],
        "produto": criar(
            cliente, "/api/produtos", {"codigo": "SOJA", "descricao": "Soja"}
        )["id"],
        "faixa": criar(
            cliente,
            "/api/faixas-horario",
            {"hora_inicio": "08:00", "hora_fim": "10:00", "capacidade": 5},
        )["id"],
    }
    for placa in placas:
        ids[placa] = criar(
            cliente,
            "/api/veiculos",
            {"placa": placa, "tipo_veiculo_id": ids["tipo"]},
        )["id"]
    return ids


def agendar(
    cliente: TestClient, ids: Ids, placa: str, tipo: str = "CARGA", **extra: Any
) -> dict[str, Any]:
    """Agendamento manual (RN-001): quem chama é uma pessoa logada."""
    return criar(
        cliente,
        "/api/agendamentos",
        {
            "veiculo_id": ids[placa],
            "motorista_id": ids["motorista"],
            "produto_id": ids["produto"],
            "tipo_operacao": tipo,
            "data_prevista": HOJE,
            **extra,
        },
    )


def chegada(cliente: TestClient, *textos: tuple[str, str]) -> dict[str, Any]:
    """Simula a chegada (spec 011 §6.4), roda a identificação e devolve a decisão."""
    resposta = cliente.post(
        "/api/simuladores/chegadas",
        json={"textos": [{"texto": t, "confianca": c} for t, c in textos]},
    )
    assert resposta.status_code == 202, resposta.text
    rodar(cliente, contexto(cliente).orquestracao.ciclo_identificacao)
    leitura: dict[str, Any] = cliente.get("/api/operacao/estado").json()[
        "ultima_leitura_placa"
    ]
    return leitura


def posicao(cliente: TestClient, cenario: str) -> None:
    resposta = cliente.post("/api/simuladores/posicao", json={"cenario": cenario})
    assert resposta.status_code == 200, resposta.text


def cancela(cliente: TestClient, qual: str, cenario: str) -> None:
    resposta = cliente.post(
        f"/api/simuladores/cancelas/{qual}", json={"cenario": cenario}
    )
    assert resposta.status_code == 200, resposta.text


def balanca(
    cliente: TestClient,
    cenario: str,
    peso_kg: str | Decimal | None = None,
    amplitude_kg: str | None = None,
) -> None:
    resposta = cliente.post(
        "/api/simuladores/balanca",
        json={
            "cenario": cenario,
            "peso_kg": None if peso_kg is None else str(peso_kg),
            "amplitude_kg": amplitude_kg,
        },
    )
    assert resposta.status_code == 200, resposta.text


def ciclos(cliente: TestClient, *nomes: str) -> None:
    orquestracao = contexto(cliente).orquestracao
    for nome in nomes:
        rodar(cliente, getattr(orquestracao, f"ciclo_{nome}"))
    rodar(cliente, orquestracao.aguardar_comandos_agendados)


def pesagem(cliente: TestClient, pesagem_id: int) -> dict[str, Any]:
    resposta = cliente.get(f"/api/pesagens/{pesagem_id}")
    assert resposta.status_code == 200, resposta.text
    corpo: dict[str, Any] = resposta.json()
    return corpo


def situacao(cliente: TestClient, pesagem_id: int) -> str:
    return str(pesagem(cliente, pesagem_id)["situacao"])


def acao(
    cliente: TestClient, pesagem_id: int, caminho: str, motivo: str = "teste"
) -> Any:
    """Ação manual com a versão que a tela acabou de ver (spec 009 §6.3).

    O 200 só diz que a transição foi gravada; o comando da cancela roda numa tarefa
    depois. Espera essa tarefa (sem sleep) para o teste conferir o resultado dela.
    """
    resposta = cliente.post(
        f"/api/pesagens/{pesagem_id}/{caminho}",
        json={"versao": pesagem(cliente, pesagem_id)["versao"], "motivo": motivo},
    )
    rodar(cliente, contexto(cliente).orquestracao.aguardar_comandos_agendados)
    return resposta


def cancelas(cliente: TestClient) -> dict[str, dict[str, Any]]:
    itens = cliente.get("/api/dispositivos").json()["dispositivos"]["cancelas"]
    return {item["cancela"]: item for item in itens}


# --- etapas do fluxo (cada uma confere a situação a que deve chegar) ---


def liberar_balanca(cliente: TestClient, pesagem_id: int) -> None:
    """Balança vazia, fila anda: reserva e abertura da entrada (RN-012, RN-019)."""
    posicao(cliente, "AUSENTE")
    ciclos(cliente, "posicao", "fila")
    assert situacao(cliente, pesagem_id) in {"ENTRADA_LIBERADA", "RETORNO_LIBERADO"}


def posicionar(cliente: TestClient, pesagem_id: int, esperada: str) -> None:
    """Caminhão em posição: a entrada fecha e a pesagem espera o peso."""
    posicao(cliente, "CONFIRMADA")
    ciclos(cliente, "posicao")
    assert situacao(cliente, pesagem_id) == esperada


def pesar(
    cliente: TestClient, relogio: Any, pesagem_id: int, peso_kg: str, esperada: str
) -> None:
    """Balança estável: três leituras da série configurada, meio segundo entre elas."""
    balanca(cliente, "ESTAVEL", peso_kg)
    for _ in range(3):
        relogio.avancar(0.5)
        ciclos(cliente, "balanca")
    assert situacao(cliente, pesagem_id) == esperada


def sair_da_balanca(cliente: TestClient, pesagem_id: int, esperada: str) -> None:
    posicao(cliente, "AUSENTE")
    ciclos(cliente, "posicao")
    assert situacao(cliente, pesagem_id) == esperada


def ida(cliente: TestClient, relogio: Any, placa: str, peso_inicial: str) -> int:
    """Da chegada da placa até a carga: devolve o id da pesagem em EM_CARGA_DESCARGA."""
    leitura = chegada(cliente, (placa, "0.950"))
    assert leitura["decisao"] == "AUTORIZADA"
    pesagem_id = int(leitura["pesagem_id"])
    liberar_balanca(cliente, pesagem_id)
    posicionar(cliente, pesagem_id, "POSICIONADA_INICIAL")
    pesar(cliente, relogio, pesagem_id, peso_inicial, "SAIDA_INICIAL_LIBERADA")
    sair_da_balanca(cliente, pesagem_id, "EM_CARGA_DESCARGA")
    return pesagem_id


def volta(cliente: TestClient, placa: str, pesagem_id: int) -> None:
    """Placa lida de novo na volta (RN-018): até o caminhão em posição para a pesagem final."""
    leitura = chegada(cliente, (placa, "0.950"))
    assert (leitura["decisao"], leitura["pesagem_id"]) == ("RETORNO_ACEITO", pesagem_id)
    liberar_balanca(cliente, pesagem_id)
    posicionar(cliente, pesagem_id, "POSICIONADA_FINAL")


def volta_liberada_pelo_administrador(
    cliente: TestClient, pesagem_id: int, motivo: str = "placa ilegível na volta"
) -> None:
    """Placa não reconhecida na volta: o administrador libera o retorno (spec 009 §6.7)."""
    resposta = acao(cliente, pesagem_id, "liberar-retorno", motivo)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["situacao"] == "AGUARDANDO_BALANCA_FINAL"
    liberar_balanca(cliente, pesagem_id)
    posicionar(cliente, pesagem_id, "POSICIONADA_FINAL")


def todos(cliente: TestClient, rota: str, **filtros: Any) -> list[dict[str, Any]]:
    """Todas as páginas de uma lista (spec 007 §3.3); a página dos testes é pequena."""
    itens: list[dict[str, Any]] = []
    pagina = 1
    while True:
        corpo = cliente.get(
            rota, params={**filtros, "pagina": pagina, "tamanho_pagina": 5}
        ).json()
        itens += corpo["itens"]
        if len(itens) >= corpo["total"]:
            return itens
        pagina += 1
