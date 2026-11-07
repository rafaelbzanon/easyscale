"""API da operação e do diagnóstico contra o banco real e os simuladores (specs 009 e 011).

Os ciclos da orquestração rodam um a um, chamados pelo teste no laço da aplicação
(`portal`), para o resultado não depender do tempo.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, date, datetime, time
from typing import Any

import pytest
from conftest import ORIGEM, Relogio, cadastrar, criar_operacao, criar_usuario, entrar
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from pesagem.api.dependencias import Contexto
from pesagem.dominio.operacao.maquina_estados import (
    EventoAutomatico,
    MotivoIntervencao,
    SituacaoOperacao,
    TipoEvento,
)
from pesagem.persistencia.banco import transacao
from pesagem.persistencia.repositorios.agendamento import NovoAgendamento

S = SituacaoOperacao
HOJE = date(2026, 11, 7)
EM = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
ACOES = (
    "tentar-novamente",
    "confirmar-posicao",
    "confirmar-balanca-vazia",
    "liberar-retorno",
    "aceitar-peso-final",
    "cancelar",
)


def contexto(cliente: TestClient) -> Contexto:
    ctx: Contexto = cliente.app.state.contexto  # type: ignore[attr-defined]
    return ctx


def rodar(cliente: TestClient, ciclo: Callable[[], Awaitable[None]]) -> None:
    cliente.portal.call(ciclo)  # type: ignore[union-attr]


def outro(cliente: TestClient, banco: Engine, perfil: str) -> TestClient:
    novo = TestClient(
        cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    )
    # Mesmo laço do cliente principal: sem isso, um comando agendado por uma ação
    # deste cliente morreria com o laço descartável de cada requisição.
    novo.portal = cliente.portal
    criar_usuario(banco, perfil.lower(), perfil)
    entrar(novo, perfil.lower())
    return novo


@pytest.fixture
def ids(banco: Engine) -> dict[str, int]:
    with transacao(banco) as t:
        return cadastrar(t.conexao, ("ABC1D23", "DEF5678", "GHI9J01"))


@pytest.fixture
def admin(banco: Engine, cliente: TestClient) -> TestClient:
    criar_usuario(banco, "chefe", "ADMINISTRADOR")
    entrar(cliente, "chefe")
    return cliente


def agendar(banco: Engine, ids: dict[str, int], veiculo: str = "veiculo0") -> int:
    with transacao(banco) as t:
        return t.agendamentos.criar_agendamento(
            NovoAgendamento(
                ids[veiculo],
                ids["motorista"],
                None,
                ids["produto"],
                "CARGA",
                HOJE,
                None,
                None,
                None,
                "USUARIO",
                ids["usuario"],
            ),
            HOJE,
            time(7, 0),
        ).agendamento_id


def pesagem(
    banco: Engine, ids: dict[str, int], veiculo: str = "veiculo0", **campos: Any
) -> int:
    """Cria uma pesagem e, se pedido, a leva direto a uma situação (sem comando)."""
    agendamento = agendar(banco, ids, veiculo)
    with transacao(banco) as t:
        registrada = criar_operacao(t, agendamento, ids["ponto"], EM)
        if campos:
            nova = replace(registrada.operacao, **campos)
            t.pesagens.gravar_transicao(
                registrada.pesagem_id,
                1,
                nova,
                EventoAutomatico(TipoEvento.BALANCA_DISPONIVEL),
                None,
                HOJE,
                EM,
            )
    return registrada.pesagem_id


def chegada(cliente: TestClient, *textos: tuple[str, str]) -> dict[str, Any]:
    """Simula a chegada (spec 011 §6.4) e roda um ciclo de identificação."""
    resposta = cliente.post(
        "/api/simuladores/chegadas",
        json={"textos": [{"texto": t, "confianca": c} for t, c in textos]},
    )
    assert resposta.status_code == 202, resposta.text
    rodar(cliente, contexto(cliente).orquestracao.ciclo_identificacao)
    ultima: dict[str, Any] = cliente.get("/api/operacao/estado").json()[
        "ultima_leitura_placa"
    ]
    return ultima


def acao(
    cliente: TestClient, pesagem_id: int, caminho: str, versao: int, motivo: str = "ok"
) -> Any:
    return cliente.post(
        f"/api/pesagens/{pesagem_id}/{caminho}",
        json={"versao": versao, "motivo": motivo},
    )


def test_permissoes(banco: Engine, cliente: TestClient, ids: dict[str, int]) -> None:
    """CA-001 e CA-002 (009); CA-001, CA-002 e CA-012 (011)."""
    assert cliente.get("/api/operacao/estado").status_code == 401
    assert cliente.get("/api/operacao/eventos").status_code == 401
    pesagem_id = pesagem(banco, ids)
    operador = outro(cliente, banco, "OPERADOR")
    auditor = outro(cliente, banco, "AUDITOR")
    for caminho in ACOES:
        assert acao(auditor, pesagem_id, caminho, 1).status_code == 403
        esperado = {409} if caminho == "tentar-novamente" else {403}
        assert acao(operador, pesagem_id, caminho, 1).status_code in esperado, caminho
    assert (
        operador.post(
            f"/api/pesagens/{pesagem_id}/liberar-caminhao", json={"motivo": "x"}
        ).status_code
        == 409
    )
    assert (
        auditor.post(
            "/api/leituras-placa/1/liberar-entrada",
            json={"agendamento_id": 1, "motivo": "x"},
        ).status_code
        == 403
    )
    for consulta in (
        "/api/operacao/estado",
        f"/api/pesagens/{pesagem_id}",
        "/api/dispositivos",
        "/api/leituras-placa",
    ):
        assert auditor.get(consulta).status_code == 200
    assert auditor.get("/api/cameras/identificacao/imagem-atual").status_code == 403
    assert (
        auditor.post("/api/imagens-decisao/1/excluir", json={"motivo": "x"}).status_code
        == 403
    )
    assert (
        operador.post(
            "/api/imagens-decisao/1/excluir", json={"motivo": "x"}
        ).status_code
        == 403
    )
    assert operador.get("/api/simuladores").status_code == 403
    assert (
        operador.get("/api/cameras/identificacao/imagem-atual").status_code == 409
    )  # sem imagem ainda


def test_estado_e_objeto_pesagem(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-003, CA-004 e CA-005 (009); CA-011 (011)."""
    primeira = pesagem(
        banco,
        ids,
        situacao=S.AGUARDANDO_INTERVENCAO,
        situacao_anterior=S.EM_CARGA_DESCARGA,
        motivo_intervencao=MotivoIntervencao.REINICIO_INCONCLUSIVO,
    )
    segunda = pesagem(banco, ids, "veiculo1", situacao=S.EM_CARGA_DESCARGA)
    pesagem(banco, ids, "veiculo2", situacao=S.CANCELADA)
    estado = admin.get("/api/operacao/estado").json()
    assert set(estado) == {
        "gerado_em",
        "tempo_real",
        "pesagens_abertas",
        "liberacoes_caminhao",
        "ultima_leitura_placa",
        "dispositivos",
    }
    assert estado["tempo_real"] == {
        "intervalo_heartbeat_ms": 100,
        "limite_sem_heartbeat_ms": 300,
    }
    abertas = estado["pesagens_abertas"]
    assert [p["id"] for p in abertas] == [
        primeira,
        segunda,
    ]  # ordem de chegada, sem terminais
    assert [c["cancela"] for c in estado["dispositivos"]["cancelas"]] == [
        "ENTRADA",
        "SAIDA",
    ]
    assert estado["dispositivos"]["balanca"]["modo"] == "SIMULADO"
    parada, carga = abertas
    assert (parada["situacao_anterior"], parada["motivo_intervencao"]) == (
        "EM_CARGA_DESCARGA",
        "REINICIO_INCONCLUSIVO",
    )
    assert (carga["situacao_anterior"], carga["motivo_intervencao"]) == (None, None)
    assert set(parada["acoes_disponiveis"]) == {"TENTAR_NOVAMENTE", "CANCELAR"}
    assert set(carga["acoes_disponiveis"]) == {"LIBERAR_RETORNO_MANUAL", "CANCELAR"}
    assert admin.get(f"/api/pesagens/{segunda}").json() == carga
    assert admin.get("/api/pesagens/999").status_code == 404
    dispositivos = admin.get("/api/dispositivos").json()
    assert dispositivos["intervalo_imagem_ms"] == 2000
    assert {c["modo"] for c in dispositivos["dispositivos"]["cancelas"]} == {"SIMULADO"}


def test_acoes_versao_motivo_e_rejeicao(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-013, CA-014, CA-015, CA-016 e CA-017."""
    pesagem_id = pesagem(
        banco,
        ids,
        situacao=S.AGUARDANDO_INTERVENCAO,
        situacao_anterior=S.ENTRADA_LIBERADA,
        motivo_intervencao=MotivoIntervencao.TEMPO_ESGOTADO,
    )
    for corpo in (
        {"versao": 2},
        {"versao": 2, "motivo": ""},
        {"versao": 2, "motivo": "x", "peso_kg": "1"},
        {"versao": 2, "motivo": "x", "responsavel": 9},
        {"motivo": "x"},
        {"versao": 2, "motivo": "x" * 201},
    ):
        assert (
            admin.post(
                f"/api/pesagens/{pesagem_id}/confirmar-posicao", json=corpo
            ).status_code
            == 422
        )
    antiga = acao(admin, pesagem_id, "confirmar-posicao", 1)
    assert antiga.json()["erro"]["campos"] == [
        {"campo": "versao", "codigo": "VERSAO_DESATUALIZADA"}
    ]
    rejeitada = acao(admin, pesagem_id, "aceitar-peso-final", 2)
    assert rejeitada.json()["erro"]["campos"] == [
        {"campo": "situacao", "codigo": "TRANSICAO_REJEITADA"}
    ]
    resposta = acao(admin, pesagem_id, "confirmar-posicao", 2, "câmera suja")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["situacao"], corpo["versao"], corpo["liberacao_manual"]) == (
        "FECHANDO_ENTRADA",
        3,
        True,
    )
    assert corpo["comando_pendente"] == {"comando": "FECHAR", "cancela": "ENTRADA"}
    with banco.connect() as conexao:
        eventos = conexao.execute(
            text(
                "SELECT tipo_registro, evento, responsavel_id, motivo FROM evento_operacao "
                "WHERE pesagem_id = :p AND evento IN ('ACEITAR_PESO_FINAL', 'CONFIRMAR_POSICAO_MANUAL') ORDER BY id"
            ),
            {"p": pesagem_id},
        ).all()
        admin_id = conexao.execute(
            text("SELECT id FROM usuario WHERE login = 'chefe'")
        ).scalar_one()
    assert [tuple(e) for e in eventos] == [
        ("TRANSICAO_REJEITADA", "ACEITAR_PESO_FINAL", admin_id, "ok"),
        ("TRANSICAO", "CONFIRMAR_POSICAO_MANUAL", admin_id, "câmera suja"),
    ]
    # O comando de fechar roda depois, numa tarefa; a pesagem segue pela máquina.
    rodar(admin, contexto(admin).orquestracao.aguardar_comandos_agendados)
    assert (
        admin.get(f"/api/pesagens/{pesagem_id}").json()["situacao"]
        == "POSICIONADA_INICIAL"
    )


def test_identificacao_e_liberacao_de_entrada(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-018 a CA-021 (009); CA-003 a CA-006 e CA-016 (011)."""
    agendamento = agendar(banco, ids)
    baixa = chegada(admin, ("BRASIL", "0.990"), ("ABC1D23", "0.500"))
    assert (baixa["decisao"], baixa["motivo"], baixa["pesagem_id"]) == (
        "NAO_AUTORIZADA",
        "CONFIANCA_BAIXA",
        None,
    )
    assert baixa["imagem_id"] is not None
    detalhe = admin.get(f"/api/leituras-placa/{baixa['id']}").json()
    textos = [t for leitura in detalhe["leituras"] for t in leitura["textos"]]
    assert {"texto": "BRASIL", "confianca": "0.990"} in textos
    imagem = admin.get(f"/api/imagens-decisao/{baixa['imagem_id']}/conteudo")
    assert (imagem.headers["content-type"], imagem.headers["cache-control"]) == (
        "image/jpeg",
        "no-store",
    )
    assert imagem.content[:2] == b"\xff\xd8"
    atual = admin.get("/api/cameras/identificacao/imagem-atual")
    assert atual.status_code == 200 and "last-modified" in atual.headers
    liberada = admin.post(
        f"/api/leituras-placa/{baixa['id']}/liberar-entrada",
        json={"agendamento_id": agendamento, "motivo": "placa suja"},
    )
    assert liberada.status_code == 201
    criada = liberada.json()
    assert (
        criada["situacao"],
        criada["liberacao_manual"],
        criada["agendamento_status"],
    ) == ("AGUARDANDO_BALANCA_INICIAL", True, "EM_ANDAMENTO")
    repetida = admin.post(
        f"/api/leituras-placa/{baixa['id']}/liberar-entrada",
        json={"agendamento_id": agendamento, "motivo": "de novo"},
    )
    assert repetida.status_code == 409
    sem_agendamento = chegada(admin, ("DEF5678", "0.950"))
    assert sem_agendamento["motivo"] == "SEM_AGENDAMENTO"
    nao_substituivel = admin.post(
        f"/api/leituras-placa/{sem_agendamento['id']}/liberar-entrada",
        json={"agendamento_id": agendamento, "motivo": "x"},
    )
    assert nao_substituivel.json()["erro"]["campos"] == [
        {"campo": "leitura_placa_id", "codigo": "MOTIVO_NAO_SUBSTITUIVEL"}
    ]
    assert chegada(admin)["motivo"] == "SEM_CANDIDATO"
    desatualizada = admin.post(
        f"/api/leituras-placa/{sem_agendamento['id']}/liberar-entrada",
        json={"agendamento_id": agendamento, "motivo": "x"},
    )
    assert (
        desatualizada.json()["erro"]["campos"][0]["codigo"] == "LEITURA_DESATUALIZADA"
    )
    # Abaixo do limiar não há placa selecionada; o filtro por placa acha a de DEF5678.
    lista = admin.get(
        "/api/leituras-placa", params={"decisao": "NAO_AUTORIZADA", "placa": "def-5678"}
    ).json()
    assert [item["id"] for item in lista["itens"]] == [sem_agendamento["id"]]
    assert (
        admin.get("/api/leituras-placa", params={"motivo": "SEM_CANDIDATO"}).json()[
            "total"
        ]
        == 1
    )


def test_autorizada_cria_pesagem(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-016 (011): placa acima do limiar e agendamento válido."""
    agendar(banco, ids)
    leitura = chegada(admin, ("ABC1D23", "0.950"))
    assert leitura["decisao"] == "AUTORIZADA" and leitura["pesagem_id"] is not None
    assert (
        admin.get(f"/api/pesagens/{leitura['pesagem_id']}").json()["situacao"]
        == "AGUARDANDO_BALANCA_INICIAL"
    )


def test_imagem_excluida(banco: Engine, admin: TestClient, ids: dict[str, int]) -> None:
    """CA-007 e CA-008 (011)."""
    leitura = chegada(admin, ("ABC1D23", "0.500"))
    caminho = f"/api/imagens-decisao/{leitura['imagem_id']}"
    assert admin.post(f"{caminho}/excluir", json={}).status_code == 422
    excluida = admin.post(
        f"{caminho}/excluir", json={"motivo": "pedido do titular"}
    ).json()
    assert (
        excluida["excluida"],
        excluida["excluida_por_nome"],
        excluida["motivo_exclusao"],
    ) == (True, "Chefe", "pedido do titular")
    for resposta in (
        admin.get(f"{caminho}/conteudo"),
        admin.post(f"{caminho}/excluir", json={"motivo": "x"}),
    ):
        assert resposta.json()["erro"]["campos"] == [
            {"campo": "imagem_id", "codigo": "IMAGEM_EXCLUIDA"}
        ]
    assert (
        admin.get(f"/api/leituras-placa/{leitura['id']}").json()["imagem_id"]
        == leitura["imagem_id"]
    )


def test_cancelar_na_balanca_e_liberar_caminhao(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-022 e CA-023."""
    pesagem_id = pesagem(banco, ids, situacao=S.ENTRADA_LIBERADA)
    livre = pesagem(banco, ids, "veiculo1", situacao=S.EM_CARGA_DESCARGA)
    assert (
        acao(admin, pesagem_id, "cancelar", 2, "desistiu").json()[
            "aguarda_liberacao_balanca"
        ]
        is True
    )
    estado = admin.get("/api/operacao/estado").json()
    assert [
        (item["pesagem_id"], item["etapa"]) for item in estado["liberacoes_caminhao"]
    ] == [(pesagem_id, "PENDENTE")]
    sem_pendencia = admin.post(
        f"/api/pesagens/{livre}/liberar-caminhao", json={"motivo": "x"}
    )
    assert sem_pendencia.json()["erro"]["campos"] == [
        {"campo": "pesagem_id", "codigo": "OPERACAO_NAO_OCUPA_BALANCA"}
    ]
    assert (
        admin.post(
            f"/api/pesagens/{pesagem_id}/liberar-caminhao", json={"motivo": "liberar"}
        ).status_code
        == 200
    )
    em_curso = admin.post(
        f"/api/pesagens/{pesagem_id}/liberar-caminhao", json={"motivo": "de novo"}
    )
    assert em_curso.json()["erro"]["campos"] == [
        {"campo": "pesagem_id", "codigo": "LIBERACAO_EM_CURSO"}
    ]
    etapa = admin.get("/api/operacao/estado").json()["liberacoes_caminhao"][0]
    assert (
        etapa["etapa"] == "AGUARDANDO_BALANCA_VAZIA"
        and etapa["pedido_por_nome"] == "Chefe"
    )
    rodar(
        admin, contexto(admin).orquestracao.ciclo_posicao
    )  # balança vazia pela câmera simulada
    assert admin.get("/api/operacao/estado").json()["liberacoes_caminhao"] == []


def test_falhas_de_balanca_e_cancela(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """CA-024 e CA-025 (009); CA-014, CA-015, CA-017 e CA-018 (011)."""
    orquestracao = contexto(admin).orquestracao
    posicionada = pesagem(banco, ids, situacao=S.POSICIONADA_INICIAL)
    rodar(admin, orquestracao.ciclo_balanca)  # simulador começa em SEM_RESPOSTA
    balanca = admin.get("/api/dispositivos").json()["dispositivos"]["balanca"]
    assert (balanca["comunicacao"], balanca["motivo_falha"]) == (
        "FALHA",
        "SEM_RESPOSTA",
    )
    assert admin.get(f"/api/pesagens/{posicionada}").json()["peso_inicial_kg"] is None
    for invalido in (
        {"cenario": "ESTAVEL", "peso_kg": "1", "amplitude_kg": "1"},
        {"cenario": "VOANDO", "peso_kg": None, "amplitude_kg": None},
        {"cenario": "INSTAVEL", "peso_kg": "1", "amplitude_kg": None},
    ):
        assert admin.post("/api/simuladores/balanca", json=invalido).status_code == 422
    alto = admin.post(
        "/api/simuladores/chegadas",
        json={"textos": [{"texto": "X", "confianca": "1.5"}]},
    )
    assert alto.status_code == 422
    assert admin.get("/api/simuladores").json()["balanca"]["cenario"] == "SEM_RESPOSTA"
    assert (
        admin.post(
            "/api/simuladores/cancelas/lateral", json={"cenario": "FALHA"}
        ).status_code
        == 404
    )
    cenarios = admin.post(
        "/api/simuladores/cancelas/entrada", json={"cenario": "SENSOR_SEM_RESPOSTA"}
    ).json()
    assert cenarios["cancelas"][0] == {
        "cancela": "ENTRADA",
        "cenario": "SENSOR_SEM_RESPOSTA",
    }
    simuladores = contexto(admin).simuladores
    assert simuladores is not None
    assert all(
        not c.comandos_enviados for c in simuladores._cancelas.values()
    )  # trocar não comanda
    # Com o sensor da entrada sem resposta, a fila não libera a balança (fail-safe);
    # a falha do comando aparece ao repetir a abertura de uma pesagem já reservada.
    with transacao(banco) as t:
        t.conexao.execute(
            text("UPDATE pesagem SET situacao = 'CANCELADA' WHERE id = :id"),
            {"id": posicionada},
        )
    fila = pesagem(
        banco,
        ids,
        "veiculo1",
        situacao=S.AGUARDANDO_INTERVENCAO,
        situacao_anterior=S.AUTORIZADA,
        motivo_intervencao=MotivoIntervencao.CANCELA_FALHA,
    )
    assert acao(admin, fila, "tentar-novamente", 2).json()["situacao"] == "AUTORIZADA"
    rodar(admin, orquestracao.aguardar_comandos_agendados)
    parada = admin.get(f"/api/pesagens/{fila}").json()
    assert (parada["situacao"], parada["motivo_intervencao"]) == (
        "AGUARDANDO_INTERVENCAO",
        "CANCELA_SEM_CONFIRMACAO",
    )
    entrada = admin.get("/api/dispositivos").json()["dispositivos"]["cancelas"][0]
    assert (entrada["estado"], entrada["ultimo_comando"]["resultado"]) == (
        "DESCONHECIDO",
        "SEM_CONFIRMACAO",
    )


def ler_eventos(linhas: Any, quantos: int, tipo: str) -> list[dict[str, Any]]:
    achados: list[dict[str, Any]] = []
    nome = None
    for linha in linhas:
        if linha.startswith("event: "):
            nome = linha.removeprefix("event: ")
        elif linha.startswith("data: ") and nome == tipo:
            achados.append(json.loads(linha.removeprefix("data: ")))
            if len(achados) == quantos:
                break
    return achados


def test_canal_de_eventos(
    banco: Engine, admin: TestClient, ids: dict[str, int], relogio: Relogio
) -> None:
    """CA-006, CA-007, CA-008 e CA-026."""
    pesagem_id = pesagem(banco, ids, situacao=S.EM_CARGA_DESCARGA)
    with admin.stream("GET", "/api/operacao/eventos") as canal:
        assert canal.headers["content-type"].startswith("text/event-stream")
        linhas = canal.iter_lines()
        assert (
            len(ler_eventos(linhas, 2, "heartbeat")) == 2
        )  # chegam sem outros eventos
        outro_cliente = TestClient(
            admin.app,
            base_url="https://pesagem.teste",
            headers={"Origin": ORIGEM},
            cookies=admin.cookies,
        )
        outro_cliente.portal = admin.portal  # mesmo laço (ver `outro`)
        assert (
            acao(outro_cliente, pesagem_id, "tentar-novamente", 2).status_code == 409
        )  # rejeição: sem evento
        assert (
            acao(
                outro_cliente, pesagem_id, "liberar-retorno", 2, "placa ilegível"
            ).status_code
            == 200
        )
        (evento,) = ler_eventos(linhas, 1, "pesagem")
        assert (evento["id"], evento["versao"], evento["situacao"]) == (
            pesagem_id,
            3,
            "AGUARDANDO_BALANCA_FINAL",
        )
        assert "cpf" not in json.dumps(evento)
        # Sessão vencida pelo tempo sem uso: o canal fecha sozinho.
        relogio.avancar(601)
        restante = list(linhas)
    assert not any(linha.startswith("event: pesagem") for linha in restante)


def test_partida_da_operacao(banco: Engine, configuracao_banco: Any) -> None:
    """CA-012 (009) e CA-013 (011): limite do heartbeat; com algum dispositivo em REAL o
    backend nem parte, então as rotas dos simuladores nunca existem com hardware real."""
    from conftest import AMBIENTE_OPERACAO, configuracao_api

    from pesagem.config import ErroConfiguracao, ler_configuracao_operacao
    from pesagem.dispositivos.erros import ErroDispositivo
    from pesagem.main import criar_aplicacao

    assert ler_configuracao_operacao(AMBIENTE_OPERACAO).tolerancia_movimentacao_kg == 20
    igual = {**AMBIENTE_OPERACAO, "PESAGEM_TEMPO_REAL_LIMITE_SEM_HEARTBEAT_MS": "5000"}
    with pytest.raises(ErroConfiguracao, match="LIMITE_SEM_HEARTBEAT"):
        ler_configuracao_operacao(igual)
    base = configuracao_api(configuracao_banco)
    for real_em in (
        replace(base.operacao, modo_balanca="REAL"),
        replace(base.operacao, modo_cancelas="REAL"),
        replace(base.operacao, modo_cameras="REAL"),
    ):
        real = replace(base, operacao=real_em)
        with pytest.raises(ErroDispositivo):  # sem protocolo ou sem implementação real
            criar_aplicacao(real, banco)


def test_cancela_sem_leitura_do_sensor_e_desconhecida(admin: TestClient) -> None:
    """Regressão (Tessera): antes da primeira consulta ao sensor, `estado` era null;
    a spec 009 §5.4 só admite ABERTA, FECHADA ou DESCONHECIDO."""
    for rota in ("/api/dispositivos", "/api/operacao/estado"):
        cancelas = admin.get(rota).json()["dispositivos"]["cancelas"]
        assert [c["estado"] for c in cancelas] == ["DESCONHECIDO", "DESCONHECIDO"]


def test_ciclos_parados_encerram_e_nao_mostram_ok(
    banco: Engine,
    configuracao_banco: Any,
    relogio: Relogio,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regressão (Lynx ALTO 2): a tarefa dos ciclos terminou e a API seguia de pé com o
    estado congelado. Agora o processo pede encerramento e nada aparece em ordem."""
    from conftest import configuracao_api

    import pesagem.main as modulo_main

    pedidos: list[bool] = []
    monkeypatch.setattr(
        modulo_main, "_pedir_encerramento", lambda: pedidos.append(True)
    )
    app = modulo_main.criar_aplicacao(
        configuracao_api(configuracao_banco), banco, relogio
    )
    orquestracao = app.state.contexto.orquestracao

    async def falhar() -> None:
        raise RuntimeError("ciclo quebrado")

    monkeypatch.setattr(orquestracao, "executar", falhar)
    with TestClient(
        app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
    ) as cliente:
        rodar(cliente, lambda: asyncio.sleep(0))  # deixa a tarefa terminar
        criar_usuario(banco, "chefe", "ADMINISTRADOR")
        entrar(cliente, "chefe")
        dispositivos = cliente.get("/api/dispositivos").json()["dispositivos"]
    assert pedidos == [True]
    assert dispositivos["balanca"]["comunicacao"] == "DESCONHECIDO"
    assert {c["estado"] for c in dispositivos["cancelas"]} == {"DESCONHECIDO"}
    assert dispositivos["posicao"]["resultado"] == "INCONCLUSIVA"


def test_motivo_so_com_espacos_e_recusado(
    banco: Engine, admin: TestClient, ids: dict[str, int]
) -> None:
    """Regressão (Lynx MÉDIO 5): motivo "   " passava (RN-011, spec 009 CA-014)."""
    pesagem_id = pesagem(banco, ids, situacao=S.EM_CARGA_DESCARGA)
    espacos = "   "
    assert acao(admin, pesagem_id, "liberar-retorno", 2, espacos).status_code == 422
    assert (
        admin.post(
            f"/api/pesagens/{pesagem_id}/liberar-caminhao", json={"motivo": espacos}
        ).status_code
        == 422
    )
    assert (
        admin.post(
            "/api/leituras-placa/1/liberar-entrada",
            json={"agendamento_id": 1, "motivo": espacos},
        ).status_code
        == 422
    )
    assert (
        admin.post(
            "/api/imagens-decisao/1/excluir", json={"motivo": espacos}
        ).status_code
        == 422
    )
    agendamento = agendar(banco, ids, "veiculo1")
    assert (
        admin.post(
            f"/api/agendamentos/{agendamento}/cancelar", json={"motivo": espacos}
        ).status_code
        == 422
    )
    # Com texto, o motivo vai sem os espaços das pontas.
    assert (
        acao(admin, pesagem_id, "liberar-retorno", 2, "  placa ilegível ").status_code
        == 200
    )
    with banco.connect() as conexao:
        motivo = conexao.execute(
            text(
                "SELECT motivo FROM evento_operacao WHERE evento = 'LIBERAR_RETORNO_MANUAL'"
            )
        ).scalar_one()
    assert motivo == "placa ilegível"
