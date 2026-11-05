"""Testes da máquina de estados da operação (spec 006).

As tabelas esperadas são escritas aqui, a partir da spec, e não importadas do
módulo: se fossem as mesmas, um erro na tabela passaria despercebido.
"""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from pesagem.dominio.operacao.maquina_estados import (
    AcaoManual,
    AcaoPedida,
    CancelaPedida,
    ComandoPedido,
    EventoAutomatico,
    EventoOperacao,
    EventoRegistrado,
    MotivoIntervencao,
    MotivoRejeicaoTransicao,
    Operacao,
    PesoAceito,
    ResultadoTransicao,
    SituacaoOperacao,
    TipoAcaoManual,
    TipoEvento,
    TransicaoAplicada,
    TransicaoRejeitada,
    aplicar_evento,
)
from pesagem.dominio.pesagem.calculo_peso import (
    ClassificacaoPesoLiquido,
    ParametrosPesoLiquido,
    TipoOperacao,
)

S = SituacaoOperacao
E = TipoEvento
M = TipoAcaoManual

PARAMETROS = ParametrosPesoLiquido(Decimal("20"))
INSTANTE = datetime(2026, 11, 4, 8, 0, tzinfo=UTC)

ABRIR_ENTRADA = AcaoPedida(ComandoPedido.ABRIR, CancelaPedida.ENTRADA)
FECHAR_ENTRADA = AcaoPedida(ComandoPedido.FECHAR, CancelaPedida.ENTRADA)
ABRIR_SAIDA = AcaoPedida(ComandoPedido.ABRIR, CancelaPedida.SAIDA)
FECHAR_SAIDA = AcaoPedida(ComandoPedido.FECHAR, CancelaPedida.SAIDA)

COMANDO_PENDENTE = {
    S.AUTORIZADA: ABRIR_ENTRADA,
    S.FECHANDO_ENTRADA: FECHAR_ENTRADA,
    S.PESO_INICIAL_OK: ABRIR_SAIDA,
    S.FECHANDO_SAIDA_INICIAL: FECHAR_SAIDA,
    S.RETORNO_AUTORIZADO: ABRIR_ENTRADA,
    S.FECHANDO_ENTRADA_RETORNO: FECHAR_ENTRADA,
    S.PESO_FINAL_OK: ABRIR_SAIDA,
    S.FECHANDO_SAIDA: FECHAR_SAIDA,
}
TERMINAIS = (S.FINALIZADA, S.CANCELADA)
SEM_TEMPO_LIMITE = (
    S.AGUARDANDO_BALANCA_INICIAL,
    S.AGUARDANDO_BALANCA_FINAL,
    S.EM_CARGA_DESCARGA,
)
POSICIONADAS = (S.POSICIONADA_INICIAL, S.POSICIONADA_FINAL)
PARA_INTERVENCAO = (
    E.CANCELA_FALHA,
    E.CANCELA_SEM_CONFIRMACAO,
    E.TEMPO_ESGOTADO,
    E.REINICIO_INCONCLUSIVO,
)

# §6, tabela principal, sem o peso.
TRANSICOES = {
    (S.AGUARDANDO_BALANCA_INICIAL, E.BALANCA_DISPONIVEL): S.AUTORIZADA,
    (S.AUTORIZADA, E.CANCELA_CONFIRMADA): S.ENTRADA_LIBERADA,
    (S.ENTRADA_LIBERADA, E.POSICAO_CONFIRMADA): S.FECHANDO_ENTRADA,
    (S.FECHANDO_ENTRADA, E.CANCELA_CONFIRMADA): S.POSICIONADA_INICIAL,
    (S.PESO_INICIAL_OK, E.CANCELA_CONFIRMADA): S.SAIDA_INICIAL_LIBERADA,
    (S.SAIDA_INICIAL_LIBERADA, E.POSICAO_AUSENTE): S.FECHANDO_SAIDA_INICIAL,
    (S.FECHANDO_SAIDA_INICIAL, E.CANCELA_CONFIRMADA): S.EM_CARGA_DESCARGA,
    (S.EM_CARGA_DESCARGA, E.PLACA_RETORNO_ACEITA): S.AGUARDANDO_BALANCA_FINAL,
    (S.AGUARDANDO_BALANCA_FINAL, E.BALANCA_DISPONIVEL): S.RETORNO_AUTORIZADO,
    (S.RETORNO_AUTORIZADO, E.CANCELA_CONFIRMADA): S.RETORNO_LIBERADO,
    (S.RETORNO_LIBERADO, E.POSICAO_CONFIRMADA): S.FECHANDO_ENTRADA_RETORNO,
    (S.FECHANDO_ENTRADA_RETORNO, E.CANCELA_CONFIRMADA): S.POSICIONADA_FINAL,
    (S.PESO_FINAL_OK, E.CANCELA_CONFIRMADA): S.SAIDA_LIBERADA,
    (S.SAIDA_LIBERADA, E.POSICAO_AUSENTE): S.FECHANDO_SAIDA,
    (S.FECHANDO_SAIDA, E.CANCELA_CONFIRMADA): S.FINALIZADA,
}

# §6, regras por grupo: só registra.
SO_REGISTRA = {
    S.ENTRADA_LIBERADA: {E.POSICAO_AUSENTE, E.POSICAO_INCONCLUSIVA},
    S.RETORNO_LIBERADO: {E.POSICAO_AUSENTE, E.POSICAO_INCONCLUSIVA},
    S.SAIDA_INICIAL_LIBERADA: {E.POSICAO_CONFIRMADA, E.POSICAO_INCONCLUSIVA},
    S.SAIDA_LIBERADA: {E.POSICAO_CONFIRMADA, E.POSICAO_INCONCLUSIVA},
    S.POSICIONADA_INICIAL: {
        E.POSICAO_CONFIRMADA,
        E.POSICAO_INCONCLUSIVA,
        E.PESO_REJEITADO,
        E.BALANCA_FALHA,
    },
    S.POSICIONADA_FINAL: {
        E.POSICAO_CONFIRMADA,
        E.POSICAO_INCONCLUSIVA,
        E.PESO_REJEITADO,
        E.BALANCA_FALHA,
    },
}


def para_intervencao_esperada(situacao: S, evento: E) -> MotivoIntervencao | None:
    if situacao in COMANDO_PENDENTE and evento is E.CANCELA_FALHA:
        return MotivoIntervencao.CANCELA_FALHA
    if situacao in COMANDO_PENDENTE and evento is E.CANCELA_SEM_CONFIRMACAO:
        return MotivoIntervencao.CANCELA_SEM_CONFIRMACAO
    if situacao in POSICIONADAS and evento is E.POSICAO_AUSENTE:
        return MotivoIntervencao.POSICAO_PERDIDA
    if evento is E.TEMPO_ESGOTADO and situacao not in SEM_TEMPO_LIMITE:
        return MotivoIntervencao.TEMPO_ESGOTADO
    if evento is E.REINICIO_INCONCLUSIVO:
        return MotivoIntervencao.REINICIO_INCONCLUSIVO
    return None


def operacao_em(
    situacao: S, tipo_operacao: TipoOperacao = TipoOperacao.CARGA
) -> Operacao:
    return Operacao(
        tipo_operacao,
        situacao=situacao,
        versao=7,
        peso_inicial_kg=Decimal("15000"),
        peso_inicial_em=INSTANTE,
    )


def intervencao(
    anterior: S, motivo: MotivoIntervencao = MotivoIntervencao.TEMPO_ESGOTADO
) -> Operacao:
    return replace(
        operacao_em(S.AGUARDANDO_INTERVENCAO),
        situacao_anterior=anterior,
        motivo_intervencao=motivo,
    )


def manual(tipo: M) -> AcaoManual:
    return AcaoManual(tipo, "usuario-1", "motivo informado")


def peso(valor: str) -> PesoAceito:
    return PesoAceito(Decimal(valor), INSTANTE)


def aplicar(operacao: Operacao, evento: EventoOperacao) -> ResultadoTransicao:
    return aplicar_evento(operacao, evento, PARAMETROS)


def aplicada(operacao: Operacao, evento: EventoOperacao) -> TransicaoAplicada:
    resultado = aplicar(operacao, evento)
    assert isinstance(resultado, TransicaoAplicada)
    return resultado


def percorrer(tipo_operacao: TipoOperacao, peso_final: str) -> list[TransicaoAplicada]:
    passos: list[EventoOperacao] = [
        EventoAutomatico(E.BALANCA_DISPONIVEL),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
        EventoAutomatico(E.POSICAO_CONFIRMADA),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
        peso("15000"),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
        EventoAutomatico(E.POSICAO_AUSENTE),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
        EventoAutomatico(E.PLACA_RETORNO_ACEITA),
        EventoAutomatico(E.BALANCA_DISPONIVEL),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
        EventoAutomatico(E.POSICAO_CONFIRMADA),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
        peso(peso_final),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
        EventoAutomatico(E.POSICAO_AUSENTE),
        EventoAutomatico(E.CANCELA_CONFIRMADA),
    ]
    operacao = Operacao(tipo_operacao)
    resultados = []
    for evento in passos:
        resultado = aplicada(operacao, evento)
        resultados.append(resultado)
        operacao = resultado.operacao
    return resultados


def test_operacao_nasce_aguardando_a_balanca_sem_comando() -> None:
    """§6 e RN-019: a entrada só abre com a balança reservada."""
    operacao = Operacao(TipoOperacao.CARGA)
    assert operacao.situacao is S.AGUARDANDO_BALANCA_INICIAL
    assert operacao.versao == 1


def test_caminho_completo_de_carga() -> None:
    """CA-001: situações na ordem da §6 e exatamente 8 comandos."""
    resultados = percorrer(TipoOperacao.CARGA, "42000")
    assert [r.operacao.situacao for r in resultados] == [
        S.AUTORIZADA,
        S.ENTRADA_LIBERADA,
        S.FECHANDO_ENTRADA,
        S.POSICIONADA_INICIAL,
        S.PESO_INICIAL_OK,
        S.SAIDA_INICIAL_LIBERADA,
        S.FECHANDO_SAIDA_INICIAL,
        S.EM_CARGA_DESCARGA,
        S.AGUARDANDO_BALANCA_FINAL,
        S.RETORNO_AUTORIZADO,
        S.RETORNO_LIBERADO,
        S.FECHANDO_ENTRADA_RETORNO,
        S.POSICIONADA_FINAL,
        S.PESO_FINAL_OK,
        S.SAIDA_LIBERADA,
        S.FECHANDO_SAIDA,
        S.FINALIZADA,
    ]
    assert [r.acao_pedida for r in resultados if r.acao_pedida] == [
        ABRIR_ENTRADA,
        FECHAR_ENTRADA,
        ABRIR_SAIDA,
        FECHAR_SAIDA,
    ] * 2
    final = resultados[-1].operacao
    assert final.peso_liquido_kg == Decimal("27000")
    assert final.classificacao is ClassificacaoPesoLiquido.COM_MOVIMENTACAO
    assert not final.liberacao_manual


def test_descarga_calcula_inicial_menos_final() -> None:
    """CA-002."""
    final = percorrer(TipoOperacao.DESCARGA, "9000")[-1].operacao
    assert final.peso_liquido_kg == Decimal("6000")


@pytest.mark.parametrize("situacao", list(S))
@pytest.mark.parametrize("evento", list(E))
def test_todos_os_pares_de_evento_automatico(situacao: S, evento: E) -> None:
    """CA-003, CA-009 a CA-016, CA-024, CA-025: tabela de todos os pares."""
    operacao = operacao_em(situacao)
    if situacao is S.AGUARDANDO_INTERVENCAO:
        operacao = intervencao(S.ENTRADA_LIBERADA)
    automatico = EventoAutomatico(evento)
    resultado = aplicar(operacao, automatico)

    if situacao in TERMINAIS:
        assert resultado == TransicaoRejeitada(
            situacao, automatico, MotivoRejeicaoTransicao.OPERACAO_TERMINAL
        )
    elif situacao is S.AGUARDANDO_INTERVENCAO:
        assert resultado == TransicaoRejeitada(
            situacao, automatico, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA
        )
    elif (situacao, evento) in TRANSICOES:
        destino = TRANSICOES[situacao, evento]
        assert isinstance(resultado, TransicaoAplicada)
        assert resultado.operacao.situacao is destino
        assert resultado.operacao.versao == 8
        assert resultado.acao_pedida == COMANDO_PENDENTE.get(destino)
    elif evento in SO_REGISTRA.get(situacao, ()):
        assert resultado == EventoRegistrado(operacao, automatico)
    elif (motivo := para_intervencao_esperada(situacao, evento)) is not None:
        assert isinstance(resultado, TransicaoAplicada)
        assert resultado.operacao.situacao is S.AGUARDANDO_INTERVENCAO
        assert resultado.operacao.situacao_anterior is situacao
        assert resultado.operacao.motivo_intervencao is motivo
        assert resultado.operacao.versao == 8
        assert resultado.acao_pedida is None
    else:
        assert resultado == TransicaoRejeitada(
            situacao, automatico, MotivoRejeicaoTransicao.TRANSICAO_INVALIDA
        )


@pytest.mark.parametrize("situacao", [s for s in S if s not in POSICIONADAS])
def test_peso_fora_de_posicionada_e_rejeitado(situacao: S) -> None:
    """CA-004 e RF-027."""
    operacao = operacao_em(situacao)
    resultado = aplicar(operacao, peso("20000"))
    assert isinstance(resultado, TransicaoRejeitada)
    assert resultado.situacao is situacao


def test_segundo_peso_nao_altera_o_guardado() -> None:
    """CA-004: a segunda leitura não duplica a pesagem."""
    resultado = aplicada(operacao_em(S.POSICIONADA_INICIAL), peso("15500"))
    assert resultado.operacao.peso_inicial_kg == Decimal("15500")
    assert isinstance(aplicar(resultado.operacao, peso("16000")), TransicaoRejeitada)


@pytest.mark.parametrize("situacao", POSICIONADAS)
@pytest.mark.parametrize(
    "evento",
    [
        PesoAceito(Decimal("NaN"), INSTANTE),
        PesoAceito(Decimal("Infinity"), INSTANTE),
        PesoAceito(Decimal("15000"), datetime(2026, 11, 4, 8, 0)),
    ],
)
def test_peso_invalido_e_rejeitado(situacao: S, evento: PesoAceito) -> None:
    """§7.1."""
    assert aplicar(operacao_em(situacao), evento) == TransicaoRejeitada(
        situacao, evento, MotivoRejeicaoTransicao.PESO_INVALIDO
    )


def test_peso_final_sem_peso_inicial_e_rejeitado() -> None:
    """RN-006: o líquido só é calculado com os dois pesos medidos."""
    operacao = Operacao(TipoOperacao.CARGA, situacao=S.POSICIONADA_FINAL)
    evento = peso("42000")
    assert aplicar(operacao, evento) == TransicaoRejeitada(
        S.POSICIONADA_FINAL, evento, MotivoRejeicaoTransicao.PESO_INVALIDO
    )


def test_comandos_so_nas_situacoes_da_spec() -> None:
    """CA-005, CA-006, CA-007."""
    resultados = percorrer(TipoOperacao.CARGA, "42000")
    pedidas = {r.operacao.situacao: r.acao_pedida for r in resultados if r.acao_pedida}
    assert pedidas == COMANDO_PENDENTE


def test_carga_so_avanca_com_placa_ou_liberacao_manual() -> None:
    """CA-008."""
    operacao = operacao_em(S.EM_CARGA_DESCARGA)
    evento = EventoAutomatico(E.POSICAO_CONFIRMADA)
    assert isinstance(aplicar(operacao, evento), TransicaoRejeitada)
    assert (
        aplicada(operacao, EventoAutomatico(E.PLACA_RETORNO_ACEITA)).operacao.situacao
        is S.AGUARDANDO_BALANCA_FINAL
    )


def test_sem_movimentacao_guarda_o_valor_calculado() -> None:
    """CA-009: o líquido não é trocado por zero."""
    resultado = aplicada(operacao_em(S.POSICIONADA_FINAL), peso("15012"))
    assert resultado.operacao.situacao is S.PESO_FINAL_OK
    assert resultado.operacao.peso_liquido_kg == Decimal("12")
    assert resultado.operacao.classificacao is ClassificacaoPesoLiquido.SEM_MOVIMENTACAO
    assert resultado.acao_pedida == ABRIR_SAIDA


def test_liquido_negativo_para_sem_pedir_a_saida() -> None:
    """CA-010."""
    resultado = aplicada(operacao_em(S.POSICIONADA_FINAL), peso("14000"))
    operacao = resultado.operacao
    assert operacao.situacao is S.AGUARDANDO_INTERVENCAO
    assert operacao.situacao_anterior is S.POSICIONADA_FINAL
    assert operacao.motivo_intervencao is MotivoIntervencao.LIQUIDO_NEGATIVO
    assert operacao.peso_final_kg == Decimal("14000")
    assert operacao.peso_liquido_kg == Decimal("-1000")
    assert resultado.acao_pedida is None


@pytest.mark.parametrize("anterior", COMANDO_PENDENTE)
def test_tentar_novamente_repete_o_comando_pendente(anterior: S) -> None:
    """CA-017."""
    resultado = aplicada(intervencao(anterior), manual(M.TENTAR_NOVAMENTE))
    assert resultado.operacao.situacao is anterior
    assert resultado.operacao.situacao_anterior is None
    assert resultado.operacao.motivo_intervencao is None
    assert resultado.acao_pedida == COMANDO_PENDENTE[anterior]


def test_tentar_novamente_sem_comando_pendente_nao_pede_acao() -> None:
    """CA-017."""
    resultado = aplicada(intervencao(S.ENTRADA_LIBERADA), manual(M.TENTAR_NOVAMENTE))
    assert resultado.operacao.situacao is S.ENTRADA_LIBERADA
    assert resultado.acao_pedida is None


def test_nova_pesagem_apos_liquido_negativo_limpa_o_peso_final() -> None:
    """§6.1: os valores anteriores ficam só na auditoria."""
    parada = aplicada(operacao_em(S.POSICIONADA_FINAL), peso("14000")).operacao
    nova = aplicada(parada, manual(M.TENTAR_NOVAMENTE)).operacao
    assert nova.situacao is S.POSICIONADA_FINAL
    assert nova.peso_final_kg is None
    assert nova.peso_final_em is None
    assert nova.peso_liquido_kg is None
    assert nova.classificacao is None
    assert aplicada(nova, peso("42000")).operacao.situacao is S.PESO_FINAL_OK


@pytest.mark.parametrize(
    ("acao", "anterior", "destino", "comando"),
    [
        (
            M.CONFIRMAR_POSICAO_MANUAL,
            S.ENTRADA_LIBERADA,
            S.FECHANDO_ENTRADA,
            FECHAR_ENTRADA,
        ),
        (
            M.CONFIRMAR_POSICAO_MANUAL,
            S.RETORNO_LIBERADO,
            S.FECHANDO_ENTRADA_RETORNO,
            FECHAR_ENTRADA,
        ),
        (
            M.CONFIRMAR_BALANCA_VAZIA_MANUAL,
            S.SAIDA_INICIAL_LIBERADA,
            S.FECHANDO_SAIDA_INICIAL,
            FECHAR_SAIDA,
        ),
        (
            M.CONFIRMAR_BALANCA_VAZIA_MANUAL,
            S.SAIDA_LIBERADA,
            S.FECHANDO_SAIDA,
            FECHAR_SAIDA,
        ),
    ],
)
def test_confirmacoes_manuais_validas(
    acao: M, anterior: S, destino: S, comando: AcaoPedida
) -> None:
    """CA-018."""
    resultado = aplicada(intervencao(anterior), manual(acao))
    assert resultado.operacao.situacao is destino
    assert resultado.operacao.liberacao_manual
    assert resultado.acao_pedida == comando


@pytest.mark.parametrize(
    ("acao", "validas"),
    [
        (M.CONFIRMAR_POSICAO_MANUAL, (S.ENTRADA_LIBERADA, S.RETORNO_LIBERADO)),
        (
            M.CONFIRMAR_BALANCA_VAZIA_MANUAL,
            (S.SAIDA_INICIAL_LIBERADA, S.SAIDA_LIBERADA),
        ),
    ],
)
def test_confirmacoes_manuais_fora_das_situacoes_da_spec(
    acao: M, validas: tuple[S, ...]
) -> None:
    """CA-018."""
    nao_terminais = [s for s in S if s not in TERMINAIS]
    for anterior in nao_terminais:
        if anterior not in validas:
            evento = manual(acao)
            resultado = aplicar(intervencao(anterior), evento)
            assert isinstance(resultado, TransicaoRejeitada)
    for situacao in validas:
        assert isinstance(
            aplicar(operacao_em(situacao), manual(acao)), TransicaoRejeitada
        )


@pytest.mark.parametrize("situacao", [s for s in S if s not in TERMINAIS])
def test_liberar_retorno_manual_so_em_carga_descarga(situacao: S) -> None:
    """CA-019."""
    resultado = aplicar(operacao_em(situacao), manual(M.LIBERAR_RETORNO_MANUAL))
    if situacao is S.EM_CARGA_DESCARGA:
        assert isinstance(resultado, TransicaoAplicada)
        assert resultado.operacao.situacao is S.AGUARDANDO_BALANCA_FINAL
        assert resultado.operacao.liberacao_manual
    else:
        assert isinstance(resultado, TransicaoRejeitada)


def test_aceitar_peso_final_com_liquido_negativo() -> None:
    """CA-020: mantém os valores e pede a saída."""
    parada = aplicada(operacao_em(S.POSICIONADA_FINAL), peso("14000")).operacao
    resultado = aplicada(parada, manual(M.ACEITAR_PESO_FINAL))
    assert resultado.operacao.situacao is S.PESO_FINAL_OK
    assert resultado.operacao.liberacao_manual
    assert resultado.operacao.peso_final_kg == Decimal("14000")
    assert resultado.operacao.peso_liquido_kg == Decimal("-1000")
    assert resultado.acao_pedida == ABRIR_SAIDA


@pytest.mark.parametrize(
    "motivo", [m for m in MotivoIntervencao if m != MotivoIntervencao.LIQUIDO_NEGATIVO]
)
def test_aceitar_peso_final_exige_liquido_negativo(motivo: MotivoIntervencao) -> None:
    """CA-020."""
    operacao = intervencao(S.POSICIONADA_FINAL, motivo)
    resultado = aplicar(operacao, manual(M.ACEITAR_PESO_FINAL))
    assert isinstance(resultado, TransicaoRejeitada)


@pytest.mark.parametrize("acao", list(M))
@pytest.mark.parametrize(
    ("responsavel", "motivo"), [("", "motivo"), ("usuario", ""), (" ", " ")]
)
def test_acao_manual_sem_responsavel_ou_motivo(
    acao: M, responsavel: str, motivo: str
) -> None:
    """CA-021 (RN-011)."""
    operacao = intervencao(S.ENTRADA_LIBERADA)
    evento = AcaoManual(acao, responsavel, motivo)
    assert aplicar(operacao, evento) == TransicaoRejeitada(
        S.AGUARDANDO_INTERVENCAO,
        evento,
        MotivoRejeicaoTransicao.RESPONSAVEL_OU_MOTIVO_AUSENTE,
    )


@pytest.mark.parametrize(
    "acao", [a for a in M if a not in (M.CANCELAR, M.LIBERAR_RETORNO_MANUAL)]
)
def test_acao_de_intervencao_fora_da_parada_e_rejeitada(acao: M) -> None:
    """CA-003."""
    resultado = aplicar(operacao_em(S.ENTRADA_LIBERADA), manual(acao))
    assert isinstance(resultado, TransicaoRejeitada)


def test_acao_manual_nao_tem_campo_de_peso() -> None:
    """CA-022."""
    assert set(AcaoManual.__dataclass_fields__) == {"tipo", "responsavel", "motivo"}


@pytest.mark.parametrize("situacao", [s for s in S if s not in TERMINAIS])
def test_cancelar_em_situacao_nao_terminal(situacao: S) -> None:
    """CA-023."""
    resultado = aplicada(operacao_em(situacao), manual(M.CANCELAR))
    assert resultado.operacao.situacao is S.CANCELADA
    assert resultado.acao_pedida is None
    assert resultado.operacao.peso_inicial_kg == Decimal("15000")


@pytest.mark.parametrize("situacao", TERMINAIS)
@pytest.mark.parametrize(
    "evento",
    [manual(a) for a in M] + [peso("15000")],
)
def test_terminais_rejeitam_acoes_e_peso(situacao: S, evento: EventoOperacao) -> None:
    """CA-023, CA-024."""
    assert aplicar(operacao_em(situacao), evento) == TransicaoRejeitada(
        situacao, evento, MotivoRejeicaoTransicao.OPERACAO_TERMINAL
    )


def test_rejeicao_e_registro_nao_alteram_a_operacao() -> None:
    """CA-025."""
    operacao = operacao_em(S.ENTRADA_LIBERADA)
    registrado = aplicar(operacao, EventoAutomatico(E.POSICAO_INCONCLUSIVA))
    assert isinstance(registrado, EventoRegistrado)
    assert registrado.operacao is operacao
