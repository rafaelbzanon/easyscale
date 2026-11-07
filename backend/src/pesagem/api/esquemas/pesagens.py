"""Objeto Pesagem (spec 009 §5.1), usado também na lista do histórico (spec 010 §5.1)."""

from decimal import Decimal
from typing import Any

from pesagem.dominio.operacao.maquina_estados import (
    COMANDO_PENDENTE,
    AcaoManual,
    MotivoIntervencao,
    Operacao,
    SituacaoOperacao,
    TipoAcaoManual,
    TransicaoAplicada,
    aplicar_evento,
)
from pesagem.dominio.pesagem.calculo_peso import (
    ClassificacaoPesoLiquido,
    ParametrosPesoLiquido,
    TipoOperacao,
)
from pesagem.orquestracao.operacao import ocupa_balanca

# Ações manuais não usam a tolerância; qualquer valor válido serve para perguntar
# à máquina de estados o que ela aceita agora.
_SEM_PESO = ParametrosPesoLiquido(Decimal("0"))


def _texto(valor: Any) -> Any:
    return str(valor) if isinstance(valor, Decimal) else valor


def _operacao(linha: Any) -> Operacao:
    def ou_nada(valor: str | None, tipo: Any) -> Any:
        return None if valor is None else tipo(valor)

    return Operacao(
        tipo_operacao=TipoOperacao(linha["tipo_operacao"]),
        situacao=SituacaoOperacao(linha["situacao"]),
        versao=linha["versao"],
        situacao_anterior=ou_nada(linha["situacao_anterior"], SituacaoOperacao),
        motivo_intervencao=ou_nada(linha["motivo_intervencao"], MotivoIntervencao),
        peso_inicial_kg=linha["peso_inicial_kg"],
        peso_inicial_em=linha["peso_inicial_em"],
        peso_final_kg=linha["peso_final_kg"],
        peso_final_em=linha["peso_final_em"],
        peso_liquido_kg=linha["peso_liquido_kg"],
        classificacao=ou_nada(linha["classificacao"], ClassificacaoPesoLiquido),
        liberacao_manual=linha["liberacao_manual"],
    )


def pesagem_resposta(linha: Any) -> dict[str, Any]:
    operacao = _operacao(linha)
    pendente = COMANDO_PENDENTE.get(operacao.situacao)
    # A lista vem da própria regra (spec 006 §6.1), para não repetir a tabela aqui.
    acoes = [
        tipo.value
        for tipo in TipoAcaoManual
        if isinstance(
            aplicar_evento(
                operacao, AcaoManual(tipo, "consulta", "consulta"), _SEM_PESO
            ),
            TransicaoAplicada,
        )
    ]
    dados = {
        **{k: _texto(v) for k, v in dict(linha).items()},
        "comando_pendente": None
        if pendente is None
        else {"comando": pendente.comando.value, "cancela": pendente.cancela.value},
        "acoes_disponiveis": acoes,
        "ocupa_balanca": ocupa_balanca(operacao),
        "faixa_hora_inicio": linha["faixa_hora_inicio"].strftime("%H:%M"),
        "faixa_hora_fim": linha["faixa_hora_fim"].strftime("%H:%M"),
    }
    return dados
