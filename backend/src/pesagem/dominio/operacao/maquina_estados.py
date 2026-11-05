"""Máquina de estados da operação (spec 006; RN-010, RN-012).

Regra pura: não executa comandos nem grava nada. Toda situação com comando
pendente tem exatamente um; a orquestração grava a situação antes de comandar,
o que permite retomar sem reenviar às cegas (§7.2). O que não está nas tabelas
é rejeitado e nunca corrigido: na dúvida, a operação não avança (RNF-009).
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pesagem.dominio.pesagem.calculo_peso import (
    ClassificacaoPesoLiquido,
    ParametrosPesoLiquido,
    TipoOperacao,
    calcular_peso_liquido,
)


class SituacaoOperacao(StrEnum):
    AGUARDANDO_BALANCA_INICIAL = "AGUARDANDO_BALANCA_INICIAL"
    AUTORIZADA = "AUTORIZADA"
    ENTRADA_LIBERADA = "ENTRADA_LIBERADA"
    FECHANDO_ENTRADA = "FECHANDO_ENTRADA"
    POSICIONADA_INICIAL = "POSICIONADA_INICIAL"
    PESO_INICIAL_OK = "PESO_INICIAL_OK"
    SAIDA_INICIAL_LIBERADA = "SAIDA_INICIAL_LIBERADA"
    FECHANDO_SAIDA_INICIAL = "FECHANDO_SAIDA_INICIAL"
    EM_CARGA_DESCARGA = "EM_CARGA_DESCARGA"
    AGUARDANDO_BALANCA_FINAL = "AGUARDANDO_BALANCA_FINAL"
    RETORNO_AUTORIZADO = "RETORNO_AUTORIZADO"
    RETORNO_LIBERADO = "RETORNO_LIBERADO"
    FECHANDO_ENTRADA_RETORNO = "FECHANDO_ENTRADA_RETORNO"
    POSICIONADA_FINAL = "POSICIONADA_FINAL"
    PESO_FINAL_OK = "PESO_FINAL_OK"
    SAIDA_LIBERADA = "SAIDA_LIBERADA"
    FECHANDO_SAIDA = "FECHANDO_SAIDA"
    AGUARDANDO_INTERVENCAO = "AGUARDANDO_INTERVENCAO"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class TipoEvento(StrEnum):
    BALANCA_DISPONIVEL = "BALANCA_DISPONIVEL"
    PLACA_RETORNO_ACEITA = "PLACA_RETORNO_ACEITA"
    CANCELA_CONFIRMADA = "CANCELA_CONFIRMADA"
    CANCELA_FALHA = "CANCELA_FALHA"
    CANCELA_SEM_CONFIRMACAO = "CANCELA_SEM_CONFIRMACAO"
    POSICAO_CONFIRMADA = "POSICAO_CONFIRMADA"
    POSICAO_AUSENTE = "POSICAO_AUSENTE"
    POSICAO_INCONCLUSIVA = "POSICAO_INCONCLUSIVA"
    PESO_REJEITADO = "PESO_REJEITADO"
    BALANCA_FALHA = "BALANCA_FALHA"
    TEMPO_ESGOTADO = "TEMPO_ESGOTADO"
    REINICIO_INCONCLUSIVO = "REINICIO_INCONCLUSIVO"


class TipoAcaoManual(StrEnum):
    TENTAR_NOVAMENTE = "TENTAR_NOVAMENTE"
    CONFIRMAR_POSICAO_MANUAL = "CONFIRMAR_POSICAO_MANUAL"
    CONFIRMAR_BALANCA_VAZIA_MANUAL = "CONFIRMAR_BALANCA_VAZIA_MANUAL"
    LIBERAR_RETORNO_MANUAL = "LIBERAR_RETORNO_MANUAL"
    ACEITAR_PESO_FINAL = "ACEITAR_PESO_FINAL"
    CANCELAR = "CANCELAR"


class MotivoIntervencao(StrEnum):
    CANCELA_FALHA = "CANCELA_FALHA"
    CANCELA_SEM_CONFIRMACAO = "CANCELA_SEM_CONFIRMACAO"
    POSICAO_PERDIDA = "POSICAO_PERDIDA"
    TEMPO_ESGOTADO = "TEMPO_ESGOTADO"
    LIQUIDO_NEGATIVO = "LIQUIDO_NEGATIVO"
    REINICIO_INCONCLUSIVO = "REINICIO_INCONCLUSIVO"


class MotivoRejeicaoTransicao(StrEnum):
    TRANSICAO_INVALIDA = "TRANSICAO_INVALIDA"
    OPERACAO_TERMINAL = "OPERACAO_TERMINAL"
    PESO_INVALIDO = "PESO_INVALIDO"
    RESPONSAVEL_OU_MOTIVO_AUSENTE = "RESPONSAVEL_OU_MOTIVO_AUSENTE"


class ComandoPedido(StrEnum):
    ABRIR = "ABRIR"
    FECHAR = "FECHAR"


class CancelaPedida(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


@dataclass(frozen=True)
class AcaoPedida:
    comando: ComandoPedido
    cancela: CancelaPedida


@dataclass(frozen=True)
class EventoAutomatico:
    tipo: TipoEvento


@dataclass(frozen=True)
class PesoAceito:
    """Leitura já aceita pela spec 002."""

    peso_kg: Decimal
    lida_em: datetime


@dataclass(frozen=True)
class AcaoManual:
    """Sem campo de peso: todo peso vem de leitura aceita (RN-004, RN-006)."""

    tipo: TipoAcaoManual
    responsavel: str
    motivo: str


type EventoOperacao = EventoAutomatico | PesoAceito | AcaoManual


@dataclass(frozen=True)
class Operacao:
    tipo_operacao: TipoOperacao
    situacao: SituacaoOperacao = SituacaoOperacao.AGUARDANDO_BALANCA_INICIAL
    versao: int = 1
    situacao_anterior: SituacaoOperacao | None = None
    motivo_intervencao: MotivoIntervencao | None = None
    peso_inicial_kg: Decimal | None = None
    peso_inicial_em: datetime | None = None
    peso_final_kg: Decimal | None = None
    peso_final_em: datetime | None = None
    peso_liquido_kg: Decimal | None = None
    classificacao: ClassificacaoPesoLiquido | None = None
    liberacao_manual: bool = False


@dataclass(frozen=True)
class TransicaoAplicada:
    operacao: Operacao
    acao_pedida: AcaoPedida | None


@dataclass(frozen=True)
class TransicaoRejeitada:
    situacao: SituacaoOperacao
    evento: EventoOperacao
    motivo_rejeicao: MotivoRejeicaoTransicao


@dataclass(frozen=True)
class EventoRegistrado:
    operacao: Operacao
    evento: EventoOperacao


type ResultadoTransicao = TransicaoAplicada | TransicaoRejeitada | EventoRegistrado


_Situacao = SituacaoOperacao
_Evento = TipoEvento

_ABRIR_ENTRADA = AcaoPedida(ComandoPedido.ABRIR, CancelaPedida.ENTRADA)
_FECHAR_ENTRADA = AcaoPedida(ComandoPedido.FECHAR, CancelaPedida.ENTRADA)
_ABRIR_SAIDA = AcaoPedida(ComandoPedido.ABRIR, CancelaPedida.SAIDA)
_FECHAR_SAIDA = AcaoPedida(ComandoPedido.FECHAR, CancelaPedida.SAIDA)

# §5.1. A ação de uma transição vem daqui, pela situação de destino: assim não
# há como chegar a uma dessas situações sem pedir o comando, nem o contrário.
_COMANDO_PENDENTE = {
    _Situacao.AUTORIZADA: _ABRIR_ENTRADA,
    _Situacao.FECHANDO_ENTRADA: _FECHAR_ENTRADA,
    _Situacao.PESO_INICIAL_OK: _ABRIR_SAIDA,
    _Situacao.FECHANDO_SAIDA_INICIAL: _FECHAR_SAIDA,
    _Situacao.RETORNO_AUTORIZADO: _ABRIR_ENTRADA,
    _Situacao.FECHANDO_ENTRADA_RETORNO: _FECHAR_ENTRADA,
    _Situacao.PESO_FINAL_OK: _ABRIR_SAIDA,
    _Situacao.FECHANDO_SAIDA: _FECHAR_SAIDA,
}

# §6, tabela principal, sem `PESO_ACEITO`.
_TRANSICOES = {
    (_Situacao.AGUARDANDO_BALANCA_INICIAL, _Evento.BALANCA_DISPONIVEL): (
        _Situacao.AUTORIZADA
    ),
    (_Situacao.AUTORIZADA, _Evento.CANCELA_CONFIRMADA): _Situacao.ENTRADA_LIBERADA,
    (_Situacao.ENTRADA_LIBERADA, _Evento.POSICAO_CONFIRMADA): (
        _Situacao.FECHANDO_ENTRADA
    ),
    (_Situacao.FECHANDO_ENTRADA, _Evento.CANCELA_CONFIRMADA): (
        _Situacao.POSICIONADA_INICIAL
    ),
    (_Situacao.PESO_INICIAL_OK, _Evento.CANCELA_CONFIRMADA): (
        _Situacao.SAIDA_INICIAL_LIBERADA
    ),
    (_Situacao.SAIDA_INICIAL_LIBERADA, _Evento.POSICAO_AUSENTE): (
        _Situacao.FECHANDO_SAIDA_INICIAL
    ),
    (_Situacao.FECHANDO_SAIDA_INICIAL, _Evento.CANCELA_CONFIRMADA): (
        _Situacao.EM_CARGA_DESCARGA
    ),
    (_Situacao.EM_CARGA_DESCARGA, _Evento.PLACA_RETORNO_ACEITA): (
        _Situacao.AGUARDANDO_BALANCA_FINAL
    ),
    (_Situacao.AGUARDANDO_BALANCA_FINAL, _Evento.BALANCA_DISPONIVEL): (
        _Situacao.RETORNO_AUTORIZADO
    ),
    (_Situacao.RETORNO_AUTORIZADO, _Evento.CANCELA_CONFIRMADA): (
        _Situacao.RETORNO_LIBERADO
    ),
    (_Situacao.RETORNO_LIBERADO, _Evento.POSICAO_CONFIRMADA): (
        _Situacao.FECHANDO_ENTRADA_RETORNO
    ),
    (_Situacao.FECHANDO_ENTRADA_RETORNO, _Evento.CANCELA_CONFIRMADA): (
        _Situacao.POSICIONADA_FINAL
    ),
    (_Situacao.PESO_FINAL_OK, _Evento.CANCELA_CONFIRMADA): _Situacao.SAIDA_LIBERADA,
    (_Situacao.SAIDA_LIBERADA, _Evento.POSICAO_AUSENTE): _Situacao.FECHANDO_SAIDA,
    (_Situacao.FECHANDO_SAIDA, _Evento.CANCELA_CONFIRMADA): _Situacao.FINALIZADA,
}

_POSICIONADAS = frozenset({_Situacao.POSICIONADA_INICIAL, _Situacao.POSICIONADA_FINAL})
_TERMINAIS = frozenset({_Situacao.FINALIZADA, _Situacao.CANCELADA})

_AGUARDA_POSICAO = frozenset({_Evento.POSICAO_AUSENTE, _Evento.POSICAO_INCONCLUSIVA})
_AGUARDA_BALANCA_VAZIA = frozenset(
    {_Evento.POSICAO_CONFIRMADA, _Evento.POSICAO_INCONCLUSIVA}
)
_AGUARDA_PESO = frozenset(
    {
        _Evento.POSICAO_CONFIRMADA,
        _Evento.POSICAO_INCONCLUSIVA,
        _Evento.PESO_REJEITADO,
        _Evento.BALANCA_FALHA,
    }
)

# §6, regras por grupo: eventos só registrados, sem mudar a situação.
_SO_REGISTRA = {
    _Situacao.ENTRADA_LIBERADA: _AGUARDA_POSICAO,
    _Situacao.RETORNO_LIBERADO: _AGUARDA_POSICAO,
    _Situacao.SAIDA_INICIAL_LIBERADA: _AGUARDA_BALANCA_VAZIA,
    _Situacao.SAIDA_LIBERADA: _AGUARDA_BALANCA_VAZIA,
    _Situacao.POSICIONADA_INICIAL: _AGUARDA_PESO,
    _Situacao.POSICIONADA_FINAL: _AGUARDA_PESO,
}

# Fila e carga não têm tempo-limite: não há dado que justifique um (§6).
_SEM_TEMPO_LIMITE = frozenset(
    {
        _Situacao.AGUARDANDO_BALANCA_INICIAL,
        _Situacao.AGUARDANDO_BALANCA_FINAL,
        _Situacao.EM_CARGA_DESCARGA,
    }
)

# §6.1: situação de onde a confirmação manual parte -> situação de destino.
_CONFIRMACOES_MANUAIS = {
    TipoAcaoManual.CONFIRMAR_POSICAO_MANUAL: {
        _Situacao.ENTRADA_LIBERADA: _Situacao.FECHANDO_ENTRADA,
        _Situacao.RETORNO_LIBERADO: _Situacao.FECHANDO_ENTRADA_RETORNO,
    },
    TipoAcaoManual.CONFIRMAR_BALANCA_VAZIA_MANUAL: {
        _Situacao.SAIDA_INICIAL_LIBERADA: _Situacao.FECHANDO_SAIDA_INICIAL,
        _Situacao.SAIDA_LIBERADA: _Situacao.FECHANDO_SAIDA,
    },
}


def aplicar_evento(
    operacao: Operacao, evento: EventoOperacao, parametros: ParametrosPesoLiquido
) -> ResultadoTransicao:
    if operacao.situacao in _TERMINAIS:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.OPERACAO_TERMINAL)
    match evento:
        case EventoAutomatico():
            return _aplicar_automatico(operacao, evento)
        case PesoAceito():
            return _aplicar_peso(operacao, evento, parametros)
        case AcaoManual():
            return _aplicar_manual(operacao, evento)


def _aplicar_automatico(
    operacao: Operacao, evento: EventoAutomatico
) -> ResultadoTransicao:
    situacao = operacao.situacao
    tipo = evento.tipo
    # A parada só termina por ação humana (§6.1).
    if situacao is _Situacao.AGUARDANDO_INTERVENCAO:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA)

    destino = _TRANSICOES.get((situacao, tipo))
    if destino is not None:
        return _ir_para(operacao, destino)
    if tipo in _SO_REGISTRA.get(situacao, frozenset()):
        return EventoRegistrado(operacao, evento)

    motivo = _motivo_de_parada(situacao, tipo)
    if motivo is None:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA)
    return _parar(operacao, motivo)


def _motivo_de_parada(
    situacao: SituacaoOperacao, tipo: TipoEvento
) -> MotivoIntervencao | None:
    if situacao in _COMANDO_PENDENTE and tipo is _Evento.CANCELA_FALHA:
        return MotivoIntervencao.CANCELA_FALHA
    if situacao in _COMANDO_PENDENTE and tipo is _Evento.CANCELA_SEM_CONFIRMACAO:
        return MotivoIntervencao.CANCELA_SEM_CONFIRMACAO
    if situacao in _POSICIONADAS and tipo is _Evento.POSICAO_AUSENTE:
        return MotivoIntervencao.POSICAO_PERDIDA
    if situacao not in _SEM_TEMPO_LIMITE and tipo is _Evento.TEMPO_ESGOTADO:
        return MotivoIntervencao.TEMPO_ESGOTADO
    if tipo is _Evento.REINICIO_INCONCLUSIVO:
        return MotivoIntervencao.REINICIO_INCONCLUSIVO
    return None


def _aplicar_peso(
    operacao: Operacao, evento: PesoAceito, parametros: ParametrosPesoLiquido
) -> ResultadoTransicao:
    if operacao.situacao not in _POSICIONADAS:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA)
    if not evento.peso_kg.is_finite() or evento.lida_em.utcoffset() is None:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.PESO_INVALIDO)

    if operacao.situacao is _Situacao.POSICIONADA_INICIAL:
        com_peso = replace(
            operacao, peso_inicial_kg=evento.peso_kg, peso_inicial_em=evento.lida_em
        )
        return _ir_para(com_peso, _Situacao.PESO_INICIAL_OK)

    # Só uma operação remontada com dados incoerentes chega aqui sem o peso
    # inicial: sem ele não há líquido, e a operação não avança (RN-006).
    if operacao.peso_inicial_kg is None:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.PESO_INVALIDO)
    liquido = calcular_peso_liquido(
        operacao.tipo_operacao, operacao.peso_inicial_kg, evento.peso_kg, parametros
    )
    com_peso = replace(
        operacao,
        peso_final_kg=evento.peso_kg,
        peso_final_em=evento.lida_em,
        peso_liquido_kg=liquido.peso_liquido_kg,
        classificacao=liquido.classificacao,
    )
    if liquido.classificacao is ClassificacaoPesoLiquido.NEGATIVO_FORA_TOLERANCIA:
        return _parar(com_peso, MotivoIntervencao.LIQUIDO_NEGATIVO)
    return _ir_para(com_peso, _Situacao.PESO_FINAL_OK)


def _aplicar_manual(operacao: Operacao, evento: AcaoManual) -> ResultadoTransicao:
    if not evento.responsavel.strip() or not evento.motivo.strip():
        return _rejeitar(
            operacao, evento, MotivoRejeicaoTransicao.RESPONSAVEL_OU_MOTIVO_AUSENTE
        )

    if evento.tipo is TipoAcaoManual.CANCELAR:
        return _ir_para(operacao, _Situacao.CANCELADA)
    if evento.tipo is TipoAcaoManual.LIBERAR_RETORNO_MANUAL:
        if operacao.situacao is not _Situacao.EM_CARGA_DESCARGA:
            return _rejeitar(
                operacao, evento, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA
            )
        return _ir_para(
            replace(operacao, liberacao_manual=True),
            _Situacao.AGUARDANDO_BALANCA_FINAL,
        )

    anterior = operacao.situacao_anterior
    if operacao.situacao is not _Situacao.AGUARDANDO_INTERVENCAO or anterior is None:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA)

    if evento.tipo is TipoAcaoManual.TENTAR_NOVAMENTE:
        return _ir_para(_preparar_nova_tentativa(operacao), anterior)
    if evento.tipo is TipoAcaoManual.ACEITAR_PESO_FINAL:
        if operacao.motivo_intervencao is not MotivoIntervencao.LIQUIDO_NEGATIVO:
            return _rejeitar(
                operacao, evento, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA
            )
        return _ir_para(
            replace(operacao, liberacao_manual=True), _Situacao.PESO_FINAL_OK
        )

    destino = _CONFIRMACOES_MANUAIS[evento.tipo].get(anterior)
    if destino is None:
        return _rejeitar(operacao, evento, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA)
    return _ir_para(replace(operacao, liberacao_manual=True), destino)


def _preparar_nova_tentativa(operacao: Operacao) -> Operacao:
    if operacao.motivo_intervencao is not MotivoIntervencao.LIQUIDO_NEGATIVO:
        return operacao
    # Nova pesagem final: os valores anteriores ficam só na auditoria (§6.1).
    return replace(
        operacao,
        peso_final_kg=None,
        peso_final_em=None,
        peso_liquido_kg=None,
        classificacao=None,
    )


def _ir_para(operacao: Operacao, destino: SituacaoOperacao) -> TransicaoAplicada:
    nova = replace(
        operacao,
        situacao=destino,
        versao=operacao.versao + 1,
        situacao_anterior=None,
        motivo_intervencao=None,
    )
    return TransicaoAplicada(nova, _COMANDO_PENDENTE.get(destino))


def _parar(operacao: Operacao, motivo: MotivoIntervencao) -> TransicaoAplicada:
    nova = replace(
        operacao,
        situacao=_Situacao.AGUARDANDO_INTERVENCAO,
        versao=operacao.versao + 1,
        situacao_anterior=operacao.situacao,
        motivo_intervencao=motivo,
    )
    return TransicaoAplicada(nova, None)


def _rejeitar(
    operacao: Operacao, evento: EventoOperacao, motivo: MotivoRejeicaoTransicao
) -> TransicaoRejeitada:
    return TransicaoRejeitada(operacao.situacao, evento, motivo)
