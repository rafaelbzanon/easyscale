"""Fluxo completo pela API, com PostgreSQL real e simuladores (spec 028, CA-001 a CA-004).

Cenários 1, 4, 6 e 7 do artigo (`specs/requisitos.md` §4): placa com agendamento, leitura
de peso, acionamento das cancelas e finalização com o peso líquido.
"""

import json
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from ponta_a_ponta.apoio import (
    HOJE,
    Relogio,
    acao,
    agendar,
    cadastrar_pela_api,
    cancelas,
    ida,
    pesagem,
    pesar,
    sair_da_balanca,
    situacao,
    todos,
    usuario,
    volta,
)

COMANDOS_DO_FLUXO = [  # spec 006: oito comandos, na ordem
    ("ENTRADA", "ABRIR"),
    ("ENTRADA", "FECHAR"),
    ("SAIDA", "ABRIR"),
    ("SAIDA", "FECHAR"),
    ("ENTRADA", "ABRIR"),
    ("ENTRADA", "FECHAR"),
    ("SAIDA", "ABRIR"),
    ("SAIDA", "FECHAR"),
]


def comandos(cliente: TestClient, pesagem_id: int) -> list[tuple[str, str]]:
    eventos = todos(cliente, f"/api/pesagens/{pesagem_id}/eventos")
    return [
        (e["cancela"], e["comando"]) for e in eventos if e["tipo"] == "COMANDO_CANCELA"
    ]


def fluxo(
    admin: TestClient,
    relogio: Relogio,
    tipo: str,
    inicial: str,
    final: str,
) -> tuple[int, dict[str, Any]]:
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendamento = agendar(admin, ids, "ABC1D23", tipo)
    assert (agendamento["origem"], agendamento["status"]) == ("USUARIO", "AGENDADO")
    pesagem_id = ida(admin, relogio, "ABC1D23", inicial)
    em_carga = pesagem(admin, pesagem_id)
    assert em_carga["agendamento_status"] == "EM_ANDAMENTO"
    assert (em_carga["peso_inicial_kg"], em_carga["peso_final_kg"]) == (
        f"{inicial}.000" if "." not in inicial else inicial,
        None,
    )
    volta(admin, "ABC1D23", pesagem_id)
    pesar(admin, relogio, pesagem_id, final, "SAIDA_LIBERADA")
    sair_da_balanca(admin, pesagem_id, "FINALIZADA")
    return agendamento["id"], pesagem(admin, pesagem_id)


def test_carga_do_login_a_finalizada(admin: TestClient, relogio: Relogio) -> None:
    """CA-001: RF-001 a RF-004, RF-006 a RF-011, RF-013 a RF-018, RN-002, RN-006, RN-012."""
    agendamento_id, final = fluxo(admin, relogio, "CARGA", "15000", "45000")
    assert final["situacao"] == "FINALIZADA"
    assert (final["peso_inicial_kg"], final["peso_final_kg"]) == (
        "15000.000",
        "45000.000",
    )
    assert (final["peso_liquido_kg"], final["classificacao"]) == (
        "30000.000",  # CARGA: final - inicial (RN-006)
        "COM_MOVIMENTACAO",
    )
    assert final["acoes_disponiveis"] == [] and final["comando_pendente"] is None
    assert (
        admin.get(f"/api/agendamentos/{agendamento_id}").json()["status"] == "CONCLUIDO"
    )
    # Cancelas: fechadas no fim, com o último comando confirmado.
    estado = cancelas(admin)
    assert {c["estado"] for c in estado.values()} == {"FECHADA"}
    assert estado["SAIDA"]["ultimo_comando"]["resultado"] == "CONFIRMADO"
    # Histórico (spec 010) e auditoria (RF-018, RF-019, RNF-010).
    lista = admin.get("/api/pesagens", params={"placa": "abc-1d23"}).json()
    assert [item["id"] for item in lista["itens"]] == [final["id"]]
    assert comandos(admin, final["id"]) == COMANDOS_DO_FLUXO
    eventos = todos(admin, f"/api/pesagens/{final['id']}/eventos")
    assert [e["evento"] for e in eventos if e["evento"] == "PESO_ACEITO"] == [
        "PESO_ACEITO",
        "PESO_ACEITO",
    ]
    assert (
        eventos[0]["evento"] == "CRIACAO" and eventos[0]["leitura_placa_id"] is not None
    )
    assert eventos[-1]["situacao_destino"] == "FINALIZADA"
    assert [e["ocorrido_em"] for e in eventos] == sorted(
        e["ocorrido_em"] for e in eventos
    )
    assert all(e["responsavel"] is None for e in eventos)  # tudo automático
    assert "ABC1D23" not in str(eventos) and "cpf" not in str(eventos).lower()
    # Reconhecimentos: a entrada e a volta (RF-022).
    leituras = todos(admin, "/api/leituras-placa")
    assert [item["decisao"] for item in reversed(leituras)] == [
        "AUTORIZADA",
        "RETORNO_ACEITO",
    ]
    assert {item["pesagem_id"] for item in leituras} == {final["id"]}


def test_descarga_calcula_inicial_menos_final(
    admin: TestClient, relogio: Relogio
) -> None:
    """CA-002: RN-006 (DESCARGA: inicial - final)."""
    _, final = fluxo(admin, relogio, "DESCARGA", "40000", "15000")
    assert (final["peso_liquido_kg"], final["classificacao"]) == (
        "25000.000",
        "COM_MOVIMENTACAO",
    )


def test_sem_movimentacao_guarda_o_liquido_real(
    admin: TestClient, relogio: Relogio
) -> None:
    """CA-003: RN-006, RN-004 (12 kg de diferença ficam como lidos, nunca zero)."""
    _, final = fluxo(admin, relogio, "CARGA", "15000", "15012")
    assert (final["situacao"], final["classificacao"]) == (
        "FINALIZADA",
        "SEM_MOVIMENTACAO",
    )
    assert final["peso_liquido_kg"] == "12.000"


def test_perfis_no_historico(
    banco: Engine, admin: TestClient, relogio: Relogio
) -> None:
    """CA-004: ADR-0004 §4.3; o AUDITOR só consulta, o OPERADOR não aceita peso."""
    _, final = fluxo(admin, relogio, "CARGA", "15000", "45000")
    auditor = usuario(admin, banco, "AUDITOR")
    operador = usuario(admin, banco, "OPERADOR")
    for cliente in (auditor, operador):
        assert cliente.get(f"/api/pesagens/{final['id']}").json() == final
        assert cliente.get(f"/api/pesagens/{final['id']}/eventos").status_code == 200
    assert acao(auditor, final["id"], "cancelar").status_code == 403
    assert acao(operador, final["id"], "cancelar").status_code == 403
    assert HOJE in admin.get("/api/agendamentos").text
    assert situacao(admin, final["id"]) == "FINALIZADA"


def test_eventos_em_tempo_real_acompanham_o_fluxo(
    admin: TestClient, relogio: Relogio
) -> None:
    """CA-005: RF-021, spec 009 CA-007 (um evento `pesagem` por transição), CA-026."""
    ids = cadastrar_pela_api(admin, ("ABC1D23",))
    agendar(admin, ids, "ABC1D23")
    with admin.stream("GET", "/api/operacao/eventos") as canal:
        assert canal.headers["content-type"].startswith("text/event-stream")
        pesagem_id = ida(admin, relogio, "ABC1D23", "15000")
        transicoes = [
            e
            for e in todos(admin, f"/api/pesagens/{pesagem_id}/eventos")
            if e["tipo"] == "TRANSICAO"
        ]
        recebidos: list[dict[str, Any]] = []
        tipos: set[str] = set()
        nome = ""
        for linha in canal.iter_lines():
            if linha.startswith("event: "):
                nome = linha.removeprefix("event: ")
                tipos.add(nome)
            elif linha.startswith("data: ") and nome == "pesagem":
                recebidos.append(json.loads(linha.removeprefix("data: ")))
                if len(recebidos) == len(transicoes):
                    break
    # O canal monta o objeto com o estado de quando é lido; o que vale aqui é a
    # contagem (uma por transição) e que nada traz CPF nem imagem (CA-026).
    assert {p["id"] for p in recebidos} == {pesagem_id}
    assert recebidos[-1]["versao"] == pesagem(admin, pesagem_id)["versao"]
    assert {"pesagem", "leitura_placa", "cancela", "posicao", "balanca"} <= tipos
    assert "cpf" not in json.dumps(recebidos).lower()
