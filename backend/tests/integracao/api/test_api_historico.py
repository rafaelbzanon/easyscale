"""API de histórico contra o banco real (spec 010, CA-001 a CA-016)."""

import logging
from dataclasses import replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import pytest
from conftest import ORIGEM, cadastrar, criar_operacao, criar_usuario, entrar
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from pesagem.dominio.operacao.maquina_estados import (
    AcaoManual,
    EventoAutomatico,
    EventoOperacao,
    MotivoIntervencao,
    PesoAceito,
    SituacaoOperacao,
    TipoAcaoManual,
    TipoEvento,
)
from pesagem.dominio.pesagem.calculo_peso import ClassificacaoPesoLiquido, TipoOperacao
from pesagem.persistencia.banco import Transacao, transacao
from pesagem.persistencia.repositorios.agendamento import NovoAgendamento

S = SituacaoOperacao
HOJE = date(2026, 11, 7)
EM = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
CAMPOS_PESAGEM = {
    "id",
    "versao",
    "situacao",
    "situacao_anterior",
    "motivo_intervencao",
    "comando_pendente",
    "acoes_disponiveis",
    "ocupa_balanca",
    "aguarda_liberacao_balanca",
    "liberacao_manual",
    "agendamento_id",
    "agendamento_status",
    "tipo_operacao",
    "placa",
    "motorista_nome",
    "transportadora_razao_social",
    "produto_descricao",
    "data_prevista",
    "faixa_hora_inicio",
    "faixa_hora_fim",
    "peso_inicial_kg",
    "peso_inicial_em",
    "peso_final_kg",
    "peso_final_em",
    "peso_liquido_kg",
    "classificacao",
    "criado_em",
    "atualizado_em",
}


def operacao(
    t: Transacao, ids: dict[str, int], veiculo: str, tipo: str = "CARGA"
) -> tuple[int, int]:
    agendamento = t.agendamentos.criar_agendamento(
        NovoAgendamento(
            ids[veiculo],
            ids["motorista"],
            None,
            ids["produto"],
            tipo,
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
    return agendamento, criar_operacao(t, agendamento, ids["ponto"], EM).pesagem_id


def gravar(
    t: Transacao,
    pesagem_id: int,
    evento: EventoOperacao | None = None,
    responsavel: int | None = None,
    **campos: object,
) -> None:
    atual = t.pesagens.obter_operacao(pesagem_id).operacao
    nova = replace(atual, **campos)  # type: ignore[arg-type]
    t.pesagens.gravar_transicao(
        pesagem_id,
        atual.versao,
        nova,
        evento or EventoAutomatico(TipoEvento.BALANCA_DISPONIVEL),
        responsavel,
        HOJE,
        EM,
    )


def pesos(
    inicial: str, final: str, liquido: str, classificacao: ClassificacaoPesoLiquido
) -> dict[str, Any]:
    return {
        "peso_inicial_kg": Decimal(inicial),
        "peso_inicial_em": EM,
        "peso_final_kg": Decimal(final),
        "peso_final_em": EM,
        "peso_liquido_kg": Decimal(liquido),
        "classificacao": classificacao,
    }


@pytest.fixture
def ids(banco: Engine) -> dict[str, int]:
    with transacao(banco) as t:
        return cadastrar(t.conexao, ("ABC1C34", "DEF5678", "GHI9012", "JKL3456"))


@pytest.fixture
def auditor(banco: Engine, cliente: TestClient) -> TestClient:
    criar_usuario(banco, "auditor", "AUDITOR")
    entrar(cliente, "auditor")
    return cliente


def test_rotas_e_permissoes(
    banco: Engine, cliente: TestClient, ids: dict[str, int]
) -> None:
    """CA-001 e CA-002."""
    assert cliente.get("/api/pesagens").status_code == 401
    for perfil in ("ADMINISTRADOR", "OPERADOR", "AUDITOR"):
        outro = TestClient(
            cliente.app, base_url="https://pesagem.teste", headers={"Origin": ORIGEM}
        )
        criar_usuario(banco, perfil.lower(), perfil)
        entrar(outro, perfil.lower())
        assert outro.get("/api/pesagens").status_code == 200
    with banco.begin() as conexao:
        conexao.execute(text("INSERT INTO perfil (codigo) VALUES ('VISITANTE')"))
    criar_usuario(banco, "visitante", "VISITANTE")
    entrar(cliente, "visitante")
    assert cliente.get("/api/pesagens").status_code == 403
    with transacao(banco) as t:
        _, pesagem_id = operacao(t, ids, "veiculo0")
    entrar(cliente, "auditor")
    for metodo in ("POST", "PATCH", "DELETE"):
        assert cliente.request(metodo, "/api/pesagens", json={}).status_code == 405
        assert (
            cliente.request(
                metodo, f"/api/pesagens/{pesagem_id}/eventos", json={}
            ).status_code
            == 405
        )


def test_pesos_liquido_e_classificacao(
    banco: Engine, auditor: TestClient, ids: dict[str, int]
) -> None:
    """CA-003, CA-004, CA-005 e CA-006."""
    with transacao(banco) as t:
        _, carga = operacao(t, ids, "veiculo0")
        gravar(
            t,
            carga,
            situacao=S.FINALIZADA,
            **pesos("1000", "1500", "500", ClassificacaoPesoLiquido.COM_MOVIMENTACAO),
        )
        _, descarga = operacao(t, ids, "veiculo1", "DESCARGA")
        gravar(
            t,
            descarga,
            situacao=S.FINALIZADA,
            tipo_operacao=TipoOperacao.DESCARGA,
            **pesos("9000", "1000", "8000", ClassificacaoPesoLiquido.COM_MOVIMENTACAO),
        )
        _, sem = operacao(t, ids, "veiculo2")
        gravar(
            t,
            sem,
            situacao=S.PESO_FINAL_OK,
            **pesos("1000", "1012", "12", ClassificacaoPesoLiquido.SEM_MOVIMENTACAO),
        )
        _, parada = operacao(t, ids, "veiculo3")
        gravar(
            t,
            parada,
            situacao=S.AGUARDANDO_INTERVENCAO,
            situacao_anterior=S.EM_CARGA_DESCARGA,
            motivo_intervencao=MotivoIntervencao.REINICIO_INCONCLUSIVO,
        )
    itens = {
        p["id"]: p
        for p in auditor.get("/api/pesagens", params={"tamanho_pagina": 5}).json()[
            "itens"
        ]
    }
    assert (
        itens[carga]["peso_inicial_kg"],
        itens[carga]["peso_final_kg"],
        itens[carga]["peso_liquido_kg"],
    ) == ("1000.000", "1500.000", "500.000")
    assert itens[carga]["agendamento_status"] == "CONCLUIDO"
    assert itens[descarga]["peso_liquido_kg"] == "8000.000"
    assert (itens[sem]["peso_liquido_kg"], itens[sem]["classificacao"]) == (
        "12.000",
        "SEM_MOVIMENTACAO",
    )
    abertas = auditor.get(
        "/api/pesagens", params={"aberta": "true", "tamanho_pagina": 5}
    ).json()["itens"]
    assert {p["id"] for p in abertas} == {sem, parada}
    for item in abertas:
        assert set(item) == CAMPOS_PESAGEM
    assert itens[parada]["peso_inicial_kg"] is None
    assert (
        itens[parada]["situacao_anterior"],
        itens[parada]["motivo_intervencao"],
    ) == ("EM_CARGA_DESCARGA", "REINICIO_INCONCLUSIVO")
    assert itens[parada]["ocupa_balanca"] is False
    assert itens[sem]["ocupa_balanca"] is True
    assert set(itens[parada]["acoes_disponiveis"]) == {"TENTAR_NOVAMENTE", "CANCELAR"}
    assert itens[sem]["comando_pendente"] == {"comando": "ABRIR", "cancela": "SAIDA"}
    assert (itens[sem]["situacao_anterior"], itens[carga]["acoes_disponiveis"]) == (
        None,
        [],
    )


def test_eventos_em_ordem_com_responsavel_e_cancela(
    banco: Engine, auditor: TestClient, ids: dict[str, int]
) -> None:
    """CA-007, CA-008, CA-009, CA-010 e CA-014."""
    final = pesos(
        "1000", "900", "-100", ClassificacaoPesoLiquido.NEGATIVO_FORA_TOLERANCIA
    )
    with transacao(banco) as t:
        _, pesagem_id = operacao(t, ids, "veiculo0")
        t.pesagens.registrar_comando_cancela(
            pesagem_id, "ENTRADA", "ABRIR", "SEM_CONFIRMACAO", 2, EM
        )
        gravar(
            t,
            pesagem_id,
            PesoAceito(Decimal("900"), EM),
            situacao=S.AGUARDANDO_INTERVENCAO,
            situacao_anterior=S.POSICIONADA_FINAL,
            motivo_intervencao=MotivoIntervencao.LIQUIDO_NEGATIVO,
            **final,
        )
        gravar(
            t,
            pesagem_id,
            AcaoManual(TipoAcaoManual.TENTAR_NOVAMENTE, "admin", "pesar de novo"),
            ids["usuario"],
            situacao=S.POSICIONADA_FINAL,
            situacao_anterior=None,
            motivo_intervencao=None,
            peso_final_kg=None,
            peso_final_em=None,
            peso_liquido_kg=None,
            classificacao=None,
        )
    resposta = auditor.get(
        f"/api/pesagens/{pesagem_id}/eventos", params={"tamanho_pagina": 5}
    )
    corpo = resposta.json()
    assert (corpo["total"], corpo["pagina"]) == (4, 1)
    criacao, comando, peso, nova = corpo["itens"]
    assert [criacao["evento"], peso["evento"], nova["evento"]] == [
        "CRIACAO",
        "PESO_ACEITO",
        "TENTAR_NOVAMENTE",
    ]
    assert (
        comando["tipo"],
        comando["evento"],
        comando["cancela"],
        comando["comando"],
        comando["resultado"],
        comando["tentativas"],
    ) == ("COMANDO_CANCELA", None, "ENTRADA", "ABRIR", "SEM_CONFIRMACAO", 2)
    assert (peso["responsavel"], peso["motivo"]) == (None, None)
    assert (
        nova["responsavel"] == {"id": ids["usuario"], "nome": "Admin"}
        and nova["motivo"] == "pesar de novo"
    )
    assert (nova["peso_kg"], nova["peso_liquido_kg"]) == ("900.000", "-100.000")
    atual = auditor.get("/api/pesagens").json()["itens"][0]
    assert (atual["peso_final_kg"], atual["peso_liquido_kg"]) == (None, None)
    for texto in (resposta.text, auditor.get("/api/pesagens").text):
        assert "cpf" not in texto
    assert "ABC1C34" not in resposta.text
    assert auditor.get("/api/pesagens/999/eventos").status_code == 404


def test_filtros_placa_data_e_agendamento(
    banco: Engine, auditor: TestClient, ids: dict[str, int]
) -> None:
    """CA-011, CA-012, CA-013 e CA-015."""
    with transacao(banco) as t:
        agendamento, primeira = operacao(t, ids, "veiculo0")
        gravar(t, primeira, situacao=S.CANCELADA)
        segunda = criar_operacao(t, agendamento, ids["ponto"], EM).pesagem_id
        _, outra = operacao(t, ids, "veiculo1")
        # 2026-11-08 02:30 UTC = 23:30 do dia 7 no pátio.
        t.conexao.execute(
            text("UPDATE pesagem SET criado_em = '2026-11-08 02:30+00' WHERE id = :id"),
            {"id": outra},
        )
    por_placa = auditor.get("/api/pesagens", params={"placa": "ABC1234"}).json()
    assert {p["id"] for p in por_placa["itens"]} == {primeira, segunda}
    assert auditor.get("/api/pesagens", params={"placa": "ABCO123"}).json()["erro"][
        "campos"
    ] == [{"campo": "placa", "codigo": "PLACA_INVALIDA"}]
    dia = auditor.get(
        "/api/pesagens",
        params={
            "data_inicio": "2026-11-07",
            "data_fim": "2026-11-07",
            "tamanho_pagina": 5,
        },
    ).json()
    assert outra in [p["id"] for p in dia["itens"]]
    assert (
        auditor.get("/api/pesagens", params={"data_inicio": "2026-11-08"}).json()[
            "total"
        ]
        == 0
    )
    assert (
        auditor.get(
            "/api/pesagens",
            params={"data_inicio": "2026-11-08", "data_fim": "2026-11-07"},
        ).status_code
        == 422
    )
    mesmo = auditor.get("/api/pesagens", params={"agendamento_id": agendamento}).json()
    assert [p["id"] for p in mesmo["itens"]] == [
        segunda,
        primeira,
    ]  # mais recente primeiro
    assert set(mesmo) == {"itens", "total", "pagina", "tamanho_pagina"}
    for invalido in (
        {"situacao": "QUALQUER"},
        {"aberta": "sim"},
        {"agendamento_id": "x"},
    ):
        assert auditor.get("/api/pesagens", params=invalido).status_code == 422


def test_logs_sem_query_nem_motivo(
    banco: Engine,
    auditor: TestClient,
    ids: dict[str, int],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CA-016."""
    with transacao(banco) as t:
        _, pesagem_id = operacao(t, ids, "veiculo0")
        gravar(
            t,
            pesagem_id,
            AcaoManual(TipoAcaoManual.CANCELAR, "admin", "MOTIVO-SEGREDO"),
            ids["usuario"],
            situacao=S.CANCELADA,
        )
    with caplog.at_level(logging.INFO):
        auditor.get("/api/pesagens", params={"placa": "ABC1C34"})
        auditor.get(f"/api/pesagens/{pesagem_id}/eventos")
    texto = "\n".join(r.getMessage() for r in caplog.records if r.name != "httpx")
    assert "ABC1C34" not in texto and "MOTIVO-SEGREDO" not in texto
