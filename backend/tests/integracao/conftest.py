"""PostgreSQL real em contêiner para os testes de persistência (ADR-0006; AGENTS.md §8).

Sem Docker, os testes falham com mensagem clara: não são pulados.
"""

import subprocess
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import OperationalError

from pesagem.api.senha import gerar_hash_senha
from pesagem.config import (
    Configuracao,
    ConfiguracaoBanco,
    ConfiguracaoOperacao,
    ConfiguracaoSeguranca,
)
from pesagem.dominio.placa.normalizacao import PlacaNormalizada, normalizar_placa
from pesagem.main import criar_aplicacao
from pesagem.persistencia.banco import Transacao, criar_engine, transacao
from pesagem.persistencia.repositorios.pesagem import OperacaoRegistrada

IMAGEM = "postgres:18.6-alpine"  # mesma da execução (ADR-0006 §3.1)
PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
SENHA = "teste-local"


def configuracao_alembic(conexao: Connection) -> Config:
    configuracao = Config(toml_file=str(PYPROJECT))
    configuracao.attributes["connection"] = conexao
    return configuracao


@pytest.fixture(scope="session")
def configuracao_banco() -> Iterator[ConfiguracaoBanco]:
    try:
        conteiner = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "-e",
                f"POSTGRES_PASSWORD={SENHA}",
                "-p",
                "127.0.0.1::5432",
                IMAGEM,
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as erro:
        pytest.fail(f"Docker indisponível para os testes de persistência: {erro}")
    try:
        porta = (
            subprocess.run(
                ["docker", "port", conteiner, "5432/tcp"],
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.split(":")[-1]
            .strip()
        )
        yield ConfiguracaoBanco("127.0.0.1", int(porta), "postgres", "postgres", SENHA)
    finally:
        subprocess.run(["docker", "stop", conteiner], capture_output=True)


@pytest.fixture(scope="session")
def engine(configuracao_banco: ConfiguracaoBanco) -> Engine:
    engine = criar_engine(configuracao_banco)
    limite = time.monotonic() + 60
    while True:
        try:
            with engine.connect() as conexao:
                conexao.execute(text("SELECT 1"))
            break
        except OperationalError:  # o servidor ainda está subindo; o laço tem limite
            if time.monotonic() > limite:
                raise
            time.sleep(0.5)
    with engine.begin() as conexao:
        command.upgrade(configuracao_alembic(conexao), "head")
    return engine


@pytest.fixture
def banco(engine: Engine) -> Engine:
    """Banco migrado, com as tabelas de dados vazias antes de cada teste."""
    with engine.begin() as conexao:
        tabelas = conexao.execute(
            text(
                "SELECT string_agg(tablename, ', ') FROM pg_tables WHERE schemaname = "
                "'public' AND tablename NOT IN ('alembic_version', 'perfil', "
                # O ponto de controle único vem da migração 0004, com os equipamentos.
                "'perfil_permissao', 'balanca', 'cancela', 'ponto_controle')"
            )
        ).scalar_one()
        conexao.execute(text(f"TRUNCATE {tabelas} RESTART IDENTITY CASCADE"))
    return engine


def esperar_bloqueio(engine: Engine) -> None:
    """Espera outra sessão ficar parada num bloqueio de linha (corridas dos CA)."""
    limite = time.monotonic() + 10
    while time.monotonic() < limite:
        with engine.connect() as conexao:
            esperando = conexao.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'"
                )
            ).scalar_one()
        if esperando:
            return
        time.sleep(0.05)
    raise AssertionError("a outra transação não chegou a esperar o bloqueio")


def cadastrar(
    conexao: Connection, placas: tuple[str, ...] = ("ABC1234",)
) -> dict[str, int]:
    """Cadastro mínimo: usuário, um ponto com balança e cancelas, veículos e uma faixa."""

    def inserir(sql: str) -> int:
        return int(conexao.execute(text(sql + " RETURNING id")).scalar_one())

    ids = {
        "usuario": inserir(
            "INSERT INTO usuario (nome, login, senha_hash, perfil_id) SELECT "
            "'Admin', 'admin', 'x', id FROM perfil WHERE codigo = 'ADMINISTRADOR'"
        ),
        "transportadora": inserir(
            "INSERT INTO transportadora (razao_social, cnpj) VALUES ('T', '11222333000181')"
        ),
        "motorista": inserir(
            "INSERT INTO motorista (nome, cpf) VALUES ('M', '52998224725')"
        ),
        "tipo_veiculo": inserir(
            "INSERT INTO tipo_veiculo (descricao) VALUES ('Truck')"
        ),
        "produto": inserir(
            "INSERT INTO produto (codigo, descricao) VALUES ('P1', 'Soja')"
        ),
        "faixa": inserir(
            "INSERT INTO faixa_horario (hora_inicio, hora_fim, capacidade) "
            "VALUES ('08:00', '10:00', 5)"
        ),
    }
    ponto = conexao.execute(
        text(
            "SELECT id, balanca_id, cancela_entrada_id, cancela_saida_id FROM ponto_controle"
        )
    ).one()
    ids.update(ponto=ponto[0], balanca=ponto[1], entrada=ponto[2], saida=ponto[3])
    for indice, placa in enumerate(placas):
        ids[f"veiculo{indice}"] = inserir(
            "INSERT INTO veiculo (placa, chave_comparacao, tipo_veiculo_id) "
            f"VALUES ('{placa}', '{chave(placa)}', {ids['tipo_veiculo']})"
        )
    return ids


# --- API (specs 007 a 013) ---

ORIGEM = "https://pesagem.teste"
INICIO = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)  # 09:00 em America/Sao_Paulo


class Relogio:
    """Relógio controlado pelos testes (tempo sem uso, bloqueio, "hoje")."""

    def __init__(self) -> None:
        self.agora = INICIO

    def __call__(self) -> datetime:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += timedelta(seconds=segundos)


def configuracao_api(configuracao_banco: ConfiguracaoBanco) -> Configuracao:
    return Configuracao(
        banco=configuracao_banco,
        seguranca=ConfiguracaoSeguranca(
            origens_permitidas=frozenset({ORIGEM}),
            sessao_tempo_sem_uso_s=600,
            login_tentativas_maximas=3,
            login_bloqueio_s=300,
        ),
        patio_fuso=ZoneInfo("America/Sao_Paulo"),
        tamanho_pagina_padrao=2,
        tamanho_pagina_maximo=5,
        operacao=ConfiguracaoOperacao(
            modo_balanca="",
            modo_cancelas="",
            modo_cameras="",
            peso_minimo_kg=Decimal("100"),
            peso_maximo_kg=Decimal("80000"),
            quantidade_leituras_estaveis=3,
            variacao_maxima_kg=Decimal("10"),
            janela_estabilidade_ms=3000,
            tolerancia_movimentacao_kg=Decimal("20"),
            limiar_confianca=Decimal("0.800"),
            intervalo_analise_ms=1000,
            idade_maxima_imagem_ms=2000,
            intervalo_leitura_balanca_ms=500,
            tempo_limite_posicionamento_ms=60000,
            tempo_limite_pesagem_ms=60000,
            tempo_limite_saida_balanca_ms=60000,
            heartbeat_ms=100,
            limite_sem_heartbeat_ms=300,
            intervalo_peso_ms=1000,
            intervalo_imagem_ms=2000,
        ),
    )


@pytest.fixture
def relogio() -> Relogio:
    return Relogio()


@pytest.fixture
def cliente(
    banco: Engine, configuracao_banco: ConfiguracaoBanco, relogio: Relogio
) -> Iterator[TestClient]:
    """HTTPS, porque o cookie é `Secure` (spec 012 §8); `Origin` permitido por padrão."""
    # Sem os ciclos de câmera e balança: o resultado não depende do tempo.
    app = criar_aplicacao(
        configuracao_api(configuracao_banco), banco, relogio, executar_ciclos=False
    )
    with TestClient(
        app,
        base_url="https://pesagem.teste",
        headers={"Origin": ORIGEM},
        raise_server_exceptions=False,
    ) as cliente:
        yield cliente


def criar_usuario(
    banco: Engine, login: str, perfil: str, senha: str = "senha-certa"
) -> int:
    with transacao(banco) as t:
        usuario_id = t.usuarios.criar_usuario(
            login.title(), login, gerar_hash_senha(senha), perfil
        )
    assert usuario_id is not None
    return usuario_id


def entrar(cliente: TestClient, login: str, senha: str = "senha-certa") -> None:
    resposta = cliente.post("/api/sessoes", json={"login": login, "senha": senha})
    assert resposta.status_code == 201, resposta.text


def chave(placa: str) -> str:
    """Chave de comparação da spec 003 (ABC1234 e ABC1C34 têm a mesma)."""
    normalizada = normalizar_placa(placa)
    assert isinstance(normalizada, PlacaNormalizada)
    return normalizada.chave_comparacao


# Variáveis da operação (specs 002, 004, 005, 009, 011, 015 §5.6) para os testes de partida.
AMBIENTE_OPERACAO = {
    "PESAGEM_BALANCA_PESO_MINIMO_KG": "100",
    "PESAGEM_BALANCA_PESO_MAXIMO_KG": "80000",
    "PESAGEM_BALANCA_QUANTIDADE_LEITURAS_ESTAVEIS": "3",
    "PESAGEM_BALANCA_VARIACAO_MAXIMA_KG": "10",
    "PESAGEM_BALANCA_JANELA_ESTABILIDADE_MS": "3000",
    "PESAGEM_LPR_LIMIAR_CONFIANCA": "0.800",
    "PESAGEM_CAMERA_INTERVALO_ANALISE_MS": "1000",
    "PESAGEM_CAMERA_IDADE_MAXIMA_IMAGEM_MS": "2000",
    "PESAGEM_BALANCA_INTERVALO_LEITURA_MS": "500",
    "PESAGEM_OPERACAO_TEMPO_LIMITE_POSICIONAMENTO_MS": "60000",
    "PESAGEM_OPERACAO_TEMPO_LIMITE_PESAGEM_MS": "60000",
    "PESAGEM_OPERACAO_TEMPO_LIMITE_SAIDA_BALANCA_MS": "60000",
    "PESAGEM_TEMPO_REAL_HEARTBEAT_MS": "5000",
    "PESAGEM_TEMPO_REAL_LIMITE_SEM_HEARTBEAT_MS": "15000",
    "PESAGEM_TEMPO_REAL_INTERVALO_PESO_MS": "1000",
    "PESAGEM_TEMPO_REAL_INTERVALO_IMAGEM_MS": "2000",
}


def criar_operacao(
    t: Transacao, agendamento_id: int, *args: Any, **kwargs: Any
) -> OperacaoRegistrada:
    """`criar_operacao` com o veículo do próprio agendamento, como a decisão faria."""
    veiculo_id = t.conexao.execute(
        text("SELECT veiculo_id FROM agendamento WHERE id = :id"),
        {"id": agendamento_id},
    ).scalar_one()
    return t.pesagens.criar_operacao(
        agendamento_id, *args, veiculo_id=veiculo_id, **kwargs
    )
