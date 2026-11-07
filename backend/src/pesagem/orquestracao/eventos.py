"""Eventos em memória para o SSE e estado dos dispositivos (spec 015 §5.5, §6.10).

Um processo só (ADR-0002, ADR-0005 §4.9). Nenhum evento leva imagem.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pesagem.dispositivos.balanca.interface import MotivoFalhaBalanca
from pesagem.dispositivos.cancela.interface import EstadoCancela, ResultadoComando
from pesagem.dispositivos.modo import ModoDispositivo
from pesagem.dominio.operacao.maquina_estados import CancelaPedida, ComandoPedido
from pesagem.dominio.pesagem.aceitacao_peso import LeituraPeso, MotivoRejeicaoPeso
from pesagem.lpr.posicao.interface import ResultadoPosicao
from pesagem.persistencia.repositorios.leitura_placa import NovaLeituraPlaca
from pesagem.persistencia.repositorios.pesagem import (
    LiberacaoCaminhao,
    OperacaoRegistrada,
)

registro = logging.getLogger(__name__)

# Eventos por assinante antes de descartar; o `GET` corrige (ADR-0005 §4.2).
TAMANHO_FILA = 100


@dataclass(frozen=True)
class AvaliacaoPeso:
    aceito: bool
    motivo_rejeicao: MotivoRejeicaoPeso | None
    avaliada_em: datetime


@dataclass(frozen=True)
class EstadoBalanca:
    modo: ModoDispositivo
    comunicacao: str  # OK | FALHA | DESCONHECIDO
    motivo_falha: MotivoFalhaBalanca | None
    comunicacao_em: datetime | None
    ultima_leitura: LeituraPeso | None
    avaliacao_peso: AvaliacaoPeso | None


@dataclass(frozen=True)
class UltimoComandoCancela:
    comando: ComandoPedido
    resultado: ResultadoComando
    tentativas: int
    concluido_em: datetime
    pesagem_id: int


@dataclass(frozen=True)
class EstadoCancelaConhecido:
    cancela: CancelaPedida
    modo: ModoDispositivo
    estado: EstadoCancela | None
    estado_em: datetime | None
    ultimo_comando: UltimoComandoCancela | None


@dataclass(frozen=True)
class EstadoPosicao:
    modo: ModoDispositivo
    resultado: ResultadoPosicao | None
    capturada_em: datetime | None
    analisada_em: datetime | None


@dataclass(frozen=True)
class EstadoIdentificacao:
    modo: ModoDispositivo
    resultado: str | None  # OK | FALHA_IMAGEM | FALHA_LEITOR
    analisada_em: datetime | None


@dataclass(frozen=True)
class EstadoDispositivos:
    balanca: EstadoBalanca
    cancelas: tuple[EstadoCancelaConhecido, EstadoCancelaConhecido]
    posicao: EstadoPosicao
    identificacao: EstadoIdentificacao


@dataclass(frozen=True)
class EventoOperacao:
    operacao: OperacaoRegistrada


@dataclass(frozen=True)
class EventoLeituraPlaca:
    leitura_placa_id: int
    leitura: NovaLeituraPlaca


@dataclass(frozen=True)
class EventoPesoLido:
    peso_kg: Decimal
    lida_em: datetime


@dataclass(frozen=True)
class EventoBalanca:
    estado: EstadoBalanca


@dataclass(frozen=True)
class EventoCancela:
    estado: EstadoCancelaConhecido


@dataclass(frozen=True)
class EventoPosicao:
    estado: EstadoPosicao


@dataclass(frozen=True)
class EventoIdentificacao:
    estado: EstadoIdentificacao


@dataclass(frozen=True)
class EventoLiberacaoCaminhao:
    liberacao: LiberacaoCaminhao


type Evento = (
    EventoOperacao
    | EventoLeituraPlaca
    | EventoPesoLido
    | EventoBalanca
    | EventoCancela
    | EventoPosicao
    | EventoIdentificacao
    | EventoLiberacaoCaminhao
)


class DistribuidorEventos:
    def __init__(self) -> None:
        self._filas: set[asyncio.Queue[Evento]] = set()

    def assinar(self) -> asyncio.Queue[Evento]:
        fila: asyncio.Queue[Evento] = asyncio.Queue(TAMANHO_FILA)
        self._filas.add(fila)
        return fila

    def cancelar(self, fila: asyncio.Queue[Evento]) -> None:
        self._filas.discard(fila)

    def publicar(self, evento: Evento) -> None:
        for fila in self._filas:
            try:
                fila.put_nowait(evento)
            except asyncio.QueueFull:
                registro.warning(
                    "assinante lento: %s descartado", type(evento).__name__
                )
