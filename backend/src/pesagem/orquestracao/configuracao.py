"""Configuração da orquestração (spec 015 §5.6). Nenhum valor tem padrão."""

from dataclasses import dataclass, fields
from datetime import tzinfo

from pesagem.orquestracao.erros import ErroConfiguracaoOrquestracao


@dataclass(frozen=True)
class ConfiguracaoOrquestracao:
    fuso_patio: tzinfo
    intervalo_analise_ms: int
    idade_maxima_imagem_ms: int
    intervalo_leitura_balanca_ms: int
    tempo_limite_posicionamento_ms: int
    tempo_limite_pesagem_ms: int
    tempo_limite_saida_balanca_ms: int
    intervalo_minimo_peso_ms: int

    def __post_init__(self) -> None:
        for campo in fields(self):
            valor = getattr(self, campo.name)
            if campo.type is int and (not isinstance(valor, int) or valor <= 0):
                raise ErroConfiguracaoOrquestracao(f"{campo.name} deve ser inteiro > 0")
