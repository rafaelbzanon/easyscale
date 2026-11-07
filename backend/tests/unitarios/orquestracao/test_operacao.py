"""Orquestração com simuladores e persistência em memória (spec 015 §11)."""

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import pytest
from memoria import Agendamento, BancoMemoria, Veiculo

from pesagem.dispositivos.balanca.simulada import BalancaSimulada, CenarioBalanca
from pesagem.dispositivos.cancela.interface import ComandoCancela, EstadoCancela
from pesagem.dispositivos.cancela.simulada import CancelaSimulada, CenarioCancela
from pesagem.dispositivos.modo import ModoDispositivo
from pesagem.dominio.autorizacao.decisao import MotivoNaoAutorizacao
from pesagem.dominio.operacao.maquina_estados import (
    COMANDO_PENDENTE,
    AcaoManual,
    CancelaPedida,
    ComandoPedido,
    MotivoIntervencao,
    Operacao,
    SituacaoOperacao,
    TipoAcaoManual,
    TransicaoAplicada,
    TransicaoRejeitada,
)
from pesagem.dominio.pesagem.aceitacao_peso import ParametrosAceitacaoPeso
from pesagem.dominio.pesagem.calculo_peso import (
    ClassificacaoPesoLiquido,
    ParametrosPesoLiquido,
    TipoOperacao,
)
from pesagem.dominio.placa.selecao import ParametrosLeituraPlaca
from pesagem.lpr.fontes.interface import FalhaImagem, MotivoFalhaImagem
from pesagem.lpr.posicao.simulada import CenarioPosicao, FontePosicaoSimulada
from pesagem.lpr.reconhecedor_simulado import ReconhecedorPlacaSimulado
from pesagem.lpr.resultado import (
    FalhaLeitor,
    LeituraPlaca,
    LeituraRoi,
    Roi,
    TextoLido,
    TextoOcr,
)
from pesagem.orquestracao.configuracao import ConfiguracaoOrquestracao
from pesagem.orquestracao.erros import ErroLiberacaoEntrada, ErroOperacaoNaoOcupaBalanca
from pesagem.orquestracao.eventos import (
    DistribuidorEventos,
    Evento,
    EventoLiberacaoCaminhao,
    EventoPesoLido,
)
from pesagem.orquestracao.operacao import Orquestracao
from pesagem.orquestracao.repositorios import Banco
from pesagem.persistencia.erros import (
    ErroBancoIndisponivel,
    ErroConflitoVersao,
    ErroLiberacaoIndisponivel,
)
from pesagem.persistencia.repositorios.pesagem import OperacaoRegistrada

S = SituacaoOperacao
C = CancelaPedida
HOJE = date(2026, 11, 7)
INICIO = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)  # 09:00 no pátio (UTC-3)
FUSO = timedelta(hours=-3)
CONFIGURACAO = ConfiguracaoOrquestracao(
    fuso_patio=__import__("datetime").timezone(FUSO),
    intervalo_analise_ms=100,
    idade_maxima_imagem_ms=2_000,
    intervalo_leitura_balanca_ms=100,
    tempo_limite_posicionamento_ms=60_000,
    tempo_limite_pesagem_ms=60_000,
    tempo_limite_saida_balanca_ms=60_000,
    intervalo_minimo_peso_ms=500,
)
PESO = ParametrosAceitacaoPeso(Decimal("0"), Decimal("100000"), 2, Decimal("5"), 10_000)
LIQUIDO = ParametrosPesoLiquido(Decimal("20"))
PLACA = ParametrosLeituraPlaca(Decimal("0.8"))
ADMINISTRADOR = 1
PLACA_A, PLACA_B = "ABC1234", "XYZ9876"
CHAVE_A, CHAVE_B = "ABC1C34", "XYZ9I76"


class Relogio:
    """Avança 1 ms a cada consulta, para as leituras nunca repetirem o instante."""

    def __init__(self) -> None:
        self.atual = INICIO

    def __call__(self) -> datetime:
        self.atual += timedelta(milliseconds=1)
        return self.atual

    def avancar(self, ms: int) -> None:
        self.atual += timedelta(milliseconds=ms)


class Cenario:
    def __init__(self) -> None:
        self.relogio = Relogio()
        self.banco = BancoMemoria()
        self.banco.estado.veiculos = {5: Veiculo(CHAVE_A), 6: Veiculo(CHAVE_B)}
        self.banco.estado.agendamentos = {
            10: Agendamento(5, HOJE),
            11: Agendamento(6, HOJE),
        }
        self.balanca = BalancaSimulada(
            CenarioBalanca.ESTAVEL, Decimal("15000"), self.relogio
        )
        self.entrada = CancelaSimulada(CenarioCancela.CONFIRMADO, EstadoCancela.FECHADA)
        self.saida = CancelaSimulada(CenarioCancela.CONFIRMADO, EstadoCancela.FECHADA)
        self.posicao = FontePosicaoSimulada(CenarioPosicao.AUSENTE, self.relogio)
        self.reconhecedor = ReconhecedorPlacaSimulado(self.relogio)
        self.distribuidor = DistribuidorEventos()
        self.eventos = self.distribuidor.assinar()
        banco: Banco = self.banco.transacao
        self.orquestracao = Orquestracao(
            CONFIGURACAO,
            banco,
            self.balanca,
            self.entrada,
            self.saida,
            self.posicao,
            self.reconhecedor.reconhecer,
            PESO,
            LIQUIDO,
            PLACA,
            self.distribuidor,
            self.relogio,
            ModoDispositivo.SIMULADO,
            ModoDispositivo.SIMULADO,
            ModoDispositivo.SIMULADO,
        )

    # Atalhos -----------------------------------------------------------------

    def pesagem(self, pesagem_id: int = 1) -> OperacaoRegistrada:
        return self.banco.estado.pesagens[pesagem_id]

    def situacao(self, pesagem_id: int = 1) -> SituacaoOperacao:
        return self.pesagem(pesagem_id).operacao.situacao

    def comandos(self) -> list[tuple[str, ComandoCancela]]:
        return [("ENTRADA", c) for c in self.entrada.comandos_enviados] + [
            ("SAIDA", c) for c in self.saida.comandos_enviados
        ]

    def eventos_publicados(self) -> list[Evento]:
        itens: list[Evento] = []
        while not self.eventos.empty():
            itens.append(self.eventos.get_nowait())
        return itens

    async def chegar(self, placa: str, confianca: float = 0.95) -> None:
        self.reconhecedor.enfileirar([TextoOcr(placa, confianca)])
        await self.orquestracao.ciclo_identificacao()

    async def posicionar(self, cenario: CenarioPosicao) -> None:
        self.posicao.definir_cenario(cenario)
        await self.orquestracao.ciclo_posicao()

    async def entrar_na_balanca(self, placa: str = PLACA_A) -> None:
        """Da chegada a `POSICIONADA_*`, com a balança livre."""
        await self.chegar(placa)
        await self.posicionar(CenarioPosicao.AUSENTE)
        await self.orquestracao.ciclo_fila()
        await self.posicionar(CenarioPosicao.CONFIRMADA)

    async def pesar(self) -> None:
        for _ in range(PESO.quantidade_leituras_estaveis):
            await self.orquestracao.ciclo_balanca()

    def semear(
        self,
        situacao: SituacaoOperacao,
        situacao_anterior: SituacaoOperacao | None = None,
        pesagem_id: int = 1,
        agendamento_id: int = 10,
        veiculo_id: int = 5,
        **campos: Any,
    ) -> None:
        """Grava uma operação já em andamento, como se viesse de antes do reinício."""
        operacao = Operacao(
            TipoOperacao.CARGA, situacao, 3, situacao_anterior, **campos
        )
        self.banco.estado.agendamentos[agendamento_id].status = "EM_ANDAMENTO"
        self.banco.estado.pesagens[pesagem_id] = OperacaoRegistrada(
            pesagem_id, agendamento_id, 1, veiculo_id, self.relogio(), False, operacao
        )


def executar[T](corrotina: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(corrotina)


def preparado(
    teste: Callable[[Cenario], Coroutine[Any, Any, None]],
) -> Callable[[], None]:
    def envolto() -> None:
        async def rodar() -> None:
            cenario = Cenario()
            await cenario.orquestracao.retomar()
            await teste(cenario)

        executar(rodar())

    envolto.__name__ = teste.__name__
    envolto.__doc__ = teste.__doc__
    return envolto


@preparado
async def test_fluxo_completo_de_carga(c: Cenario) -> None:
    """CA-005, CA-014: 8 comandos na ordem, pesos, líquido e agendamento concluído."""
    await c.entrar_na_balanca()
    assert c.situacao() is S.POSICIONADA_INICIAL
    assert c.banco.estado.agendamentos[10].status == "EM_ANDAMENTO"
    await c.pesar()
    assert c.situacao() is S.SAIDA_INICIAL_LIBERADA
    await c.posicionar(CenarioPosicao.AUSENTE)
    assert c.situacao() is S.EM_CARGA_DESCARGA
    # Volta, pela entrada, com nova leitura da placa (RN-018).
    await c.entrar_na_balanca()
    assert c.situacao() is S.POSICIONADA_FINAL
    c.orquestracao.balanca = BalancaSimulada(
        CenarioBalanca.ESTAVEL, Decimal("25000"), c.relogio
    )
    await c.pesar()
    assert c.situacao() is S.SAIDA_LIBERADA
    await c.posicionar(CenarioPosicao.AUSENTE)
    operacao = c.pesagem().operacao
    assert operacao.situacao is S.FINALIZADA
    assert (operacao.peso_inicial_kg, operacao.peso_final_kg) == (
        Decimal("15000"),
        Decimal("25000"),
    )
    assert operacao.peso_liquido_kg == Decimal("10000")
    assert operacao.classificacao is ClassificacaoPesoLiquido.COM_MOVIMENTACAO
    assert c.banco.estado.agendamentos[10].status == "CONCLUIDO"
    A, F = ComandoCancela.ABRIR, ComandoCancela.FECHAR
    assert c.entrada.comandos_enviados == [A, F, A, F]
    assert c.saida.comandos_enviados == [A, F, A, F]
    assert len(c.banco.estado.comandos) == 8
    assert len(c.banco.estado.imagens) == 4  # 2 placas + 2 posições confirmadas
    leituras = list(c.banco.estado.leituras.values())
    assert [leitura.decisao for leitura in leituras] == ["AUTORIZADA", "RETORNO_ACEITO"]
    assert all(
        leitura.imagem_id
        and leitura.pesagem_id == 1
        and leitura.chave_comparacao == CHAVE_A
        for leitura in leituras
    )


@preparado
async def test_placa_sem_agendamento_registra_e_nao_cria_operacao(c: Cenario) -> None:
    """CA-006 (RN-003)."""
    await c.chegar("DEF5678")
    leitura = c.banco.estado.leituras[1]
    assert leitura.decisao == "NAO_AUTORIZADA"
    assert leitura.motivo == MotivoNaoAutorizacao.VEICULO_NAO_CADASTRADO
    assert leitura.imagem_id == 1 and leitura.placa_normalizada == "DEF5678"
    assert c.banco.estado.pesagens == {} and c.comandos() == []


@preparado
async def test_mesma_decisao_registra_uma_vez_e_mudanca_registra_de_novo(
    c: Cenario,
) -> None:
    """CA-007."""
    c.banco.estado.agendamentos[10].status = "CANCELADO"
    await c.chegar(PLACA_A)
    await c.chegar(PLACA_A)
    assert len(c.banco.estado.leituras) == 1
    c.banco.estado.agendamentos[10].status = "AGENDADO"
    await c.chegar(PLACA_A)
    assert [leitura.decisao for leitura in c.banco.estado.leituras.values()] == [
        "NAO_AUTORIZADA",
        "AUTORIZADA",
    ]
    assert c.situacao() is S.AGUARDANDO_BALANCA_INICIAL
    # Mesma placa de novo: OPERACAO_JA_ABERTA, registrada uma vez.
    await c.chegar(PLACA_A)
    await c.chegar(PLACA_A)
    assert len(c.banco.estado.leituras) == 3
    # Cancelada, o agendamento volta a AGENDADO e a mesma placa entra de novo (RN-009).
    cancelar = AcaoManual(TipoAcaoManual.CANCELAR, "admin", "desistiu")
    await c.orquestracao.aplicar_acao_manual(
        1, c.pesagem().operacao.versao, cancelar, 1
    )
    await c.chegar(PLACA_A)
    assert c.banco.estado.leituras[4].decisao == "AUTORIZADA"
    assert c.banco.estado.leituras[4].pesagem_id == 2
    assert c.situacao(2) is S.AGUARDANDO_BALANCA_INICIAL


@preparado
async def test_falhas_da_camera_e_do_leitor(c: Cenario) -> None:
    """CA-008."""
    await c.orquestracao.ciclo_identificacao()  # SEM_IMAGEM: nada
    assert c.banco.estado.leituras == {}
    c.reconhecedor.enfileirar(FalhaImagem(MotivoFalhaImagem.IMAGEM_INVALIDA, "x.jpg"))
    await c.orquestracao.ciclo_identificacao()
    c.reconhecedor.enfileirar(FalhaLeitor("x.jpg"))
    await c.orquestracao.ciclo_identificacao()
    c.reconhecedor.enfileirar(FalhaImagem(MotivoFalhaImagem.FONTE_INDISPONIVEL, None))
    await c.orquestracao.ciclo_identificacao()
    motivos = [leitura.motivo for leitura in c.banco.estado.leituras.values()]
    assert motivos == ["FALHA_IMAGEM", "FALHA_LEITOR", "FALHA_IMAGEM"]
    assert all(
        leitura.imagem_id is None for leitura in c.banco.estado.leituras.values()
    )
    assert (
        c.orquestracao.estado_dispositivos().identificacao.resultado == "FALHA_IMAGEM"
    )


@preparado
async def test_reserva_da_balanca_por_ordem_de_chegada(c: Cenario) -> None:
    """CA-009 (RN-019)."""
    await c.chegar(PLACA_A)
    await c.chegar(PLACA_B)
    await c.posicionar(CenarioPosicao.AUSENTE)
    await c.orquestracao.ciclo_fila()
    await c.orquestracao.ciclo_fila()
    assert (c.situacao(1), c.situacao(2)) == (
        S.ENTRADA_LIBERADA,
        S.AGUARDANDO_BALANCA_INICIAL,
    )
    await c.posicionar(CenarioPosicao.CONFIRMADA)
    await c.pesar()
    await c.orquestracao.ciclo_fila()
    assert c.situacao(2) is S.AGUARDANDO_BALANCA_INICIAL  # saída ainda aberta
    await c.posicionar(CenarioPosicao.AUSENTE)
    assert c.situacao(1) is S.EM_CARGA_DESCARGA
    await c.orquestracao.ciclo_fila()
    assert c.situacao(2) is S.ENTRADA_LIBERADA


@preparado
async def test_balanca_disponivel_exige_balanca_vazia_recente_e_cancelas_fechadas(
    c: Cenario,
) -> None:
    """CA-010."""
    await c.chegar(PLACA_A)
    await c.orquestracao.ciclo_fila()  # posição nunca analisada
    assert c.situacao() is S.AGUARDANDO_BALANCA_INICIAL
    for cenario in (CenarioPosicao.CONFIRMADA, CenarioPosicao.INCONCLUSIVA):
        await c.posicionar(cenario)
        await c.orquestracao.ciclo_fila()
        assert c.situacao() is S.AGUARDANDO_BALANCA_INICIAL
    await c.posicionar(CenarioPosicao.AUSENTE)
    c.relogio.avancar(3_000)  # posição antiga
    await c.orquestracao.ciclo_fila()
    assert c.situacao() is S.AGUARDANDO_BALANCA_INICIAL
    await c.posicionar(CenarioPosicao.AUSENTE)
    c.saida.definir_cenario(CenarioCancela.SENSOR_SEM_RESPOSTA)
    await c.orquestracao.ciclo_fila()
    assert c.situacao() is S.AGUARDANDO_BALANCA_INICIAL
    c.saida.definir_cenario(CenarioCancela.CONFIRMADO)
    aberta = CancelaSimulada(CenarioCancela.CONFIRMADO, EstadoCancela.ABERTA)
    c.orquestracao._cancelas[C.SAIDA] = aberta  # noqa: SLF001
    await c.orquestracao.ciclo_fila()
    assert c.situacao() is S.AGUARDANDO_BALANCA_INICIAL
    c.orquestracao._cancelas[C.SAIDA] = c.saida  # noqa: SLF001
    await c.orquestracao.ciclo_fila()
    assert c.situacao() is S.ENTRADA_LIBERADA
    assert c.comandos() == [("ENTRADA", ComandoCancela.ABRIR)]


@pytest.mark.parametrize("situacao", list(COMANDO_PENDENTE))
@pytest.mark.parametrize("sensor", ["pedida", "contraria", "desconhecido"])
def test_retomada_com_comando_pendente(situacao: SituacaoOperacao, sensor: str) -> None:
    """CA-011 (spec 006 §7.2): nada é reenviado às cegas."""

    async def rodar() -> None:
        c = Cenario()
        acao = COMANDO_PENDENTE[situacao]
        pedida = (
            EstadoCancela.ABERTA
            if acao.comando is ComandoPedido.ABRIR
            else EstadoCancela.FECHADA
        )
        contraria = (
            EstadoCancela.FECHADA
            if pedida is EstadoCancela.ABERTA
            else EstadoCancela.ABERTA
        )
        cancela = CancelaSimulada(
            CenarioCancela.SENSOR_SEM_RESPOSTA
            if sensor == "desconhecido"
            else CenarioCancela.CONFIRMADO,
            pedida if sensor == "pedida" else contraria,
        )
        c.orquestracao._cancelas[acao.cancela] = cancela  # noqa: SLF001
        precisa_peso = (
            "FINAL" in situacao
            or "RETORNO" in situacao
            or situacao in (S.FECHANDO_SAIDA, S.SAIDA_LIBERADA)
        )
        c.semear(
            situacao,
            peso_inicial_kg=Decimal("1") if precisa_peso else None,
            peso_inicial_em=INICIO if precisa_peso else None,
        )
        await c.orquestracao.retomar()
        depois = c.situacao()
        if sensor == "pedida":
            assert cancela.comandos_enviados == [] and depois is not situacao
            assert depois is not S.AGUARDANDO_INTERVENCAO
        elif sensor == "contraria":
            assert len(cancela.comandos_enviados) == 1 and depois is not situacao
        else:
            assert cancela.comandos_enviados == []
            assert depois is S.AGUARDANDO_INTERVENCAO
            assert (
                c.pesagem().operacao.motivo_intervencao
                is MotivoIntervencao.REINICIO_INCONCLUSIVO
            )

    executar(rodar())


@pytest.mark.parametrize(
    "situacao",
    [
        S.POSICIONADA_INICIAL,
        S.AGUARDANDO_INTERVENCAO,
        S.FINALIZADA,
        S.CANCELADA,
        S.EM_CARGA_DESCARGA,
    ],
)
def test_retomada_sem_comando_pendente_nao_muda_nada(
    situacao: SituacaoOperacao,
) -> None:
    """CA-012."""

    async def rodar() -> None:
        c = Cenario()
        anterior = S.AUTORIZADA if situacao is S.AGUARDANDO_INTERVENCAO else None
        c.semear(situacao, anterior)
        versao = c.pesagem().operacao.versao
        await c.orquestracao.retomar()
        assert c.situacao() is situacao and c.pesagem().operacao.versao == versao
        assert c.comandos() == []

    executar(rodar())


@preparado
async def test_falha_na_gravacao_nao_avanca_nem_comanda(c: Cenario) -> None:
    """CA-013 (spec 006 §7.3)."""
    await c.chegar(PLACA_A)
    await c.posicionar(CenarioPosicao.AUSENTE)
    c.banco.falhar_em = "gravar_transicao"
    await c.orquestracao.ciclo_fila()
    assert c.situacao() is S.AGUARDANDO_BALANCA_INICIAL and c.comandos() == []
    await c.orquestracao.ciclo_fila()
    await c.posicionar(CenarioPosicao.CONFIRMADA)
    assert c.situacao() is S.POSICIONADA_INICIAL
    c.banco.falhar_em = "gravar_transicao"
    await c.pesar()
    operacao = c.pesagem().operacao
    assert (
        operacao.situacao is S.POSICIONADA_INICIAL and operacao.peso_inicial_kg is None
    )
    assert c.saida.comandos_enviados == []
    # Gravação que falha depois de um comando enviado: só a gravação é repetida.
    c.banco.falhar_em = "registrar_comando_cancela"
    await c.pesar()
    assert c.situacao() is S.PESO_INICIAL_OK and c.saida.comandos_enviados == [
        ComandoCancela.ABRIR
    ]
    await c.orquestracao.ciclo_fila()
    assert (
        c.situacao() is S.SAIDA_INICIAL_LIBERADA and len(c.saida.comandos_enviados) == 1
    )


@preparado
async def test_cancelamento_e_liberacao_do_caminhao_na_balanca(c: Cenario) -> None:
    """CA-014, CA-015 (RN-020, spec 006 §6.4)."""
    await c.entrar_na_balanca()
    await c.chegar(PLACA_B)
    cancelar = AcaoManual(TipoAcaoManual.CANCELAR, "admin", "caminhão errado")
    await c.orquestracao.aplicar_acao_manual(
        1, c.pesagem().operacao.versao, cancelar, ADMINISTRADOR
    )
    assert c.situacao() is S.CANCELADA and c.pesagem().aguarda_liberacao_balanca
    assert c.banco.estado.agendamentos[10].status == "AGENDADO"
    assert c.banco.estado.liberacoes[1].etapa == "PENDENTE"
    await c.posicionar(CenarioPosicao.AUSENTE)
    await c.orquestracao.ciclo_fila()
    assert c.situacao(2) is S.AGUARDANDO_BALANCA_INICIAL  # fila parada
    with pytest.raises(ErroOperacaoNaoOcupaBalanca):
        await c.orquestracao.liberar_caminhao_cancelado(2, ADMINISTRADOR, "x")
    # Falha ao abrir: pendência mantida e pedido repetível.
    c.saida.definir_cenario(CenarioCancela.NAO_MOVE)
    liberacao = await c.orquestracao.liberar_caminhao_cancelado(
        1, ADMINISTRADOR, "liberar"
    )
    assert (liberacao.etapa, liberacao.motivo_falha) == (
        "FALHOU",
        "CANCELA_SEM_CONFIRMACAO",
    )
    c.saida.definir_cenario(CenarioCancela.CONFIRMADO)
    await c.posicionar(CenarioPosicao.CONFIRMADA)
    liberacao = await c.orquestracao.liberar_caminhao_cancelado(
        1, ADMINISTRADOR, "liberar"
    )
    assert liberacao.etapa == "AGUARDANDO_BALANCA_VAZIA"
    with pytest.raises(ErroLiberacaoIndisponivel):
        await c.orquestracao.liberar_caminhao_cancelado(1, ADMINISTRADOR, "de novo")
    await c.posicionar(CenarioPosicao.CONFIRMADA)  # ainda na balança
    assert c.banco.estado.liberacoes[1].etapa == "AGUARDANDO_BALANCA_VAZIA"
    await c.posicionar(CenarioPosicao.AUSENTE)
    assert c.banco.estado.liberacoes[1].etapa == "CONCLUIDA"
    assert not c.pesagem().aguarda_liberacao_balanca
    assert [r.responsavel_id for r in c.banco.estado.comandos if r.pesagem_id == 1][
        -2:
    ] == [1, 1]
    await c.orquestracao.ciclo_fila()
    assert c.situacao(2) is S.ENTRADA_LIBERADA
    etapas = [
        e.liberacao.etapa
        for e in c.eventos_publicados()
        if isinstance(e, EventoLiberacaoCaminhao)
    ]
    assert etapas == [
        "PENDENTE",
        "ABRINDO_SAIDA",
        "FALHOU",
        "ABRINDO_SAIDA",
        "AGUARDANDO_BALANCA_VAZIA",
        "FECHANDO_SAIDA",
        "CONCLUIDA",
    ]


@preparado
async def test_liberacao_aguardando_balanca_vazia_esgota_o_tempo(c: Cenario) -> None:
    """CA-015: sem câmera confirmando a balança vazia, FALHOU com TEMPO_ESGOTADO."""
    c.semear(S.CANCELADA)
    c.banco.estado.pesagens[1] = replace(c.pesagem(), aguarda_liberacao_balanca=True)
    from pesagem.persistencia.repositorios.pesagem import LiberacaoCaminhao

    c.banco.estado.liberacoes[1] = LiberacaoCaminhao(
        1, "PENDENTE", None, None, None, None, INICIO
    )
    await c.orquestracao.liberar_caminhao_cancelado(1, ADMINISTRADOR, "x")
    await c.posicionar(CenarioPosicao.INCONCLUSIVA)
    c.relogio.avancar(60_000)
    await c.posicionar(CenarioPosicao.INCONCLUSIVA)
    assert (
        c.banco.estado.liberacoes[1].etapa,
        c.banco.estado.liberacoes[1].motivo_falha,
    ) == (
        "FALHOU",
        "TEMPO_ESGOTADO",
    )
    assert c.saida.comandos_enviados == [ComandoCancela.ABRIR]


@preparado
async def test_falhas_da_balanca_nao_gravam_peso(c: Cenario) -> None:
    """CA-016 (RN-004, RN-005)."""
    await c.entrar_na_balanca()
    c.orquestracao.balanca = BalancaSimulada(
        CenarioBalanca.SEM_RESPOSTA, Decimal("1"), c.relogio
    )
    await c.pesar()
    await c.pesar()
    c.orquestracao.balanca = BalancaSimulada(
        CenarioBalanca.INSTAVEL, Decimal("15000"), c.relogio, amplitude_kg=Decimal("10")
    )
    await c.pesar()
    await c.pesar()
    assert (
        c.situacao() is S.POSICIONADA_INICIAL
        and c.pesagem().operacao.peso_inicial_kg is None
    )
    registrados = [
        (r.evento, r.motivo)
        for r in c.banco.estado.auditoria
        if r.tipo == "EVENTO_REGISTRADO"
    ]
    assert registrados.count(("BALANCA_FALHA", "SEM_RESPOSTA")) == 1
    assert registrados.count(("PESO_REJEITADO", "INSTAVEL")) == 1
    assert ("PESO_REJEITADO", "LEITURAS_INSUFICIENTES") not in registrados
    estado = c.orquestracao.estado_dispositivos().balanca
    assert estado.comunicacao == "OK" and estado.avaliacao_peso is not None
    assert estado.avaliacao_peso.motivo_rejeicao == "INSTAVEL"
    c.relogio.avancar(60_000)
    await c.posicionar(CenarioPosicao.CONFIRMADA)
    operacao = c.pesagem().operacao
    assert operacao.situacao is S.AGUARDANDO_INTERVENCAO
    assert operacao.motivo_intervencao is MotivoIntervencao.TEMPO_ESGOTADO
    assert operacao.situacao_anterior is S.POSICIONADA_INICIAL


@pytest.mark.parametrize(
    ("cenario", "motivo"),
    [
        (CenarioCancela.FALHA, MotivoIntervencao.CANCELA_FALHA),
        (CenarioCancela.NAO_MOVE, MotivoIntervencao.CANCELA_SEM_CONFIRMACAO),
        (CenarioCancela.SENSOR_SEM_RESPOSTA, MotivoIntervencao.CANCELA_SEM_CONFIRMACAO),
    ],
)
def test_falha_da_cancela_para_a_operacao(
    cenario: CenarioCancela, motivo: MotivoIntervencao
) -> None:
    """CA-017 (RN-007): falha ao abrir a saída depois do peso inicial."""

    async def rodar() -> None:
        c = Cenario()
        await c.orquestracao.retomar()
        await c.entrar_na_balanca()
        c.saida.definir_cenario(cenario)
        await c.pesar()
        operacao = c.pesagem().operacao
        assert operacao.situacao is S.AGUARDANDO_INTERVENCAO
        assert (operacao.motivo_intervencao, operacao.situacao_anterior) == (
            motivo,
            S.PESO_INICIAL_OK,
        )
        assert operacao.peso_inicial_kg == Decimal("15000")
        enviados = len(c.saida.comandos_enviados)
        assert enviados == (2 if cenario is CenarioCancela.NAO_MOVE else 1)
        estado = c.orquestracao.estado_dispositivos().cancelas[1]
        assert estado.estado is EstadoCancela.DESCONHECIDO
        c.saida.definir_cenario(CenarioCancela.CONFIRMADO)
        tentar = AcaoManual(
            TipoAcaoManual.TENTAR_NOVAMENTE, "op", "equipamento verificado"
        )
        resultado = await c.orquestracao.aplicar_acao_manual(
            1, operacao.versao, tentar, ADMINISTRADOR
        )
        # O 200 significa transição gravada; o comando roda depois (spec 009 §6.3).
        assert isinstance(resultado, TransicaoAplicada)
        assert resultado.operacao.situacao is S.PESO_INICIAL_OK
        await c.orquestracao.aguardar_comandos_agendados()
        assert c.situacao() is S.SAIDA_INICIAL_LIBERADA
        # Com o sensor de volta, a saída já está aberta: nada é reenviado (spec 004 CA-012).
        reenviados = 0 if cenario is CenarioCancela.SENSOR_SEM_RESPOSTA else 1
        assert len(c.saida.comandos_enviados) == enviados + reenviados

    executar(rodar())


@preparado
async def test_imagem_antiga_e_inconclusiva_e_nao_avanca(c: Cenario) -> None:
    """CA-018 (ADR-0005 §4.1), CA-012 da spec 006."""
    await c.chegar(PLACA_A)
    await c.posicionar(CenarioPosicao.AUSENTE)
    await c.orquestracao.ciclo_fila()
    c.posicao = FontePosicaoSimulada(
        CenarioPosicao.CONFIRMADA, c.relogio, atraso_captura_ms=2_500
    )
    c.orquestracao._fonte_posicao = c.posicao  # noqa: SLF001
    await c.orquestracao.ciclo_posicao()
    await c.orquestracao.ciclo_posicao()
    assert c.situacao() is S.ENTRADA_LIBERADA
    assert c.orquestracao.estado_dispositivos().posicao.resultado == "INCONCLUSIVA"
    registrados = [
        r for r in c.banco.estado.auditoria if r.evento == "POSICAO_INCONCLUSIVA"
    ]
    assert len(registrados) == 1  # só quando muda


@preparado
async def test_acao_manual_com_versao_velha_e_confirmacao_manual(c: Cenario) -> None:
    """CA-019 (ADR-0005 §4.5; RN-022)."""
    await c.chegar(PLACA_A)
    await c.posicionar(CenarioPosicao.AUSENTE)
    await c.orquestracao.ciclo_fila()
    versao = c.pesagem().operacao.versao
    acao = AcaoManual(
        TipoAcaoManual.CONFIRMAR_POSICAO_MANUAL, "admin", "câmera coberta"
    )
    with pytest.raises(ErroConflitoVersao):
        await c.orquestracao.aplicar_acao_manual(1, versao - 1, acao, ADMINISTRADOR)
    assert c.situacao() is S.ENTRADA_LIBERADA
    resultado = await c.orquestracao.aplicar_acao_manual(1, versao, acao, ADMINISTRADOR)
    assert isinstance(
        resultado, TransicaoRejeitada
    )  # só vale em AGUARDANDO_INTERVENCAO
    c.relogio.avancar(60_000)
    await c.posicionar(CenarioPosicao.INCONCLUSIVA)
    assert c.situacao() is S.AGUARDANDO_INTERVENCAO
    imagens_antes = len(c.banco.estado.imagens)
    resultado = await c.orquestracao.aplicar_acao_manual(
        1, c.pesagem().operacao.versao, acao, ADMINISTRADOR
    )
    assert isinstance(resultado, TransicaoAplicada)
    await c.orquestracao.aguardar_comandos_agendados()
    assert (
        c.situacao() is S.POSICIONADA_INICIAL and c.pesagem().operacao.liberacao_manual
    )
    assert len(c.banco.estado.imagens) == imagens_antes + 1
    sem_motivo = AcaoManual(TipoAcaoManual.CANCELAR, "admin", "  ")
    resultado = await c.orquestracao.aplicar_acao_manual(
        1, c.pesagem().operacao.versao, sem_motivo, ADMINISTRADOR
    )
    assert isinstance(resultado, TransicaoRejeitada)


@preparado
async def test_liberacao_manual_de_entrada(c: Cenario) -> None:
    """CA-020 (RN-016, §6.7)."""
    liberar = c.orquestracao.liberar_entrada_manual
    await c.chegar(PLACA_A, confianca=0.5)
    assert c.banco.estado.leituras[1].motivo == "CONFIANCA_BAIXA"
    with pytest.raises(ErroLiberacaoEntrada, match="LEITURA_DESATUALIZADA"):
        await liberar(99, 10, ADMINISTRADOR, "x")
    with pytest.raises(ErroLiberacaoEntrada, match="VEICULO_NAO_CADASTRADO"):
        await liberar(1, 99, ADMINISTRADOR, "agendamento inexistente")
    c.banco.estado.veiculos[5].ativo = False
    with pytest.raises(ErroLiberacaoEntrada, match="VEICULO_INATIVO"):
        await liberar(1, 10, ADMINISTRADOR, "x")
    c.banco.estado.veiculos[5].ativo = True
    operacao = await liberar(1, 10, ADMINISTRADOR, "placa conferida pessoalmente")
    assert (
        operacao.operacao.liberacao_manual
        and c.situacao() is S.AGUARDANDO_BALANCA_INICIAL
    )
    assert c.banco.estado.leituras[1].pesagem_id == 1
    with pytest.raises(ErroLiberacaoEntrada, match="LEITURA_NAO_LIBERAVEL"):
        await liberar(1, 10, ADMINISTRADOR, "de novo")
    # Faixa ainda não começou: substituível. Sem agendamento: não.
    c.banco.estado.agendamentos[11].faixa_hora_inicio = __import__("datetime").time(
        23, 0
    )
    await c.chegar(PLACA_B)
    assert c.banco.estado.leituras[2].motivo == "ANTES_DA_FAIXA"
    await liberar(2, 11, ADMINISTRADOR, "faixa")
    assert c.situacao(2) is S.AGUARDANDO_BALANCA_INICIAL
    await c.chegar("DEF5678")
    with pytest.raises(ErroLiberacaoEntrada, match="MOTIVO_NAO_SUBSTITUIVEL"):
        await liberar(3, 10, ADMINISTRADOR, "x")
    await c.chegar(
        PLACA_A
    )  # OPERACAO_JA_ABERTA: leitura AUTORIZADA? não: NAO_AUTORIZADA
    with pytest.raises(ErroLiberacaoEntrada, match="MOTIVO_NAO_SUBSTITUIVEL"):
        await liberar(4, 10, ADMINISTRADOR, "x")


@preparado
async def test_imagem_que_nao_codifica_vira_falha_imagem(c: Cenario) -> None:
    """CA-021 (P-5)."""

    async def reconhecer() -> LeituraPlaca:
        roi = Roi(0, 0, 0, 0)
        textos = (TextoLido(PLACA_A, Decimal("0.95")),)
        return LeituraPlaca(
            "x",
            c.relogio(),
            np.zeros((0, 0, 3), dtype=np.uint8),
            (LeituraRoi(roi, textos),),
        )

    c.orquestracao._reconhecedor = reconhecer  # noqa: SLF001
    await c.orquestracao.ciclo_identificacao()
    leitura = c.banco.estado.leituras[1]
    assert (leitura.decisao, leitura.motivo, leitura.imagem_id) == (
        "NAO_AUTORIZADA",
        "FALHA_IMAGEM",
        None,
    )
    assert c.banco.estado.pesagens == {}


@preparado
async def test_peso_lido_respeita_intervalo_e_eventos_nao_levam_pixels(
    c: Cenario,
) -> None:
    """CA-022 (ADR-0005 §4.6, §4.7)."""
    await c.entrar_na_balanca()
    c.eventos_publicados()
    c.orquestracao.balanca = BalancaSimulada(
        CenarioBalanca.INSTAVEL, Decimal("15000"), c.relogio, amplitude_kg=Decimal("10")
    )
    for _ in range(4):
        await c.orquestracao.ciclo_balanca()
    eventos = c.eventos_publicados()
    assert sum(isinstance(e, EventoPesoLido) for e in eventos) == 1
    c.relogio.avancar(500)
    await c.orquestracao.ciclo_balanca()
    assert sum(isinstance(e, EventoPesoLido) for e in c.eventos_publicados()) == 1
    assert c.orquestracao.imagem_atual("identificacao") is not None
    assert c.orquestracao.imagem_atual("posicao") is not None
    for evento in eventos:
        assert "pixels" not in repr(evento)


# Regressões da revisão de segurança (Lynx, 2026-11-07).


@preparado
async def test_cancelar_antes_do_comando_agendado_impede_o_comando(c: Cenario) -> None:
    """ALTO 1 (AGENTS §7.1.3; spec 006 §6: CANCELAR não comanda)."""
    c.semear(
        S.AGUARDANDO_INTERVENCAO,
        S.AUTORIZADA,
        motivo_intervencao=MotivoIntervencao.CANCELA_FALHA,
    )
    versao = c.pesagem().operacao.versao
    tentar = AcaoManual(TipoAcaoManual.TENTAR_NOVAMENTE, "op", "m")
    cancelar = AcaoManual(TipoAcaoManual.CANCELAR, "admin", "m")
    await c.orquestracao.aplicar_acao_manual(1, versao, tentar, ADMINISTRADOR)
    await c.orquestracao.aplicar_acao_manual(1, versao + 1, cancelar, ADMINISTRADOR)
    await c.orquestracao.aguardar_comandos_agendados()
    assert c.situacao() is S.CANCELADA
    assert c.comandos() == []


def test_banco_indisponivel_nao_para_os_ciclos() -> None:
    """ALTO 2 (spec 015 §7): o banco fora do ar só adia; os ciclos continuam."""

    async def rodar() -> None:
        c = Cenario()
        await c.orquestracao.retomar()
        chamadas = {"n": 0}

        def falhar() -> list[OperacaoRegistrada]:
            chamadas["n"] += 1
            raise ErroBancoIndisponivel("OperationalError")

        c.banco.operacoes_abertas = falhar  # type: ignore[method-assign]
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(c.orquestracao.executar(), 0.35)
        assert chamadas["n"] >= 6  # vários períodos dos ciclos, sem morrer

    executar(rodar())


@preparado
async def test_etapa_da_liberacao_nao_gravada_nao_comanda(c: Cenario) -> None:
    """MÉDIO 3 (spec 015 §6.8): sem gravar FECHANDO_SAIDA, nenhum FECHAR é enviado."""
    await c.entrar_na_balanca()
    cancelar = AcaoManual(TipoAcaoManual.CANCELAR, "admin", "m")
    await c.orquestracao.aplicar_acao_manual(
        1, c.pesagem().operacao.versao, cancelar, 1
    )
    await c.orquestracao.liberar_caminhao_cancelado(1, ADMINISTRADOR, "m")
    assert c.saida.comandos_enviados == [ComandoCancela.ABRIR]
    for _ in range(2):
        c.banco.falhar_em = "atualizar_liberacao_caminhao"
        await c.posicionar(CenarioPosicao.AUSENTE)
        assert c.saida.comandos_enviados == [ComandoCancela.ABRIR]
        assert c.banco.estado.liberacoes[1].etapa == "AGUARDANDO_BALANCA_VAZIA"
    await c.posicionar(CenarioPosicao.AUSENTE)
    assert c.saida.comandos_enviados == [ComandoCancela.ABRIR, ComandoCancela.FECHAR]
    assert c.banco.estado.liberacoes[1].etapa == "CONCLUIDA"


@preparado
async def test_tempo_limite_usa_a_situacao_atual_e_nao_a_fotografia(c: Cenario) -> None:
    """MÉDIO 4: a posição confirmada no mesmo ciclo não vira TEMPO_ESGOTADO falso."""
    await c.chegar(PLACA_A)
    await c.posicionar(CenarioPosicao.AUSENTE)
    await c.orquestracao.ciclo_fila()
    assert c.situacao() is S.ENTRADA_LIBERADA
    c.relogio.avancar(60_000)
    await c.posicionar(CenarioPosicao.CONFIRMADA)
    assert c.situacao() is S.POSICIONADA_INICIAL
    # Em POSICIONADA_* o tempo conta de novo, e aí esgota.
    c.relogio.avancar(60_000)
    await c.posicionar(CenarioPosicao.CONFIRMADA)
    operacao = c.pesagem().operacao
    assert operacao.situacao is S.AGUARDANDO_INTERVENCAO
    assert operacao.situacao_anterior is S.POSICIONADA_INICIAL


@preparado
async def test_agendamento_de_outro_veiculo_nao_cria_operacao(c: Cenario) -> None:
    """BAIXO 7 (spec 014): a criação exige o veículo da decisão."""
    c.banco.estado.agendamentos[
        10
    ].veiculo_id = 6  # trocado entre a decisão e a gravação
    await c.chegar(PLACA_A)
    assert c.banco.estado.pesagens == {}
