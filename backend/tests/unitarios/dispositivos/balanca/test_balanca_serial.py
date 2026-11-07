"""Testes da balança serial sem hardware (spec 029, `dispositivos-serial`).

O PySerial abre `socket://`, e um servidor TCP local faz o papel do equipamento.
O protocolo daqui é fictício e existe só nos testes: não é de nenhum modelo real.
"""

import asyncio
import socket
import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import pytest

from pesagem.dispositivos.balanca.interface import (
    FalhaBalanca,
    LeituraBalanca,
    MotivoFalhaBalanca,
)
from pesagem.dispositivos.balanca.serial import BalancaSerial, ParametrosSerial

INSTANTE = datetime(2026, 11, 7, 8, 0, tzinfo=UTC)
TIMEOUT_MS = 300


class ProtocoloDeTeste:
    """Quadro fictício `<peso>`; pedido `?` (ou nenhum)."""

    def __init__(self, pedido: bytes | None = b"?") -> None:
        self._pedido = pedido

    def montar_pedido(self) -> bytes | None:
        return self._pedido

    def extrair_quadro(self, recebido: bytes) -> bytes | None:
        inicio = recebido.find(b"<")
        fim = recebido.find(b">", inicio + 1)
        if inicio < 0 or fim < 0:
            return None
        return recebido[inicio : fim + 1]

    def interpretar_quadro(self, quadro: bytes) -> Decimal | None:
        try:
            return Decimal(quadro[1:-1].decode("ascii"))
        except (InvalidOperation, UnicodeDecodeError):
            return None


# Recebe a conexão e a lista onde guardar os pedidos recebidos.
Atendimento = Callable[[socket.socket, list[bytes]], None]


class EquipamentoFalso:
    """Servidor TCP local; cada conexão é atendida pelo próximo atendimento."""

    def __init__(self, *atendimentos: Atendimento) -> None:
        self.pedidos: list[bytes] = []
        self.conexoes = 0
        self._atendimentos = list(atendimentos)
        self._servidor = socket.create_server(("127.0.0.1", 0))
        self.url = f"socket://127.0.0.1:{self._servidor.getsockname()[1]}"
        self._abertas: list[socket.socket] = []
        threading.Thread(target=self._aceitar, daemon=True).start()

    def _aceitar(self) -> None:
        for atender in self._atendimentos:
            try:
                conexao, _ = self._servidor.accept()
            except OSError:
                return  # servidor fechado no fim do teste
            self.conexoes += 1
            self._abertas.append(conexao)
            try:
                atender(conexao, self.pedidos)
            except OSError:
                return

    def fechar(self) -> None:
        for s in (self._servidor, *self._abertas):
            s.close()


def responder(*respostas: list[bytes]) -> Atendimento:
    """A cada pedido, envia os pedaços da próxima resposta (`[]` = silêncio)."""

    def atender(conexao: socket.socket, pedidos: list[bytes]) -> None:
        for pedacos in respostas:
            pedido = conexao.recv(64)
            if not pedido:
                return
            pedidos.append(pedido)
            for pedaco in pedacos:
                conexao.sendall(pedaco)
                time.sleep(0.02)
        while conexao.recv(64):  # espera o cliente fechar
            pass

    return atender


def cair_no_primeiro_pedido(conexao: socket.socket, pedidos: list[bytes]) -> None:
    pedidos.append(conexao.recv(64))
    conexao.close()


def transmitir_sem_pedido(conexao: socket.socket, pedidos: list[bytes]) -> None:
    """Balança que transmite continuamente, sem esperar pedido."""
    conexao.setblocking(False)
    while True:
        try:
            dados = conexao.recv(64)
        except BlockingIOError:
            dados = None
        if dados == b"":
            return  # cliente fechou
        if dados:
            pedidos.append(dados)
        conexao.sendall(b"<12340>")
        time.sleep(0.05)


def parametros(porta: str) -> ParametrosSerial:
    return ParametrosSerial(porta, 9600, "N", 8, 1, TIMEOUT_MS, 10)


@pytest.fixture
def criar() -> Iterator[Callable[..., tuple[BalancaSerial, EquipamentoFalso]]]:
    criados: list[tuple[BalancaSerial, EquipamentoFalso]] = []

    def fabrica(
        *atendimentos: Atendimento, pedido: bytes | None = b"?"
    ) -> tuple[BalancaSerial, EquipamentoFalso]:
        equipamento = EquipamentoFalso(*atendimentos)
        balanca = BalancaSerial(
            ProtocoloDeTeste(pedido), parametros(equipamento.url), lambda: INSTANTE
        )
        criados.append((balanca, equipamento))
        return balanca, equipamento

    yield fabrica
    for balanca, equipamento in criados:
        balanca.fechar()
        equipamento.fechar()


def ler(balanca: BalancaSerial, vezes: int = 1) -> list[LeituraBalanca | FalhaBalanca]:
    async def ler_varias() -> list[LeituraBalanca | FalhaBalanca]:
        return [await balanca.ler_peso() for _ in range(vezes)]

    return asyncio.run(ler_varias())


def test_le_quadro_completo(
    criar: Callable[..., tuple[BalancaSerial, EquipamentoFalso]],
) -> None:
    """CA-001, CA-008: pedido enviado, peso com o relógio injetado."""
    balanca, equipamento = criar(responder([b"<15000.5>"]))
    assert ler(balanca) == [LeituraBalanca(Decimal("15000.5"), INSTANTE, 1)]
    assert equipamento.pedidos == [b"?"]


def test_monta_quadro_que_chega_em_pedacos(
    criar: Callable[..., tuple[BalancaSerial, EquipamentoFalso]],
) -> None:
    """CA-002."""
    balanca, _ = criar(responder([b"<15", b"0", b"00>"]))
    assert ler(balanca) == [LeituraBalanca(Decimal("15000"), INSTANTE, 1)]


def test_ignora_lixo_antes_do_quadro_e_dados_antigos(
    criar: Callable[..., tuple[BalancaSerial, EquipamentoFalso]],
) -> None:
    """CA-003: o `<99999>` que sobra da 1ª leitura não é usado na 2ª."""
    balanca, equipamento = criar(responder([b"\x00lixo<15000><99999>"], [b"<20000>"]))
    assert ler(balanca, 2) == [
        LeituraBalanca(Decimal("15000"), INSTANTE, 1),
        LeituraBalanca(Decimal("20000"), INSTANTE, 1),
    ]
    assert equipamento.conexoes == 1  # porta aberta uma vez só (CA-007)


def test_sem_resposta_tenta_duas_vezes(
    criar: Callable[..., tuple[BalancaSerial, EquipamentoFalso]],
) -> None:
    """CA-004: inclui o quadro que nunca termina."""
    balanca, equipamento = criar(responder([], [b"<150"]))
    inicio = time.monotonic()
    assert ler(balanca) == [FalhaBalanca(MotivoFalhaBalanca.SEM_RESPOSTA, 2)]
    assert equipamento.pedidos == [b"?", b"?"]
    # Cada tentativa respeita o timeout; nunca bloqueia indefinidamente.
    assert time.monotonic() - inicio < 2 * TIMEOUT_MS / 1000 + 1


def test_quadro_corrompido_nao_repete(
    criar: Callable[..., tuple[BalancaSerial, EquipamentoFalso]],
) -> None:
    """CA-005."""
    balanca, equipamento = criar(responder([b"<1x0>"]))
    assert ler(balanca) == [FalhaBalanca(MotivoFalhaBalanca.QUADRO_CORROMPIDO, 1)]
    assert equipamento.pedidos == [b"?"]


def test_porta_inexistente_e_desconectada() -> None:
    """CA-006."""
    balanca = BalancaSerial(
        ProtocoloDeTeste(), parametros("/dev/pesagem-nao-existe"), lambda: INSTANTE
    )
    assert ler(balanca, 2) == [FalhaBalanca(MotivoFalhaBalanca.DESCONECTADA, 1)] * 2


def test_reabre_depois_de_desconectada(
    criar: Callable[..., tuple[BalancaSerial, EquipamentoFalso]],
) -> None:
    """CA-007."""
    balanca, equipamento = criar(cair_no_primeiro_pedido, responder([b"<15000>"]))
    assert ler(balanca, 2) == [
        FalhaBalanca(MotivoFalhaBalanca.DESCONECTADA, 1),
        LeituraBalanca(Decimal("15000"), INSTANTE, 1),
    ]
    assert equipamento.conexoes == 2


def test_sem_pedido_nada_e_escrito(
    criar: Callable[..., tuple[BalancaSerial, EquipamentoFalso]],
) -> None:
    """CA-008: modelo que transmite sem pedido."""
    balanca, equipamento = criar(transmitir_sem_pedido, pedido=None)
    assert ler(balanca) == [LeituraBalanca(Decimal("12340"), INSTANTE, 1)]
    assert equipamento.pedidos == []
