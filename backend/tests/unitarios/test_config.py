"""Configuração do banco (spec 014, CA-016)."""

import pytest

from pesagem.config import ErroConfiguracao, ler_configuracao_banco

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
