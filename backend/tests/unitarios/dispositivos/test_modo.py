"""Testes da escolha de modo e de implementação (spec 004 §5.3, §6.4)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from pesagem.dispositivos.balanca.interface import Balanca, ProtocoloBalanca
from pesagem.dispositivos.balanca.simulada import BalancaSimulada, CenarioBalanca
from pesagem.dispositivos.cancela.interface import Cancela, EstadoCancela
from pesagem.dispositivos.cancela.simulada import CancelaSimulada, CenarioCancela
from pesagem.dispositivos.erros import (
    ErroConfiguracaoDispositivo,
    ErroDispositivo,
    ErroModoIndisponivel,
)
from pesagem.dispositivos.modo import (
    ModoDispositivo,
    criar_balanca,
    criar_cancela,
    selecionar_modo,
)


class ProtocoloDeTeste:
    """Dublê só para os testes: nenhum protocolo real existe ainda (Q-01)."""

    def montar_pedido(self) -> bytes | None:
        return None

    def interpretar_quadro(self, quadro: bytes) -> Decimal | None:
        return None


PROTOCOLOS: dict[str, ProtocoloBalanca] = {"MODELO_TESTE": ProtocoloDeTeste()}


class Fabrica:
    """Conta quantas vezes o simulador foi criado."""

    def __init__(self) -> None:
        self.criados = 0

    def balanca(self) -> Balanca:
        self.criados += 1
        return BalancaSimulada(
            CenarioBalanca.ESTAVEL, Decimal("1"), lambda: datetime.now(UTC)
        )

    def cancela(self) -> Cancela:
        self.criados += 1
        return CancelaSimulada(CenarioCancela.CONFIRMADO, EstadoCancela.FECHADA)


@pytest.mark.parametrize(
    ("valor", "modo"),
    [
        (None, ModoDispositivo.SIMULADO),
        ("", ModoDispositivo.SIMULADO),
        ("SIMULADO", ModoDispositivo.SIMULADO),
        ("REAL", ModoDispositivo.REAL),
    ],
)
def test_seleciona_modo(valor: str | None, modo: ModoDispositivo) -> None:
    """CA-014 (RNF-003: ausente é SIMULADO)."""
    assert selecionar_modo(valor) is modo


@pytest.mark.parametrize(
    "valor", ["real", " REAL", "REAL ", "SIMULADA", "simulado", "X", " "]
)
def test_modo_invalido_levanta_erro(valor: str) -> None:
    """CA-014: nunca escolhe um modo parecido."""
    with pytest.raises(ErroConfiguracaoDispositivo):
        selecionar_modo(valor)


def test_simulado_cria_os_simuladores() -> None:
    """§6.4."""
    fabrica = Fabrica()
    balanca = criar_balanca(ModoDispositivo.SIMULADO, None, {}, fabrica.balanca)
    cancela = criar_cancela(ModoDispositivo.SIMULADO, fabrica.cancela)
    assert isinstance(balanca, BalancaSimulada)
    assert isinstance(cancela, CancelaSimulada)
    assert fabrica.criados == 2


def test_real_e_indisponivel_e_nao_cria_simulador() -> None:
    """CA-015 (P-3: nunca cai para o simulado)."""
    fabrica = Fabrica()
    with pytest.raises(ErroModoIndisponivel):
        criar_balanca(ModoDispositivo.REAL, "MODELO_TESTE", PROTOCOLOS, fabrica.balanca)
    with pytest.raises(ErroModoIndisponivel):
        criar_cancela(ModoDispositivo.REAL, fabrica.cancela)
    assert fabrica.criados == 0


@pytest.mark.parametrize("nome", [None, "", "OUTRO_MODELO", "modelo_teste"])
def test_real_com_protocolo_ausente_ou_desconhecido(nome: str | None) -> None:
    """CA-018."""
    fabrica = Fabrica()
    with pytest.raises(ErroConfiguracaoDispositivo):
        criar_balanca(ModoDispositivo.REAL, nome, PROTOCOLOS, fabrica.balanca)
    assert fabrica.criados == 0


def test_erros_derivam_de_erro_dispositivo() -> None:
    """§7 (`CONVENCOES.md` §4.5)."""
    assert issubclass(ErroConfiguracaoDispositivo, ErroDispositivo)
    assert issubclass(ErroModoIndisponivel, ErroDispositivo)
