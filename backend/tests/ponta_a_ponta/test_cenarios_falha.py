"""Cenários 2, 3, 5 e 6 do artigo e as falhas do AGENTS.md §7.2 que a API mostra (spec 028).

Cada falha termina em estado seguro: ninguém entra, nenhum peso é gravado, nenhuma
cancela é comandada às cegas.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from ponta_a_ponta.apoio import (
    Relogio,
    acao,
    agendar,
    balanca,
    cadastrar_pela_api,
    cancela,
    cancelas,
    chegada,
    ciclos,
    ida,
    liberar_balanca,
    pesagem,
    pesar,
    posicao,
    posicionar,
    sair_da_balanca,
    situacao,
    todos,
    usuario,
    volta,
    volta_liberada_pelo_administrador,
)


def eventos(cliente: TestClient, pesagem_id: int) -> list[dict[str, Any]]:
    return todos(cliente, f"/api/pesagens/{pesagem_id}/eventos")


def sem_comando(cliente: TestClient) -> bool:
    return all(c["ultimo_comando"] is None for c in cancelas(cliente).values())


def test_sem_agendamento_e_veiculo_nao_cadastrado(admin: TestClient) -> None:
    """CA-006 (cenário 2): RF-009, RN-002, RN-003, AGENTS.md §7.2."""
    ids = cadastrar_pela_api(admin, ("ABC1D23", "DEF5678"))
    agendar(admin, ids, "ABC1D23")
    sem = chegada(admin, ("DEF5678", "0.950"))
    assert (sem["decisao"], sem["motivo"], sem["pesagem_id"]) == (
        "NAO_AUTORIZADA",
        "SEM_AGENDAMENTO",
        None,
    )
    assert sem["imagem_id"] is not None  # a evidência fica guardada (RN-022)
    desconhecida = chegada(admin, ("XYZ9K88", "0.950"))
    assert desconhecida["motivo"] == "VEICULO_NAO_CADASTRADO"
    estado = admin.get("/api/operacao/estado").json()
    assert estado["pesagens_abertas"] == [] and sem_comando(admin)
    assert admin.get("/api/pesagens").json()["total"] == 0
    # A decisão fica registrada para auditoria (RF-019).
    motivos = [
        item["motivo"]
        for item in todos(admin, "/api/leituras-placa", decisao="NAO_AUTORIZADA")
    ]
    assert sorted(motivos) == ["SEM_AGENDAMENTO", "VEICULO_NAO_CADASTRADO"]


def test_reconhecimento_inconclusivo_e_liberacao_manual(
    banco: Engine, admin: TestClient
) -> None:
    """CA-007 (cenário 3): RF-007, RF-008, RN-003, RN-016, AGENTS.md §7.2."""
    ids = cadastrar_pela_api(admin, ("ABC1D23", "DEF5678"))
    agendamento = agendar(admin, ids, "ABC1D23")
    casos = [
        ((), "SEM_CANDIDATO"),
        ((("BRASIL", "0.990"),), "PLACA_INVALIDA"),
        ((("ABC1D23", "0.950"), ("DEF5678", "0.940")), "AMBIGUA"),
        ((("ABC1D23", "0.500"),), "CONFIANCA_BAIXA"),
    ]
    for textos, motivo in casos:
        leitura = chegada(admin, *textos)
        assert (leitura["decisao"], leitura["motivo"]) == ("NAO_AUTORIZADA", motivo)
        assert leitura["pesagem_id"] is None
    assert admin.get("/api/operacao/estado").json()["pesagens_abertas"] == []
    assert sem_comando(admin)
    # Sem imagem nova a análise não registra nada (nada a analisar).
    total = admin.get("/api/leituras-placa").json()["total"]
    ciclos(admin, "identificacao")
    assert admin.get("/api/leituras-placa").json()["total"] == total
    # Os textos rejeitados ficam visíveis para o operador decidir (RF-022).
    detalhe = admin.get(f"/api/leituras-placa/{leitura['id']}").json()
    assert detalhe["leituras"][0]["textos"][0]["confianca"] == "0.500"
    # Só o administrador libera; o operador não (RN-016).
    operador = usuario(admin, banco, "OPERADOR")
    pedido = {"agendamento_id": agendamento["id"], "motivo": "placa suja"}
    rota = f"/api/leituras-placa/{leitura['id']}/liberar-entrada"
    assert operador.post(rota, json=pedido).status_code == 403
    criada = admin.post(rota, json=pedido)
    assert criada.status_code == 201
    assert (criada.json()["situacao"], criada.json()["liberacao_manual"]) == (
        "AGUARDANDO_BALANCA_INICIAL",
        True,
    )
    # A entrada só abre pela fila da balança, nunca na hora da liberação (RN-019).
    assert sem_comando(admin)


def test_balanca_falha_e_leitura_rejeitada(
    banco: Engine, admin: TestClient, relogio: Relogio
) -> None:
    """CA-008 (cenário 5): RF-013, RN-004, RN-005, RNF-005, RNF-009, AGENTS.md §7.2."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendar(admin, ids, "ABC1D23")
    pesagem_id = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    liberar_balanca(admin, pesagem_id)
    posicionar(admin, pesagem_id, "POSICIONADA_INICIAL")

    def sem_peso() -> None:
        assert pesagem(admin, pesagem_id)["peso_inicial_kg"] is None
        assert situacao(admin, pesagem_id) == "POSICIONADA_INICIAL"

    for cenario, motivo in (
        ("SEM_RESPOSTA", "SEM_RESPOSTA"),
        ("QUADRO_CORROMPIDO", "QUADRO_CORROMPIDO"),
        ("DESCONECTADA", "DESCONECTADA"),
    ):
        balanca(admin, cenario)
        relogio.avancar(0.5)
        ciclos(admin, "balanca")
        dispositivo = admin.get("/api/dispositivos").json()["dispositivos"]["balanca"]
        assert (dispositivo["comunicacao"], dispositivo["motivo_falha"]) == (
            "FALHA",
            motivo,
        )
        sem_peso()
    balanca(admin, "INSTAVEL", "15000", "50")
    for _ in range(3):
        relogio.avancar(0.5)
        ciclos(admin, "balanca")
    avaliacao = admin.get("/api/dispositivos").json()["dispositivos"]["balanca"]
    assert avaliacao["comunicacao"] == "OK"
    assert (
        avaliacao["avaliacao_peso"]["aceito"],
        avaliacao["avaliacao_peso"]["motivo_rejeicao"],
    ) == (
        False,
        "INSTAVEL",
    )
    sem_peso()
    balanca(admin, "ESTAVEL", "50")  # abaixo do mínimo configurado (100 kg)
    for _ in range(3):
        relogio.avancar(0.5)
        ciclos(admin, "balanca")
    rejeicao = admin.get("/api/dispositivos").json()["dispositivos"]["balanca"]
    assert rejeicao["avaliacao_peso"]["motivo_rejeicao"] == "FORA_DE_FAIXA"
    sem_peso()
    registrados = {
        e["motivo_dispositivo"]
        for e in eventos(admin, pesagem_id)
        if e["tipo"] == "EVENTO_REGISTRADO"
    }
    assert {
        "SEM_RESPOSTA",
        "QUADRO_CORROMPIDO",
        "DESCONECTADA",
        "INSTAVEL",
        "FORA_DE_FAIXA",
    } <= registrados
    # A etapa não vence sozinha para sempre: depois do limite, para e pede o operador.
    relogio.avancar(61)
    ciclos(admin, "posicao")
    parada = pesagem(admin, pesagem_id)
    assert (parada["situacao"], parada["motivo_intervencao"]) == (
        "AGUARDANDO_INTERVENCAO",
        "TEMPO_ESGOTADO",
    )
    operador = usuario(admin, banco, "OPERADOR")
    assert acao(operador, pesagem_id, "tentar-novamente").status_code == 200
    assert situacao(admin, pesagem_id) == "POSICIONADA_INICIAL"
    pesar(admin, relogio, pesagem_id, "15000", "SAIDA_INICIAL_LIBERADA")
    assert pesagem(admin, pesagem_id)["peso_inicial_kg"] == "15000.000"


@pytest.mark.parametrize(
    ("cenario", "motivo", "resultado", "tentativas"),
    [
        ("FALHA", "CANCELA_FALHA", "FALHA", 1),
        ("NAO_MOVE", "CANCELA_SEM_CONFIRMACAO", "SEM_CONFIRMACAO", 2),
    ],
)
def test_cancela_que_falha_e_tentar_novamente(
    banco: Engine,
    admin: TestClient,
    cenario: str,
    motivo: str,
    resultado: str,
    tentativas: int,
) -> None:
    """CA-009 (cenário 6): RF-011, RN-007, spec 004 CA-009 e CA-010, AGENTS.md §7.1.3 e §7.1.4."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendar(admin, ids, "ABC1D23")
    pesagem_id = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    cancela(admin, "entrada", cenario)
    posicao(admin, "AUSENTE")
    ciclos(admin, "posicao", "fila")
    parada = pesagem(admin, pesagem_id)
    assert (parada["situacao"], parada["motivo_intervencao"]) == (
        "AGUARDANDO_INTERVENCAO",
        motivo,
    )
    abrir = [e for e in eventos(admin, pesagem_id) if e["tipo"] == "COMANDO_CANCELA"]
    assert len(abrir) == 1  # um comando só, sem reenvio às cegas
    assert (abrir[0]["comando"], abrir[0]["resultado"], abrir[0]["tentativas"]) == (
        "ABRIR",
        resultado,
        tentativas,
    )
    ciclos(admin, "posicao", "fila")  # nada anda sozinho
    assert situacao(admin, pesagem_id) == "AGUARDANDO_INTERVENCAO"
    # O operador tenta de novo, com a cancela já consertada: um comando novo.
    cancela(admin, "entrada", "CONFIRMADO")
    operador = usuario(admin, banco, "OPERADOR")
    assert acao(operador, pesagem_id, "tentar-novamente").status_code == 200
    ciclos(admin)
    assert situacao(admin, pesagem_id) == "ENTRADA_LIBERADA"
    comandos = [e for e in eventos(admin, pesagem_id) if e["tipo"] == "COMANDO_CANCELA"]
    assert [c["resultado"] for c in comandos] == [resultado, "CONFIRMADO"]


def test_cancela_sem_confirmacao_vira_desconhecida(admin: TestClient) -> None:
    """CA-010 (cenário 6): RN-007, AGENTS.md §7.2 (estado desconhecido, nunca sucesso)."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendar(admin, ids, "ABC1D23")
    pesagem_id = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    liberar_balanca(admin, pesagem_id)
    cancela(admin, "entrada", "SENSOR_SEM_RESPOSTA")
    posicao(admin, "CONFIRMADA")
    ciclos(admin, "posicao")
    parada = pesagem(admin, pesagem_id)
    assert (parada["situacao"], parada["motivo_intervencao"]) == (
        "AGUARDANDO_INTERVENCAO",
        "CANCELA_SEM_CONFIRMACAO",
    )
    entrada = cancelas(admin)["ENTRADA"]
    assert (entrada["estado"], entrada["ultimo_comando"]["resultado"]) == (
        "DESCONHECIDO",
        "SEM_CONFIRMACAO",
    )
    assert acao(admin, pesagem_id, "tentar-novamente").status_code == 200
    ciclos(admin)
    assert situacao(admin, pesagem_id) == "AGUARDANDO_INTERVENCAO"  # sensor ainda mudo


def test_posicao_inconclusiva_nao_avanca(
    banco: Engine, admin: TestClient, relogio: Relogio
) -> None:
    """CA-011: RF-027, RN-012, AGENTS.md §7.2 (câmera incerta não decide)."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendar(admin, ids, "ABC1D23")
    pesagem_id = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    liberar_balanca(admin, pesagem_id)
    posicao(admin, "INCONCLUSIVA")
    ciclos(admin, "posicao")
    assert situacao(admin, pesagem_id) == "ENTRADA_LIBERADA"
    estado = admin.get("/api/dispositivos").json()["dispositivos"]["posicao"]
    assert estado["resultado"] == "INCONCLUSIVA"
    assert (
        cancelas(admin)["ENTRADA"]["estado"] == "ABERTA"
    )  # continua aberta, sem fechar
    relogio.avancar(61)
    ciclos(admin, "posicao")
    parada = pesagem(admin, pesagem_id)
    assert (parada["situacao"], parada["motivo_intervencao"]) == (
        "AGUARDANDO_INTERVENCAO",
        "TEMPO_ESGOTADO",
    )
    operador = usuario(admin, banco, "OPERADOR")
    assert acao(operador, pesagem_id, "confirmar-posicao").status_code == 403
    confirmada = acao(admin, pesagem_id, "confirmar-posicao", "vi o caminhão no pátio")
    assert confirmada.status_code == 200
    ciclos(admin)
    final = pesagem(admin, pesagem_id)
    assert (final["situacao"], final["liberacao_manual"]) == (
        "POSICIONADA_INICIAL",
        True,
    )
    manual = [
        e for e in eventos(admin, pesagem_id) if e["motivo"] == "vi o caminhão no pátio"
    ]
    assert manual[0]["responsavel"]["nome"] == "Chefe"


def test_acao_com_versao_velha_e_transicao_rejeitada(admin: TestClient) -> None:
    """CA-012: spec 009 §6.3, RN-010, AGENTS.md §7.2 (concorrência e transição inválida)."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendar(admin, ids, "ABC1D23")
    pesagem_id = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    vista = pesagem(admin, pesagem_id)
    liberar_balanca(admin, pesagem_id)  # a pesagem muda depois de a tela ver
    velha = admin.post(
        f"/api/pesagens/{pesagem_id}/cancelar",
        json={"versao": vista["versao"], "motivo": "teste"},
    )
    assert velha.status_code == 409
    assert velha.json()["erro"]["campos"] == [
        {"campo": "versao", "codigo": "VERSAO_DESATUALIZADA"}
    ]
    assert situacao(admin, pesagem_id) == "ENTRADA_LIBERADA"
    rejeitada = acao(admin, pesagem_id, "aceitar-peso-final")
    assert rejeitada.status_code == 409
    assert rejeitada.json()["erro"]["campos"] == [
        {"campo": "situacao", "codigo": "TRANSICAO_REJEITADA"}
    ]
    registros = [e["tipo"] for e in eventos(admin, pesagem_id)]
    assert registros.count("TRANSICAO_REJEITADA") == 1
    assert situacao(admin, pesagem_id) == "ENTRADA_LIBERADA"


def test_liquido_negativo_vai_ao_administrador(
    banco: Engine, admin: TestClient, relogio: Relogio
) -> None:
    """CA-013 (cenário 7): RN-006, RN-016, spec 006 §6.1, spec 010 CA-010."""
    ids = cadastrar_pela_api(admin, ("ABC1D23", "DEF5678"))
    agendar(admin, ids, "ABC1D23")
    pesagem_id = ida(admin, relogio, "ABC1D23", "30000")
    volta(admin, "ABC1D23", pesagem_id)
    pesar(admin, relogio, pesagem_id, "20000", "AGUARDANDO_INTERVENCAO")
    parada = pesagem(admin, pesagem_id)
    assert (parada["motivo_intervencao"], parada["peso_liquido_kg"]) == (
        "LIQUIDO_NEGATIVO",
        "-10000.000",
    )
    assert parada["classificacao"] == "NEGATIVO_FORA_TOLERANCIA"
    assert cancelas(admin)["SAIDA"]["estado"] == "FECHADA"  # a saída não abre
    operador = usuario(admin, banco, "OPERADOR")
    assert acao(operador, pesagem_id, "aceitar-peso-final").status_code == 403
    # Nova pesagem final: o peso descartado fica só na auditoria.
    assert acao(operador, pesagem_id, "tentar-novamente").status_code == 200
    nova = pesagem(admin, pesagem_id)
    assert (nova["situacao"], nova["peso_final_kg"], nova["peso_liquido_kg"]) == (
        "POSICIONADA_FINAL",
        None,
        None,
    )
    descartado = [
        e
        for e in eventos(admin, pesagem_id)
        if e["evento"] == "PESO_ACEITO" and e["peso_liquido_kg"] == "-10000.000"
    ]
    assert len(descartado) == 1 and descartado[0]["peso_kg"] == "20000.000"
    pesar(admin, relogio, pesagem_id, "45000", "SAIDA_LIBERADA")
    sair_da_balanca(admin, pesagem_id, "FINALIZADA")
    assert pesagem(admin, pesagem_id)["peso_liquido_kg"] == "15000.000"
    # Segundo caminhão: o administrador aceita o líquido negativo (RN-016).
    agendar(admin, ids, "DEF5678")
    segundo = ida(admin, relogio, "DEF5678", "30000")
    volta(admin, "DEF5678", segundo)
    pesar(admin, relogio, segundo, "20000", "AGUARDANDO_INTERVENCAO")
    aceita = acao(admin, segundo, "aceitar-peso-final", "balança conferida à mão")
    assert aceita.status_code == 200
    ciclos(admin)
    sair_da_balanca(admin, segundo, "FINALIZADA")
    final = pesagem(admin, segundo)
    assert (final["classificacao"], final["liberacao_manual"]) == (
        "NEGATIVO_FORA_TOLERANCIA",
        True,
    )
    assert final["peso_liquido_kg"] == "-10000.000"


def test_balanca_atende_um_caminhao_por_vez(
    admin: TestClient, relogio: Relogio
) -> None:
    """CA-014: RN-008, RN-019, spec 015 CA-009 (reserva e ordem de chegada)."""
    ids = cadastrar_pela_api(admin, ("ABC1D23", "DEF5678"))
    agendar(admin, ids, "ABC1D23")
    agendar(admin, ids, "DEF5678")
    primeiro = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    segundo = int(chegada(admin, ("DEF5678", "0.950"))["pesagem_id"])
    fila = admin.get("/api/operacao/estado").json()["pesagens_abertas"]
    assert [p["id"] for p in fila] == [primeiro, segundo]  # ordem de chegada
    liberar_balanca(admin, primeiro)
    ciclos(admin, "posicao", "fila", "fila")
    assert situacao(admin, segundo) == "AGUARDANDO_BALANCA_INICIAL"
    posicionar(admin, primeiro, "POSICIONADA_INICIAL")
    pesar(admin, relogio, primeiro, "15000", "SAIDA_INICIAL_LIBERADA")
    posicao(admin, "CONFIRMADA")  # o primeiro ainda está na balança
    ciclos(admin, "posicao", "fila")
    assert situacao(admin, segundo) == "AGUARDANDO_BALANCA_INICIAL"
    sair_da_balanca(admin, primeiro, "EM_CARGA_DESCARGA")
    ciclos(admin, "posicao", "fila")  # balança livre: agora o segundo
    assert situacao(admin, segundo) == "ENTRADA_LIBERADA"


def test_cancelar_na_balanca_e_liberar_o_caminhao(
    banco: Engine, admin: TestClient
) -> None:
    """CA-015: RN-009, RN-020, spec 009 §6.6, spec 006 §6.4."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendamento = agendar(admin, ids, "ABC1D23")
    pesagem_id = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    liberar_balanca(admin, pesagem_id)
    posicionar(admin, pesagem_id, "POSICIONADA_INICIAL")
    cancelada = acao(admin, pesagem_id, "cancelar", "motorista desistiu")
    assert cancelada.status_code == 200
    assert cancelada.json()["aguarda_liberacao_balanca"] is True
    assert (
        admin.get(f"/api/agendamentos/{agendamento['id']}").json()["status"]
        == "AGENDADO"
    )
    pendencia = admin.get("/api/operacao/estado").json()["liberacoes_caminhao"]
    assert [(p["pesagem_id"], p["etapa"]) for p in pendencia] == [
        (pesagem_id, "PENDENTE")
    ]
    operador = usuario(admin, banco, "OPERADOR")
    pedido = operador.post(
        f"/api/pesagens/{pesagem_id}/liberar-caminhao", json={"motivo": "liberar saída"}
    )
    assert pedido.status_code == 200
    ciclos(admin)
    assert cancelas(admin)["SAIDA"]["estado"] == "ABERTA"
    posicao(admin, "AUSENTE")  # o caminhão saiu da balança
    ciclos(admin, "posicao")
    assert admin.get("/api/operacao/estado").json()["liberacoes_caminhao"] == []
    assert cancelas(admin)["SAIDA"]["estado"] == "FECHADA"
    historico = todos(admin, "/api/pesagens", agendamento_id=agendamento["id"])
    assert [p["situacao"] for p in historico] == [
        "CANCELADA"
    ]  # fica no histórico (RN-009)


def test_mesma_placa_volta_depois_do_cancelamento(admin: TestClient) -> None:
    """CA-017: RN-009, spec 006 §6.2 (CANCELADA devolve o agendamento a AGENDADO)."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendamento = agendar(admin, ids, "ABC1D23")
    primeira = int(chegada(admin, ("ABC1D23", "0.950"))["pesagem_id"])
    assert acao(admin, primeira, "cancelar", "desistiu").status_code == 200
    nova = chegada(admin, ("ABC1D23", "0.950"))
    assert (nova["decisao"], nova["agendamento_id"]) == (
        "AUTORIZADA",
        agendamento["id"],
    )
    assert nova["pesagem_id"] not in (None, primeira)
    historico = todos(admin, "/api/pesagens", agendamento_id=agendamento["id"])
    assert sorted(p["situacao"] for p in historico) == [
        "AGUARDANDO_BALANCA_INICIAL",
        "CANCELADA",
    ]


def test_placa_nao_reconhecida_na_volta(
    banco: Engine, admin: TestClient, relogio: Relogio
) -> None:
    """CA-016: RN-018, spec 009 §6.7, AGENTS.md §7.2 (volta não autorizada por inferência)."""
    ids = cadastrar_pela_api(admin, ("ABC1D23", "DEF5678"))
    agendar(admin, ids, "ABC1D23")
    pesagem_id = ida(admin, relogio, "ABC1D23", "15000")
    ruim = chegada(admin, ("ABC1D23", "0.500"))
    assert (ruim["decisao"], ruim["motivo"]) == ("NAO_AUTORIZADA", "CONFIANCA_BAIXA")
    outra = chegada(admin, ("DEF5678", "0.950"))  # cadastrada, sem agendamento
    assert outra["motivo"] == "SEM_AGENDAMENTO"
    ciclos(admin, "posicao", "fila")
    assert situacao(admin, pesagem_id) == "EM_CARGA_DESCARGA"
    operador = usuario(admin, banco, "OPERADOR")
    assert acao(operador, pesagem_id, "liberar-retorno").status_code == 403
    volta_liberada_pelo_administrador(admin, pesagem_id)
    pesar(admin, relogio, pesagem_id, "45000", "SAIDA_LIBERADA")
    sair_da_balanca(admin, pesagem_id, "FINALIZADA")
    final = pesagem(admin, pesagem_id)
    assert (final["liberacao_manual"], final["peso_liquido_kg"]) == (True, "30000.000")
