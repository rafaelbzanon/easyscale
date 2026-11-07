"""Ciclos da operação (spec 015 §6, §7).

Tarefas `asyncio` num só processo (D-05): leituras de câmera, posição e balança
ficam fora da trava; "aplicar evento → gravar → comandar → gravar o resultado"
roda sob a trava, para nenhum dispositivo receber duas chamadas ao mesmo tempo
e dois eventos nunca se misturarem. Toda situação é gravada **antes** do
comando (spec 006 §7.2). Falha de gravação: nada avança, nada é comandado.
"""

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from pesagem.dispositivos.balanca.interface import Balanca, FalhaBalanca
from pesagem.dispositivos.cancela.interface import (
    Cancela,
    EstadoCancela,
    ResultadoComando,
    ResultadoComandoCancela,
)
from pesagem.dispositivos.modo import ModoDispositivo
from pesagem.dominio.autorizacao.decisao import (
    MOTIVOS_SUBSTITUIVEIS,
    AgendamentoCandidato,
    EntradaAutorizada,
    EntradaNaoAutorizada,
    FalhaIdentificacao,
    LeituraIdentificacao,
    MotivoNaoAutorizacao,
    OperacaoAberta,
    RetornoAceito,
    SituacaoVeiculo,
    decidir_autorizacao,
    decidir_liberacao_manual,
)
from pesagem.dominio.operacao.maquina_estados import (
    COMANDO_PENDENTE,
    AcaoManual,
    AcaoPedida,
    CancelaPedida,
    ComandoPedido,
    EventoAutomatico,
    Operacao,
    PesoAceito,
    ResultadoTransicao,
    SituacaoOperacao,
    TipoAcaoManual,
    TipoEvento,
    TransicaoAplicada,
    aplicar_evento,
)
from pesagem.dominio.operacao.maquina_estados import (
    EventoOperacao as EventoMaquina,
)
from pesagem.dominio.pesagem.aceitacao_peso import (
    LeituraPeso,
    MotivoRejeicaoPeso,
    ParametrosAceitacaoPeso,
    validar_leituras_peso,
)
from pesagem.dominio.pesagem.aceitacao_peso import (
    PesoAceito as PesoValidado,
)
from pesagem.dominio.pesagem.calculo_peso import ParametrosPesoLiquido, TipoOperacao
from pesagem.dominio.placa.selecao import (
    CandidatoPlaca,
    ParametrosLeituraPlaca,
    PlacaSelecionada,
    selecionar_placa,
)
from pesagem.lpr.codificacao import codificar_jpeg
from pesagem.lpr.fontes.interface import FalhaImagem, MotivoFalhaImagem
from pesagem.lpr.posicao.interface import FontePosicao, LeituraPosicao, ResultadoPosicao
from pesagem.lpr.resultado import FalhaLeitor, LeituraPlaca, Roi
from pesagem.orquestracao.configuracao import ConfiguracaoOrquestracao
from pesagem.orquestracao.erros import (
    ErroLiberacaoEntrada,
    ErroOperacaoNaoOcupaBalanca,
)
from pesagem.orquestracao.eventos import (
    AvaliacaoPeso,
    DistribuidorEventos,
    EstadoBalanca,
    EstadoCancelaConhecido,
    EstadoDispositivos,
    EstadoIdentificacao,
    EstadoPosicao,
    EventoBalanca,
    EventoCancela,
    EventoIdentificacao,
    EventoLeituraPlaca,
    EventoLiberacaoCaminhao,
    EventoOperacao,
    EventoPesoLido,
    EventoPosicao,
    UltimoComandoCancela,
)
from pesagem.orquestracao.repositorios import Banco, Transacao
from pesagem.persistencia.erros import ErroConflitoVersao, ErroPersistencia
from pesagem.persistencia.repositorios.leitura_placa import Json, NovaLeituraPlaca
from pesagem.persistencia.repositorios.pesagem import (
    LiberacaoCaminhao,
    OperacaoRegistrada,
)
from pesagem.persistencia.repositorios.veiculo import (
    SituacaoVeiculo as SituacaoVeiculoRegistrada,
)

registro = logging.getLogger(__name__)

type ReconhecedorPlaca = Callable[
    [], Awaitable[LeituraPlaca | FalhaImagem | FalhaLeitor]
]

_S = SituacaoOperacao
_E = TipoEvento

# Spec 006 §6.3: situações que ocupam a balança.
OCUPAM_BALANCA = frozenset(
    {
        _S.AUTORIZADA,
        _S.ENTRADA_LIBERADA,
        _S.FECHANDO_ENTRADA,
        _S.POSICIONADA_INICIAL,
        _S.PESO_INICIAL_OK,
        _S.SAIDA_INICIAL_LIBERADA,
        _S.FECHANDO_SAIDA_INICIAL,
        _S.RETORNO_AUTORIZADO,
        _S.RETORNO_LIBERADO,
        _S.FECHANDO_ENTRADA_RETORNO,
        _S.POSICIONADA_FINAL,
        _S.PESO_FINAL_OK,
        _S.SAIDA_LIBERADA,
        _S.FECHANDO_SAIDA,
    }
)
AGUARDAM_BALANCA = frozenset(
    {_S.AGUARDANDO_BALANCA_INICIAL, _S.AGUARDANDO_BALANCA_FINAL}
)
POSICIONADAS = frozenset({_S.POSICIONADA_INICIAL, _S.POSICIONADA_FINAL})
AGUARDAM_POSICAO = frozenset({_S.ENTRADA_LIBERADA, _S.RETORNO_LIBERADO})
AGUARDAM_BALANCA_VAZIA = frozenset({_S.SAIDA_INICIAL_LIBERADA, _S.SAIDA_LIBERADA})
ESPERAM_CAMERA = AGUARDAM_POSICAO | POSICIONADAS | AGUARDAM_BALANCA_VAZIA

_EVENTO_POSICAO = {
    ResultadoPosicao.CONFIRMADA: _E.POSICAO_CONFIRMADA,
    ResultadoPosicao.AUSENTE: _E.POSICAO_AUSENTE,
    ResultadoPosicao.INCONCLUSIVA: _E.POSICAO_INCONCLUSIVA,
}
_EVENTO_CANCELA = {
    ResultadoComando.CONFIRMADO: _E.CANCELA_CONFIRMADA,
    ResultadoComando.FALHA: _E.CANCELA_FALHA,
    ResultadoComando.SEM_CONFIRMACAO: _E.CANCELA_SEM_CONFIRMACAO,
}
_MOTIVO_FALHA_LIBERACAO = {
    ResultadoComando.FALHA: "CANCELA_FALHA",
    ResultadoComando.SEM_CONFIRMACAO: "CANCELA_SEM_CONFIRMACAO",
}
_POSICAO_PEDIDA = {
    ComandoPedido.ABRIR: EstadoCancela.ABERTA,
    ComandoPedido.FECHAR: EstadoCancela.FECHADA,
}
_CONFIRMACOES_COM_IMAGEM = frozenset(
    {
        TipoAcaoManual.CONFIRMAR_POSICAO_MANUAL,
        TipoAcaoManual.CONFIRMAR_BALANCA_VAZIA_MANUAL,
    }
)
_ETAPA_POR_COMANDO = {
    ComandoPedido.ABRIR: ("ABRINDO_SAIDA", "AGUARDANDO_BALANCA_VAZIA"),
    ComandoPedido.FECHAR: ("FECHANDO_SAIDA", "CONCLUIDA"),
}


def ocupa_balanca(operacao: Operacao) -> bool:
    if operacao.situacao is _S.AGUARDANDO_INTERVENCAO:
        return operacao.situacao_anterior in OCUPAM_BALANCA
    return operacao.situacao in OCUPAM_BALANCA


@dataclass(frozen=True)
class ImagemDecisao:
    """Imagem já codificada, salva na mesma transação da decisão (RN-022)."""

    conteudo: bytes
    origem: str
    capturada_em: datetime
    roi: tuple[int, int, int, int] | None


def _converter_situacao(
    registrada: SituacaoVeiculoRegistrada | None,
) -> SituacaoVeiculo | None:
    """`dominio` não importa `persistencia` (P-4): a orquestração converte."""
    if registrada is None:
        return None
    aberta = registrada.operacao_aberta
    return SituacaoVeiculo(
        registrada.veiculo_id,
        registrada.ativo,
        None
        if aberta is None
        else OperacaoAberta(aberta.pesagem_id, _S(aberta.situacao)),
        tuple(
            AgendamentoCandidato(
                a.agendamento_id,
                a.status,
                a.data_prevista,
                TipoOperacao(a.tipo_operacao),
                a.faixa_hora_inicio,
                a.motorista_ativo,
            )
            for a in registrada.agendamentos
        ),
    )


class Orquestracao:
    def __init__(
        self,
        configuracao: ConfiguracaoOrquestracao,
        banco: Banco,
        balanca: Balanca,
        cancela_entrada: Cancela,
        cancela_saida: Cancela,
        fonte_posicao: FontePosicao,
        reconhecedor: ReconhecedorPlaca,
        parametros_peso: ParametrosAceitacaoPeso,
        parametros_liquido: ParametrosPesoLiquido,
        parametros_placa: ParametrosLeituraPlaca,
        distribuidor: DistribuidorEventos,
        relogio: Callable[[], datetime],
        modo_balanca: ModoDispositivo,
        modo_cancelas: ModoDispositivo,
        modo_cameras: ModoDispositivo,
    ) -> None:
        self._configuracao = configuracao
        self._banco = banco
        # Público: o controle dos simuladores troca a instância (§6.9).
        self.balanca = balanca
        self._cancelas = {
            CancelaPedida.ENTRADA: cancela_entrada,
            CancelaPedida.SAIDA: cancela_saida,
        }
        self._fonte_posicao = fonte_posicao
        self._reconhecedor = reconhecedor
        self._parametros_peso = parametros_peso
        self._parametros_liquido = parametros_liquido
        self._parametros_placa = parametros_placa
        self._distribuidor = distribuidor
        self._relogio = relogio
        self._trava = asyncio.Lock()
        self._ponto_controle_id: int | None = None
        self._idade_maxima = timedelta(milliseconds=configuracao.idade_maxima_imagem_ms)
        self._tempo_limite = {
            **dict.fromkeys(
                AGUARDAM_POSICAO,
                timedelta(milliseconds=configuracao.tempo_limite_posicionamento_ms),
            ),
            **dict.fromkeys(
                POSICIONADAS,
                timedelta(milliseconds=configuracao.tempo_limite_pesagem_ms),
            ),
            **dict.fromkeys(
                AGUARDAM_BALANCA_VAZIA,
                timedelta(milliseconds=configuracao.tempo_limite_saida_balanca_ms),
            ),
        }
        # Identificação (§6.1): última decisão registrada e sua leitura.
        self._ultima_decisao: tuple[str | None, str, str | None] | None = None
        self._ultima_leitura_placa_id: int | None = None
        # Eventos que a spec 006 só registra: enviados quando o resultado muda.
        self._ultimo_registrado: dict[int, tuple[TipoEvento, str | None]] = {}
        # Gravações que falharam depois de um comando físico: só a gravação é repetida.
        self._gravacoes_pendentes: list[Callable[[], Awaitable[None]]] = []
        self._comandos_agendados: set[asyncio.Task[None]] = set()
        self._ultima_posicao: LeituraPosicao | None = None
        # Última leitura com imagem: evidência das confirmações manuais (RN-022).
        self._ultima_imagem_posicao: LeituraPosicao | None = None
        self._serie: deque[LeituraPeso] = deque(
            maxlen=parametros_peso.quantidade_leituras_estaveis
        )
        self._serie_de: tuple[int, int] | None = None
        self._ultimo_peso_publicado_em: datetime | None = None
        self._estado_balanca = EstadoBalanca(
            modo_balanca, "DESCONHECIDO", None, None, None, None
        )
        self._estado_cancelas = {
            cancela: EstadoCancelaConhecido(cancela, modo_cancelas, None, None, None)
            for cancela in CancelaPedida
        }
        self._estado_posicao = EstadoPosicao(modo_cameras, None, None, None)
        self._estado_identificacao = EstadoIdentificacao(modo_cameras, None, None)
        # Imagem mais recente analisada de cada fonte, em JPEG (spec 011).
        self._imagem_atual: dict[str, tuple[bytes, datetime]] = {}

    # ----------------------------------------------------------------- apoio

    async def _transacao[T](self, funcao: Callable[[Transacao], T]) -> T:
        def executar() -> T:
            with self._banco() as t:
                return funcao(t)

        return await asyncio.to_thread(executar)

    async def _abertas(self) -> list[OperacaoRegistrada]:
        return await self._transacao(lambda t: t.pesagens.listar_operacoes_abertas())

    def _hoje(self, agora: datetime) -> datetime:
        return agora.astimezone(self._configuracao.fuso_patio)

    def _publicar_cancela(
        self,
        cancela: CancelaPedida,
        estado: EstadoCancela,
        em: datetime,
        ultimo_comando: UltimoComandoCancela | None = None,
    ) -> None:
        atual = self._estado_cancelas[cancela]
        novo = replace(
            atual,
            estado=estado,
            estado_em=em,
            ultimo_comando=ultimo_comando or atual.ultimo_comando,
        )
        if novo != replace(atual, estado_em=em):
            self._distribuidor.publicar(EventoCancela(novo))
        self._estado_cancelas[cancela] = novo

    def imagem_atual(self, fonte: str) -> tuple[bytes, datetime] | None:
        """`fonte`: `identificacao` ou `posicao`; JPEG e instante de captura."""
        return self._imagem_atual.get(fonte)

    def estado_dispositivos(self) -> EstadoDispositivos:
        return EstadoDispositivos(
            self._estado_balanca,
            (
                self._estado_cancelas[CancelaPedida.ENTRADA],
                self._estado_cancelas[CancelaPedida.SAIDA],
            ),
            self._estado_posicao,
            self._estado_identificacao,
        )

    # --------------------------------------------------- aplicar e comandar

    async def _processar(
        self,
        pesagem_id: int,
        evento: EventoMaquina,
        *,
        responsavel_id: int | None = None,
        imagem: ImagemDecisao | None = None,
        motivo_dispositivo: str | None = None,
        antes: Callable[[Transacao], None] | None = None,
        comandar_depois: bool = False,
    ) -> ResultadoTransicao:
        """Aplica, grava e executa a ação pedida. Levanta `ErroPersistencia` sem efeito.

        `comandar_depois`: devolve com a transição gravada e executa o comando numa
        tarefa, sob a trava (spec 009 §6.3: o 200 significa só "gravada").
        """

        def gravar(
            t: Transacao,
        ) -> tuple[ResultadoTransicao, OperacaoRegistrada | None]:
            if antes is not None:
                antes(t)
            registrada = t.pesagens.obter_operacao(pesagem_id)
            agora = self._relogio()
            resultado = aplicar_evento(
                registrada.operacao, evento, self._parametros_liquido
            )
            if not isinstance(resultado, TransicaoAplicada):
                t.pesagens.registrar_evento(
                    pesagem_id, resultado, responsavel_id, agora, motivo_dispositivo
                )
                return resultado, None
            imagem_id = (
                None
                if imagem is None
                else t.imagens.salvar(
                    imagem.conteudo, imagem.origem, imagem.capturada_em, imagem.roi
                )
            )
            aguarda = (
                isinstance(evento, AcaoManual)
                and evento.tipo is TipoAcaoManual.CANCELAR
                and ocupa_balanca(registrada.operacao)
            )
            t.pesagens.gravar_transicao(
                pesagem_id,
                registrada.operacao.versao,
                resultado.operacao,
                evento,
                responsavel_id,
                self._hoje(agora).date(),
                agora,
                aguarda_liberacao_balanca=aguarda,
                imagem_id=imagem_id,
            )
            nova = replace(
                registrada,
                operacao=resultado.operacao,
                situacao_desde=agora,
                aguarda_liberacao_balanca=registrada.aguarda_liberacao_balanca
                or aguarda,
            )
            return resultado, nova

        resultado, nova = await self._transacao(gravar)
        if nova is None:
            self._ultimo_registrado[pesagem_id] = (
                evento.tipo
                if isinstance(evento, EventoAutomatico)
                else _E.TEMPO_ESGOTADO,
                motivo_dispositivo,
            )
            return resultado
        self._ultimo_registrado.pop(pesagem_id, None)
        self._distribuidor.publicar(EventoOperacao(nova))
        if (
            isinstance(evento, AcaoManual)
            and evento.tipo is TipoAcaoManual.CANCELAR
            and nova.aguarda_liberacao_balanca
        ):
            self._distribuidor.publicar(
                EventoLiberacaoCaminhao(
                    LiberacaoCaminhao(
                        pesagem_id,
                        "PENDENTE",
                        None,
                        None,
                        None,
                        None,
                        nova.situacao_desde,
                    )
                )
            )
        assert isinstance(resultado, TransicaoAplicada)
        if resultado.acao_pedida is not None:
            if comandar_depois:
                self._agendar_comando(nova, resultado.acao_pedida)
            else:
                await self._comandar(nova, resultado.acao_pedida)
        return resultado

    def _agendar_comando(
        self, registrada: OperacaoRegistrada, acao: AcaoPedida
    ) -> None:
        async def comandar() -> None:
            async with self._trava:
                # Outra ação pode ter passado antes (ex.: CANCELAR): só comanda se a
                # operação ainda for exatamente a gravada (AGENTS §7.1.3).
                atual = await self._transacao(
                    lambda t: t.pesagens.obter_operacao(registrada.pesagem_id)
                )
                if atual.operacao != registrada.operacao:
                    registro.info(
                        "comando da pesagem %s não enviado: a operação mudou antes",
                        registrada.pesagem_id,
                    )
                    return
                await self._comandar(registrada, acao)

        tarefa = asyncio.create_task(comandar())
        self._comandos_agendados.add(tarefa)
        tarefa.add_done_callback(self._comandos_agendados.discard)

    async def aguardar_comandos_agendados(self) -> None:
        """Espera os comandos das ações manuais terminarem (testes e encerramento)."""
        while self._comandos_agendados:
            await asyncio.gather(*self._comandos_agendados)

    async def _processar_se_mudou(
        self, pesagem_id: int, tipo: TipoEvento, motivo_dispositivo: str | None = None
    ) -> None:
        """Eventos que a spec 006 só registra não entram na auditoria a cada ciclo."""
        if self._ultimo_registrado.get(pesagem_id) == (tipo, motivo_dispositivo):
            return
        await self._processar_ciclo(
            pesagem_id, EventoAutomatico(tipo), motivo_dispositivo=motivo_dispositivo
        )

    async def _processar_ciclo(
        self,
        pesagem_id: int,
        evento: EventoMaquina,
        *,
        imagem: ImagemDecisao | None = None,
        motivo_dispositivo: str | None = None,
    ) -> None:
        """Nos ciclos, uma falha de gravação só é registrada: o próximo ciclo reavalia."""
        try:
            await self._processar(
                pesagem_id, evento, imagem=imagem, motivo_dispositivo=motivo_dispositivo
            )
        except ErroConflitoVersao:
            registro.info(
                "versão mudou na pesagem %s; reavaliando no próximo ciclo", pesagem_id
            )
        except ErroPersistencia as erro:
            registro.error(
                "gravação falhou na pesagem %s: %s", pesagem_id, type(erro).__name__
            )

    async def _comandar(self, registrada: OperacaoRegistrada, acao: AcaoPedida) -> None:
        """Executa a ação pedida e aplica o resultado (RN-007). A situação já foi gravada."""
        pesagem_id = registrada.pesagem_id
        resultado = await self._enviar_comando(acao, pesagem_id)
        evento = EventoAutomatico(_EVENTO_CANCELA[resultado.resultado])
        em = self._relogio()

        def registrar(t: Transacao) -> None:
            t.pesagens.registrar_comando_cancela(
                pesagem_id,
                acao.cancela,
                acao.comando,
                resultado.resultado,
                resultado.tentativas,
                em,
            )

        async def gravar() -> None:
            await self._processar(pesagem_id, evento, antes=registrar)

        try:
            await gravar()
        except ErroPersistencia as erro:
            # O comando já foi enviado: só a gravação é repetida, nunca o comando.
            registro.error(
                "resultado da cancela não gravado (%s); repetindo depois",
                type(erro).__name__,
            )
            self._gravacoes_pendentes.append(gravar)

    async def _enviar_comando(
        self, acao: AcaoPedida, pesagem_id: int
    ) -> ResultadoComandoCancela:
        cancela = self._cancelas[acao.cancela]
        resultado = await (
            cancela.abrir() if acao.comando is ComandoPedido.ABRIR else cancela.fechar()
        )
        em = self._relogio()
        # Sem confirmação, a posição é desconhecida (RN-007), não a pedida.
        estado = (
            _POSICAO_PEDIDA[acao.comando]
            if resultado.resultado is ResultadoComando.CONFIRMADO
            else EstadoCancela.DESCONHECIDO
        )
        ultimo = UltimoComandoCancela(
            acao.comando, resultado.resultado, resultado.tentativas, em, pesagem_id
        )
        self._publicar_cancela(acao.cancela, estado, em, ultimo)
        return resultado

    async def _repetir_gravacoes_pendentes(self) -> None:
        pendentes, self._gravacoes_pendentes = self._gravacoes_pendentes, []
        for gravar in pendentes:
            try:
                await gravar()
            except ErroPersistencia:
                self._gravacoes_pendentes.append(gravar)

    # -------------------------------------------------------------- retomada

    async def retomar(self) -> None:
        """Spec 006 §7.2: lê o sensor antes de qualquer comando; nada às cegas."""
        self._ponto_controle_id = await self._transacao(
            lambda t: t.pontos_controle.obter_unico()
        )
        async with self._trava:
            for registrada in await self._abertas():
                acao = COMANDO_PENDENTE.get(registrada.operacao.situacao)
                if acao is None:
                    continue
                estado = await self._cancelas[acao.cancela].consultar_estado()
                self._publicar_cancela(acao.cancela, estado, self._relogio())
                if estado is _POSICAO_PEDIDA[acao.comando]:
                    await self._processar_ciclo(
                        registrada.pesagem_id, EventoAutomatico(_E.CANCELA_CONFIRMADA)
                    )
                elif estado is EstadoCancela.DESCONHECIDO:
                    await self._processar_ciclo(
                        registrada.pesagem_id,
                        EventoAutomatico(_E.REINICIO_INCONCLUSIVO),
                    )
                else:
                    await self._comandar(registrada, acao)
            for liberacao in await self._liberacoes():
                if liberacao.etapa in ("ABRINDO_SAIDA", "FECHANDO_SAIDA"):
                    await self._retomar_liberacao(liberacao)

    async def executar(self) -> None:
        """Roda os ciclos até ser cancelado. Chamar depois de `retomar()`."""
        intervalo = self._configuracao.intervalo_analise_ms / 1000
        intervalo_balanca = self._configuracao.intervalo_leitura_balanca_ms / 1000

        async def repetir(ciclo: Callable[[], Awaitable[None]], espera: float) -> None:
            while True:
                try:
                    await ciclo()
                except ErroPersistencia as erro:
                    # Banco fora do ar não para a orquestração: nada avança até voltar.
                    registro.error("%s: %s", ciclo.__name__, type(erro).__name__)
                await asyncio.sleep(espera)

        async with asyncio.TaskGroup() as grupo:
            grupo.create_task(repetir(self.ciclo_identificacao, intervalo))
            grupo.create_task(repetir(self.ciclo_posicao, intervalo))
            grupo.create_task(repetir(self.ciclo_fila, intervalo))
            grupo.create_task(repetir(self.ciclo_balanca, intervalo_balanca))

    # --------------------------------------------------------- identificação

    async def ciclo_identificacao(self) -> None:
        reconhecido = await self._reconhecedor()
        agora = self._relogio()
        if (
            isinstance(reconhecido, FalhaImagem)
            and reconhecido.motivo is MotivoFalhaImagem.SEM_IMAGEM
        ):
            return
        candidatos: list[tuple[Roi, CandidatoPlaca]] = []
        if isinstance(reconhecido, FalhaImagem):
            leitura: LeituraIdentificacao = FalhaIdentificacao.FALHA_IMAGEM
            origem, capturada_em = reconhecido.origem or "", agora
        elif isinstance(reconhecido, FalhaLeitor):
            leitura = FalhaIdentificacao.FALHA_LEITOR
            origem, capturada_em = reconhecido.origem, agora
        else:
            candidatos = [
                (leitura_roi.roi, CandidatoPlaca(texto.texto, texto.confianca))
                for leitura_roi in reconhecido.leituras
                for texto in leitura_roi.textos
            ]
            leitura = selecionar_placa(
                [c for _, c in candidatos], self._parametros_placa
            )
            origem, capturada_em = reconhecido.origem, reconhecido.capturada_em
        self._publicar_identificacao(
            leitura.name if isinstance(leitura, FalhaIdentificacao) else "OK", agora
        )
        selecionada = leitura if isinstance(leitura, PlacaSelecionada) else None
        chave = selecionada.placa.chave_comparacao if selecionada else None
        # Codifica antes de decidir: sem imagem gravável não há autorização (§6.1, P-5).
        conteudo: bytes | None = None
        if isinstance(reconhecido, LeituraPlaca):
            conteudo = codificar_jpeg(reconhecido.pixels)
            if conteudo is not None:
                self._imagem_atual["identificacao"] = (conteudo, capturada_em)
            if not candidatos:
                conteudo = None
            elif conteudo is None:
                leitura, selecionada, chave = (
                    FalhaIdentificacao.FALHA_IMAGEM,
                    None,
                    None,
                )

        def decidir_e_gravar(
            t: Transacao,
        ) -> (
            tuple[
                tuple[str | None, str, str | None],
                int,
                NovaLeituraPlaca,
                OperacaoRegistrada | None,
            ]
            | None
        ):
            situacao = (
                _converter_situacao(t.veiculos.buscar_situacao_por_chave(chave))
                if chave
                else None
            )
            decisao = decidir_autorizacao(
                leitura, situacao, agora, self._configuracao.fuso_patio
            )
            nome = type(decisao).__name__
            decisao_nome = {
                "EntradaAutorizada": "AUTORIZADA",
                "RetornoAceito": "RETORNO_ACEITO",
            }.get(nome, "NAO_AUTORIZADA")
            motivo = (
                decisao.motivo if isinstance(decisao, EntradaNaoAutorizada) else None
            )
            assinatura = (chave, decisao_nome, motivo)
            # Só uma não autorização se repete: autorizar cria ou move a operação, e
            # o ciclo seguinte já decide diferente (ex.: OPERACAO_JA_ABERTA). Assim o
            # mesmo caminhão entra de novo depois de um cancelamento (RN-009).
            if assinatura == self._ultima_decisao and isinstance(
                decisao, EntradaNaoAutorizada
            ):
                return None
            imagem_id = None
            if conteudo is not None:
                roi = candidatos[selecionada.indice][0] if selecionada else None
                imagem_id = t.imagens.salvar(
                    conteudo,
                    origem,
                    capturada_em,
                    None if roi is None else (roi.x, roi.y, roi.largura, roi.altura),
                )
            nova = NovaLeituraPlaca(
                origem=origem,
                capturada_em=capturada_em,
                decidida_em=agora,
                decisao=decisao_nome,
                leituras=_leituras_json(reconhecido),
                agendamento_id=decisao.agendamento_id
                if isinstance(decisao, EntradaAutorizada)
                else None,
                motivo=motivo,
                placa_lida=candidatos[selecionada.indice][1].placa_lida
                if selecionada
                else None,
                placa_normalizada=selecionada.placa.placa_normalizada
                if selecionada
                else None,
                formato=selecionada.placa.formato if selecionada else None,
                chave_comparacao=chave,
                correcoes=[
                    {"posicao": c.posicao, "lido": c.lido, "corrigido": c.corrigido}
                    for c in selecionada.placa.correcoes
                ]
                if selecionada
                else None,
                confianca=selecionada.confianca if selecionada else None,
                imagem_id=imagem_id,
            )
            operacao: OperacaoRegistrada | None = None
            if isinstance(decisao, EntradaAutorizada):
                leitura_id = t.leituras_placa.registrar(nova)
                assert self._ponto_controle_id is not None, "chame retomar() antes"
                operacao = t.pesagens.criar_operacao(
                    decisao.agendamento_id,
                    self._ponto_controle_id,
                    agora,
                    leitura_id,
                    veiculo_id=decisao.veiculo_id,
                )
                nova = replace(nova, pesagem_id=operacao.pesagem_id)
            elif isinstance(decisao, RetornoAceito):
                leitura_id = t.leituras_placa.registrar(nova)
                registrada = t.pesagens.obter_operacao(decisao.pesagem_id)
                evento = EventoAutomatico(_E.PLACA_RETORNO_ACEITA)
                resultado = aplicar_evento(
                    registrada.operacao, evento, self._parametros_liquido
                )
                if isinstance(resultado, TransicaoAplicada):
                    t.pesagens.gravar_transicao(
                        decisao.pesagem_id,
                        registrada.operacao.versao,
                        resultado.operacao,
                        evento,
                        None,
                        self._hoje(agora).date(),
                        agora,
                        leitura_placa_id=leitura_id,
                    )
                    # A ligação com a pesagem é feita pelo `gravar_transicao`, uma só vez.
                    nova = replace(nova, pesagem_id=decisao.pesagem_id)
                    operacao = replace(
                        registrada, operacao=resultado.operacao, situacao_desde=agora
                    )
                else:
                    t.pesagens.registrar_evento(
                        decisao.pesagem_id,
                        resultado,
                        None,
                        agora,
                        leitura_placa_id=leitura_id,
                    )
            else:
                leitura_id = t.leituras_placa.registrar(nova)
            return assinatura, leitura_id, nova, operacao

        async with self._trava:
            try:
                gravado = await self._transacao(decidir_e_gravar)
            except ErroPersistencia as erro:
                # Corrida com cancelamento ou outra entrada: o próximo ciclo decide de novo.
                registro.error(
                    "decisão de entrada não gravada: %s", type(erro).__name__
                )
                return
            if gravado is None:
                return
            assinatura, leitura_id, nova, operacao = gravado
            self._ultima_decisao = assinatura
            self._ultima_leitura_placa_id = leitura_id
            self._distribuidor.publicar(EventoLeituraPlaca(leitura_id, nova))
            if operacao is not None:
                self._distribuidor.publicar(EventoOperacao(operacao))

    def _publicar_identificacao(self, resultado: str, agora: datetime) -> None:
        novo = replace(
            self._estado_identificacao, resultado=resultado, analisada_em=agora
        )
        if novo.resultado != self._estado_identificacao.resultado:
            self._distribuidor.publicar(EventoIdentificacao(novo))
        self._estado_identificacao = novo

    # ------------------------------------------------------------------ fila

    async def ciclo_fila(self) -> None:
        """Spec 006 §6.3: uma operação por vez, por ordem de chegada (RN-019)."""
        async with self._trava:
            await self._repetir_gravacoes_pendentes()
            abertas = await self._abertas()
            fila = [op for op in abertas if op.operacao.situacao in AGUARDAM_BALANCA]
            if not fila or any(ocupa_balanca(op.operacao) for op in abertas):
                return
            if await self._transacao(
                lambda t: t.pesagens.listar_aguardando_liberacao_balanca()
            ):
                return
            if not self._balanca_vazia(self._relogio()):
                return
            for cancela in CancelaPedida:
                estado = await self._cancelas[cancela].consultar_estado()
                self._publicar_cancela(cancela, estado, self._relogio())
                if estado is not EstadoCancela.FECHADA:
                    return
            primeira = min(fila, key=lambda op: (op.situacao_desde, op.pesagem_id))
            await self._processar_ciclo(
                primeira.pesagem_id, EventoAutomatico(_E.BALANCA_DISPONIVEL)
            )

    def _balanca_vazia(self, agora: datetime) -> bool:
        posicao = self._ultima_posicao
        return (
            posicao is not None
            and posicao.resultado is ResultadoPosicao.AUSENTE
            and agora - posicao.capturada_em <= self._idade_maxima
        )

    # --------------------------------------------------------------- posição

    async def ciclo_posicao(self) -> None:
        abertas = await self._abertas()
        liberacoes = await self._liberacoes()
        ocupante = next(
            (op for op in abertas if op.operacao.situacao in ESPERAM_CAMERA), None
        )
        aguardando_vazia = [
            lib for lib in liberacoes if lib.etapa == "AGUARDANDO_BALANCA_VAZIA"
        ]
        precisa = (
            ocupante is not None
            or aguardando_vazia
            or any(op.operacao.situacao in AGUARDAM_BALANCA for op in abertas)
        )
        resultado: ResultadoPosicao | None = None
        leitura: LeituraPosicao | None = None
        if precisa:
            leitura = await self._fonte_posicao.analisar_posicao()
            agora = self._relogio()
            resultado = leitura.resultado
            if agora - leitura.capturada_em > self._idade_maxima:
                resultado = ResultadoPosicao.INCONCLUSIVA
            leitura = LeituraPosicao(resultado, leitura.capturada_em, leitura.imagem)
            self._ultima_posicao = leitura
            if leitura.imagem is not None:
                self._ultima_imagem_posicao = leitura
            if (
                leitura.imagem is not None
                and (jpeg := codificar_jpeg(leitura.imagem.pixels)) is not None
            ):
                self._imagem_atual["posicao"] = (jpeg, leitura.capturada_em)
            novo = EstadoPosicao(
                self._estado_posicao.modo, resultado, leitura.capturada_em, agora
            )
            if novo.resultado != self._estado_posicao.resultado:
                self._distribuidor.publicar(EventoPosicao(novo))
            self._estado_posicao = novo
        async with self._trava:
            if ocupante is not None and leitura is not None and resultado is not None:
                await self._aplicar_posicao(ocupante, leitura, resultado)
            for liberacao in aguardando_vazia:
                try:
                    await self._conduzir_liberacao(liberacao, resultado)
                except ErroPersistencia as erro:
                    registro.error(
                        "liberação da pesagem %s não gravada: %s",
                        liberacao.pesagem_id,
                        type(erro).__name__,
                    )
            # Relida sob a trava: a fotografia de antes pode ter mudado neste ciclo
            # (ex.: ENTRADA_LIBERADA → POSICIONADA_INICIAL), e o tempo-limite vale
            # para a situação atual, contado de `situacao_desde`.
            agora = self._relogio()
            for op in await self._abertas():
                limite = self._tempo_limite.get(op.operacao.situacao)
                if limite is not None and agora - op.situacao_desde >= limite:
                    await self._processar_ciclo(
                        op.pesagem_id, EventoAutomatico(_E.TEMPO_ESGOTADO)
                    )

    async def _conduzir_liberacao(
        self, liberacao: LiberacaoCaminhao, resultado: ResultadoPosicao | None
    ) -> None:
        if resultado is ResultadoPosicao.AUSENTE:
            await self._comandar_liberacao(liberacao, ComandoPedido.FECHAR)
        elif (
            self._relogio() - liberacao.atualizada_em
            >= self._tempo_limite[_S.SAIDA_LIBERADA]
        ):
            await self._atualizar_liberacao(liberacao, "FALHOU", "TEMPO_ESGOTADO")

    async def _aplicar_posicao(
        self,
        ocupante: OperacaoRegistrada,
        leitura: LeituraPosicao,
        resultado: ResultadoPosicao,
    ) -> None:
        tipo = _EVENTO_POSICAO[resultado]
        situacao = ocupante.operacao.situacao
        avanca = (tipo is _E.POSICAO_CONFIRMADA and situacao in AGUARDAM_POSICAO) or (
            tipo is _E.POSICAO_AUSENTE and situacao in AGUARDAM_BALANCA_VAZIA
        )
        if not avanca:
            # `POSICAO_AUSENTE` em `POSICIONADA_*` para a operação (spec 006 §6): sempre enviado.
            if tipo is _E.POSICAO_AUSENTE and situacao in POSICIONADAS:
                await self._processar_ciclo(ocupante.pesagem_id, EventoAutomatico(tipo))
            else:
                await self._processar_se_mudou(ocupante.pesagem_id, tipo)
            return
        imagem = None
        if tipo is _E.POSICAO_CONFIRMADA:
            imagem = self._imagem_posicao(leitura)
            if imagem is None:
                await self._processar_se_mudou(
                    ocupante.pesagem_id, _E.POSICAO_INCONCLUSIVA
                )
                return
        await self._processar_ciclo(
            ocupante.pesagem_id, EventoAutomatico(tipo), imagem=imagem
        )

    def _imagem_posicao(self, leitura: LeituraPosicao | None) -> ImagemDecisao | None:
        if leitura is None or leitura.imagem is None:
            return None
        conteudo = codificar_jpeg(leitura.imagem.pixels)
        if conteudo is None:
            return None
        return ImagemDecisao(
            conteudo, leitura.imagem.origem, leitura.capturada_em, None
        )

    # --------------------------------------------------------------- balança

    async def ciclo_balanca(self) -> None:
        """Lida só em `POSICIONADA_*` (§6.4, P-1). Nunca inventa nem ajusta peso."""
        abertas = await self._abertas()
        posicionada = next(
            (op for op in abertas if op.operacao.situacao in POSICIONADAS), None
        )
        if posicionada is None:
            self._serie.clear()
            self._serie_de = None
            return
        chave = (posicionada.pesagem_id, posicionada.operacao.versao)
        if chave != self._serie_de:
            self._serie.clear()
            self._serie_de = chave
        leitura = await self.balanca.ler_peso()
        agora = self._relogio()
        if isinstance(leitura, FalhaBalanca):
            self._serie.clear()
            self._publicar_balanca(
                replace(
                    self._estado_balanca,
                    comunicacao="FALHA",
                    motivo_falha=leitura.motivo,
                    comunicacao_em=agora,
                )
            )
            async with self._trava:
                await self._processar_se_mudou(
                    posicionada.pesagem_id, _E.BALANCA_FALHA, leitura.motivo
                )
            return
        leitura_peso = LeituraPeso(leitura.peso_kg, leitura.lida_em)
        self._serie.append(leitura_peso)
        intervalo = timedelta(milliseconds=self._configuracao.intervalo_minimo_peso_ms)
        if (
            self._ultimo_peso_publicado_em is None
            or agora - self._ultimo_peso_publicado_em >= intervalo
        ):
            self._distribuidor.publicar(
                EventoPesoLido(leitura.peso_kg, leitura.lida_em)
            )
            self._ultimo_peso_publicado_em = agora
        avaliacao = validar_leituras_peso(list(self._serie), self._parametros_peso)
        motivo_rejeicao = (
            None if isinstance(avaliacao, PesoValidado) else avaliacao.motivo
        )
        self._publicar_balanca(
            EstadoBalanca(
                self._estado_balanca.modo,
                "OK",
                None,
                agora,
                leitura_peso,
                AvaliacaoPeso(motivo_rejeicao is None, motivo_rejeicao, agora),
            )
        )
        async with self._trava:
            if isinstance(avaliacao, PesoValidado):
                await self._processar_ciclo(
                    posicionada.pesagem_id,
                    PesoAceito(avaliacao.peso_kg, avaliacao.lida_em),
                )
                self._serie.clear()
            elif avaliacao.motivo is not MotivoRejeicaoPeso.LEITURAS_INSUFICIENTES:
                await self._processar_se_mudou(
                    posicionada.pesagem_id, _E.PESO_REJEITADO, avaliacao.motivo
                )

    def _publicar_balanca(self, novo: EstadoBalanca) -> None:
        atual = self._estado_balanca
        if (
            novo.comunicacao,
            novo.motivo_falha,
            novo.avaliacao_peso and novo.avaliacao_peso.motivo_rejeicao,
        ) != (
            atual.comunicacao,
            atual.motivo_falha,
            atual.avaliacao_peso and atual.avaliacao_peso.motivo_rejeicao,
        ):
            self._distribuidor.publicar(EventoBalanca(novo))
        self._estado_balanca = novo

    # ---------------------------------------------------------- ações manuais

    async def aplicar_acao_manual(
        self, pesagem_id: int, versao_vista: int, acao: AcaoManual, responsavel_id: int
    ) -> ResultadoTransicao:
        """Spec 006 §5.3; versão vista antes da máquina (ADR-0005 §4.5)."""
        async with self._trava:
            registrada = await self._transacao(
                lambda t: t.pesagens.obter_operacao(pesagem_id)
            )
            if registrada.operacao.versao != versao_vista:
                raise ErroConflitoVersao(str(pesagem_id))
            imagem = (
                self._imagem_posicao(self._ultima_imagem_posicao)
                if acao.tipo in _CONFIRMACOES_COM_IMAGEM
                else None
            )
            return await self._processar(
                pesagem_id,
                acao,
                responsavel_id=responsavel_id,
                imagem=imagem,
                comandar_depois=True,
            )

    async def liberar_entrada_manual(
        self,
        leitura_placa_id: int,
        agendamento_id: int,
        responsavel_id: int,
        motivo: str,
    ) -> OperacaoRegistrada:
        """RN-016 (§6.7): só substitui identificação e horário; o resto continua exigido."""
        async with self._trava:
            if (
                leitura_placa_id != self._ultima_leitura_placa_id
                or self._ultima_decisao is None
            ):
                raise ErroLiberacaoEntrada("LEITURA_DESATUALIZADA")
            motivo_leitura = self._ultima_decisao[2]
            agora = self._relogio()

            def executar(t: Transacao) -> OperacaoRegistrada:
                leitura = t.leituras_placa.buscar(leitura_placa_id)
                if (
                    leitura is None
                    or leitura.decisao != "NAO_AUTORIZADA"
                    or leitura.pesagem_id is not None
                ):
                    raise ErroLiberacaoEntrada("LEITURA_NAO_LIBERAVEL")
                if (
                    motivo_leitura is None
                    or MotivoNaoAutorizacao(motivo_leitura) not in MOTIVOS_SUBSTITUIVEIS
                ):
                    raise ErroLiberacaoEntrada("MOTIVO_NAO_SUBSTITUIVEL")
                situacao = _converter_situacao(
                    t.veiculos.buscar_situacao_por_agendamento(agendamento_id)
                )
                decisao = decidir_liberacao_manual(
                    situacao, agendamento_id, agora, self._configuracao.fuso_patio
                )
                if isinstance(decisao, EntradaNaoAutorizada):
                    raise ErroLiberacaoEntrada(decisao.motivo)
                assert self._ponto_controle_id is not None, "chame retomar() antes"
                return t.pesagens.criar_operacao(
                    agendamento_id,
                    self._ponto_controle_id,
                    agora,
                    leitura_placa_id,
                    True,
                    responsavel_id,
                    motivo,
                    veiculo_id=decisao.veiculo_id,
                )

            operacao = await self._transacao(executar)
            self._distribuidor.publicar(EventoOperacao(operacao))
            return operacao

    # ------------------------------------------ caminhão de operação cancelada

    async def _liberacoes(self) -> list[LiberacaoCaminhao]:
        def buscar(t: Transacao) -> list[LiberacaoCaminhao]:
            liberacoes = []
            for op in t.pesagens.listar_aguardando_liberacao_balanca():
                liberacao = t.pesagens.buscar_liberacao_caminhao(op.pesagem_id)
                if liberacao is not None:
                    liberacoes.append(liberacao)
            return liberacoes

        return await self._transacao(buscar)

    async def liberar_caminhao_cancelado(
        self, pesagem_id: int, responsavel_id: int, motivo: str
    ) -> LiberacaoCaminhao:
        """RN-020 (§6.8). `ErroLiberacaoIndisponivel` da persistência se já em curso."""
        async with self._trava:
            agora = self._relogio()

            def pedir(t: Transacao) -> None:
                if not t.pesagens.obter_operacao(pesagem_id).aguarda_liberacao_balanca:
                    raise ErroOperacaoNaoOcupaBalanca(str(pesagem_id))
                t.pesagens.pedir_liberacao_caminhao(
                    pesagem_id, responsavel_id, motivo, agora
                )

            await self._transacao(pedir)
            liberacao = LiberacaoCaminhao(
                pesagem_id, "ABRINDO_SAIDA", None, responsavel_id, motivo, agora, agora
            )
            self._distribuidor.publicar(EventoLiberacaoCaminhao(liberacao))
            return await self._comandar_liberacao(liberacao, ComandoPedido.ABRIR)

    async def _comandar_liberacao(
        self, liberacao: LiberacaoCaminhao, comando: ComandoPedido
    ) -> LiberacaoCaminhao:
        acao = AcaoPedida(comando, CancelaPedida.SAIDA)
        if liberacao.etapa != _ETAPA_POR_COMANDO[comando][0]:
            # A etapa é gravada antes do comando, como a situação (spec 006 §7.2).
            liberacao = await self._atualizar_liberacao(
                liberacao, _ETAPA_POR_COMANDO[comando][0]
            )
        resultado = await self._enviar_comando(acao, liberacao.pesagem_id)
        em = self._relogio()
        etapa_sucesso = _ETAPA_POR_COMANDO[comando][1]
        etapa = (
            etapa_sucesso
            if resultado.resultado is ResultadoComando.CONFIRMADO
            else "FALHOU"
        )
        motivo_falha = _MOTIVO_FALHA_LIBERACAO.get(resultado.resultado)

        def registrar(t: Transacao) -> None:
            t.pesagens.registrar_comando_cancela(
                liberacao.pesagem_id,
                acao.cancela,
                acao.comando,
                resultado.resultado,
                resultado.tentativas,
                em,
                liberacao.pedido_por,
                liberacao.motivo,
            )

        return await self._gravar_resultado_liberacao(
            liberacao, etapa, motivo_falha, registrar
        )

    async def _atualizar_liberacao(
        self,
        liberacao: LiberacaoCaminhao,
        etapa: str,
        motivo_falha: str | None = None,
        antes: Callable[[Transacao], None] | None = None,
    ) -> LiberacaoCaminhao:
        """Grava e publica a etapa. Levanta `ErroPersistencia`: antes de um comando,
        isso impede o comando (spec 015 §6.8)."""
        em = self._relogio()
        nova = replace(
            liberacao, etapa=etapa, motivo_falha=motivo_falha, atualizada_em=em
        )

        def executar(t: Transacao) -> None:
            if antes is not None:
                antes(t)
            t.pesagens.atualizar_liberacao_caminhao(
                liberacao.pesagem_id, etapa, em, motivo_falha
            )

        await self._transacao(executar)
        self._distribuidor.publicar(EventoLiberacaoCaminhao(nova))
        return nova

    async def _gravar_resultado_liberacao(
        self,
        liberacao: LiberacaoCaminhao,
        etapa: str,
        motivo_falha: str | None,
        antes: Callable[[Transacao], None],
    ) -> LiberacaoCaminhao:
        """Depois de um comando já enviado: a gravação é repetida, nunca o comando."""

        async def gravar() -> None:
            await self._atualizar_liberacao(liberacao, etapa, motivo_falha, antes)

        try:
            return await self._atualizar_liberacao(
                liberacao, etapa, motivo_falha, antes
            )
        except ErroPersistencia as erro:
            registro.error(
                "resultado da liberação não gravado (%s); repetindo depois",
                type(erro).__name__,
            )
            self._gravacoes_pendentes.append(gravar)
            return replace(
                liberacao,
                etapa=etapa,
                motivo_falha=motivo_falha,
                atualizada_em=self._relogio(),
            )

    async def _retomar_liberacao(self, liberacao: LiberacaoCaminhao) -> None:
        """Mesma regra da §7.1 para a saída: o sensor decide, nunca o reenvio cego."""
        comando = (
            ComandoPedido.ABRIR
            if liberacao.etapa == "ABRINDO_SAIDA"
            else ComandoPedido.FECHAR
        )
        estado = await self._cancelas[CancelaPedida.SAIDA].consultar_estado()
        self._publicar_cancela(CancelaPedida.SAIDA, estado, self._relogio())
        if estado is _POSICAO_PEDIDA[comando]:
            await self._atualizar_liberacao(liberacao, _ETAPA_POR_COMANDO[comando][1])
        elif estado is EstadoCancela.DESCONHECIDO:
            await self._atualizar_liberacao(
                liberacao, "FALHOU", "CANCELA_SEM_CONFIRMACAO"
            )
        else:
            await self._comandar_liberacao(liberacao, comando)


def _leituras_json(reconhecido: LeituraPlaca | FalhaImagem | FalhaLeitor) -> Json:
    if not isinstance(reconhecido, LeituraPlaca):
        return []
    return [
        {
            "roi": {
                "x": r.roi.x,
                "y": r.roi.y,
                "largura": r.roi.largura,
                "altura": r.roi.altura,
            },
            "textos": [
                {"texto": t.texto, "confianca": str(t.confianca)} for t in r.textos
            ],
        }
        for r in reconhecido.leituras
    ]
