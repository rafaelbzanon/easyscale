"""Configuração do banco (spec 014, CA-016) e da balança serial (spec 029)."""

import pytest

from pesagem.config import ErroConfiguracao, _serial_balanca, ler_configuracao_banco
from pesagem.dispositivos.balanca.serial import ParametrosSerial

COMPLETA = {
    "PESAGEM_BANCO_HOST": "db",
    "PESAGEM_BANCO_PORTA": "5432",
    "PESAGEM_BANCO_NOME": "pesagem",
    "PESAGEM_BANCO_USUARIO": "pesagem",
    "PESAGEM_BANCO_SENHA": "segredo-de-teste",
}


def test_le_a_configuracao_completa() -> None:
    configuracao = ler_configuracao_banco(COMPLETA)
    assert (configuracao.host, configuracao.porta) == ("db", 5432)
    assert "segredo-de-teste" not in repr(configuracao)


@pytest.mark.parametrize("variavel", sorted(COMPLETA))
def test_falha_sem_variavel_obrigatoria(variavel: str) -> None:
    ambiente = {**COMPLETA, variavel: " "}
    with pytest.raises(ErroConfiguracao, match=variavel):
        ler_configuracao_banco(ambiente)


@pytest.mark.parametrize("porta", ["0", "65536", "abc", "-1"])
def test_falha_com_porta_invalida_sem_mostrar_o_valor(porta: str) -> None:
    with pytest.raises(ErroConfiguracao, match="PESAGEM_BANCO_PORTA") as erro:
        ler_configuracao_banco({**COMPLETA, "PESAGEM_BANCO_PORTA": porta})
    assert porta not in str(erro.value)


# Spec 029 §6.3: parâmetros seriais da balança, só em REAL.
SERIAL_REAL = {
    "PESAGEM_BALANCA_MODO": "REAL",
    "PESAGEM_BALANCA_PORTA": "/dev/pesagem-teste",
    "PESAGEM_BALANCA_BAUD_RATE": "9600",
    "PESAGEM_BALANCA_PARIDADE": "E",
    "PESAGEM_BALANCA_DATA_BITS": "7",
    "PESAGEM_BALANCA_STOP_BITS": "1.5",
    "PESAGEM_BALANCA_TIMEOUT_MS": "500",
    "PESAGEM_BALANCA_INTERVALO_TENTATIVA_MS": "200",
}


def test_le_parametros_seriais_em_real() -> None:
    """Spec 029 CA-010."""
    assert _serial_balanca(SERIAL_REAL) == ParametrosSerial(
        "/dev/pesagem-teste", 9600, "E", 7, 1.5, 500, 200
    )


@pytest.mark.parametrize("modo", [None, "", "SIMULADO", "real"])
def test_fora_de_real_nao_le_parametros_seriais(modo: str | None) -> None:
    """Spec 029 CA-010: em SIMULADO nenhum parâmetro serial é exigido."""
    ambiente = {} if modo is None else {"PESAGEM_BALANCA_MODO": modo}
    assert _serial_balanca(ambiente) is None


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [
        *((v, " ") for v in sorted(SERIAL_REAL) if v != "PESAGEM_BALANCA_MODO"),
        ("PESAGEM_BALANCA_BAUD_RATE", "9601"),
        ("PESAGEM_BALANCA_PARIDADE", "n"),
        ("PESAGEM_BALANCA_PARIDADE", "NONE"),
        ("PESAGEM_BALANCA_DATA_BITS", "9"),
        ("PESAGEM_BALANCA_STOP_BITS", "1.0"),
        ("PESAGEM_BALANCA_TIMEOUT_MS", "0"),
        ("PESAGEM_BALANCA_INTERVALO_TENTATIVA_MS", "-1"),
    ],
)
def test_parametro_serial_invalido_impede_a_partida(variavel: str, valor: str) -> None:
    """Spec 029 CA-010: cita o nome da variável."""
    with pytest.raises(ErroConfiguracao, match=variavel):
        _serial_balanca({**SERIAL_REAL, variavel: valor})
