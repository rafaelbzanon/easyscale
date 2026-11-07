"""Leitura das variáveis de ambiente (`AMBIENTE.md` §8; specs 007, 008, 012, 014).

Valor obrigatório ausente ou inválido impede a partida: nada é "chutado".
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from ipaddress import IPv4Network, IPv6Network, ip_network
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ErroConfiguracao(Exception):
    """Variável ausente ou inválida. A mensagem cita o nome, nunca o valor."""


@dataclass(frozen=True)
class ConfiguracaoBanco:
    host: str
    porta: int
    nome: str
    usuario: str
    senha: str = field(repr=False)


@dataclass(frozen=True)
class ConfiguracaoSeguranca:
    """Spec 012 §6.12."""

    origens_permitidas: frozenset[str]
    sessao_tempo_sem_uso_s: int
    login_tentativas_maximas: int
    login_bloqueio_s: int


@dataclass(frozen=True)
class ConfiguracaoAutoatendimento:
    """Spec 013 §6.7. Sem redes configuradas, o autoatendimento fica desligado."""

    redes: tuple[IPv4Network | IPv6Network, ...]
    tentativas_maximas: int
    bloqueio_s: int


@dataclass(frozen=True)
class ConfiguracaoOperacao:
    """Specs 002, 004, 005, 009, 011 e 015 §5.6. Valores crus: a composição (`main.py`)
    cria os parâmetros do domínio, que validam de novo as regras deles."""

    modo_balanca: str
    modo_cancelas: str
    modo_cameras: str
    peso_minimo_kg: Decimal
    peso_maximo_kg: Decimal
    quantidade_leituras_estaveis: int
    variacao_maxima_kg: Decimal
    janela_estabilidade_ms: int
    tolerancia_movimentacao_kg: Decimal
    limiar_confianca: Decimal
    intervalo_analise_ms: int
    idade_maxima_imagem_ms: int
    intervalo_leitura_balanca_ms: int
    tempo_limite_posicionamento_ms: int
    tempo_limite_pesagem_ms: int
    tempo_limite_saida_balanca_ms: int
    heartbeat_ms: int
    limite_sem_heartbeat_ms: int
    intervalo_peso_ms: int
    intervalo_imagem_ms: int


@dataclass(frozen=True)
class Configuracao:
    banco: ConfiguracaoBanco
    seguranca: ConfiguracaoSeguranca
    # Fuso que define o "hoje" e os horários das faixas (spec 008 §6.1).
    patio_fuso: ZoneInfo
    # Paginação das listas (spec 007 §3.3).
    tamanho_pagina_padrao: int
    tamanho_pagina_maximo: int
    operacao: ConfiguracaoOperacao
    autoatendimento: ConfiguracaoAutoatendimento | None = None


def _obrigatoria(ambiente: Mapping[str, str], nome: str) -> str:
    valor = ambiente.get(nome, "").strip()
    if not valor:
        raise ErroConfiguracao(f"variável obrigatória ausente: {nome}")
    return valor


def _inteiro(ambiente: Mapping[str, str], nome: str, minimo: int, maximo: int) -> int:
    texto = _obrigatoria(ambiente, nome)
    if not texto.isdigit() or not minimo <= int(texto) <= maximo:
        raise ErroConfiguracao(f"{nome} deve ser um inteiro de {minimo} a {maximo}")
    return int(texto)


def _decimal(
    ambiente: Mapping[str, str], nome: str, padrao: str | None = None
) -> Decimal:
    texto = ambiente.get(nome, "").strip() or padrao
    if texto is None:
        raise ErroConfiguracao(f"variável obrigatória ausente: {nome}")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ErroConfiguracao(f"{nome} deve ser um número decimal") from None
    if not valor.is_finite():
        raise ErroConfiguracao(f"{nome} deve ser um número decimal")
    return valor


def ler_configuracao_operacao(ambiente: Mapping[str, str]) -> ConfiguracaoOperacao:
    def ms(nome: str) -> int:
        return _inteiro(ambiente, nome, 1, 24 * 3600 * 1000)

    heartbeat = ms("PESAGEM_TEMPO_REAL_HEARTBEAT_MS")
    limite = ms("PESAGEM_TEMPO_REAL_LIMITE_SEM_HEARTBEAT_MS")
    if limite <= heartbeat:
        # Spec 009 §6.2: senão a tela ficaria "desatualizada" entre dois heartbeats.
        raise ErroConfiguracao(
            "PESAGEM_TEMPO_REAL_LIMITE_SEM_HEARTBEAT_MS deve ser maior que "
            "PESAGEM_TEMPO_REAL_HEARTBEAT_MS"
        )
    return ConfiguracaoOperacao(
        # Ausente = SIMULADO (spec 004 §5.3); o texto é conferido por `selecionar_modo`.
        modo_balanca=ambiente.get("PESAGEM_BALANCA_MODO", ""),
        modo_cancelas=ambiente.get("PESAGEM_CANCELA_MODO", ""),
        modo_cameras=ambiente.get("PESAGEM_CAMERA_MODO", ""),
        peso_minimo_kg=_decimal(ambiente, "PESAGEM_BALANCA_PESO_MINIMO_KG"),
        peso_maximo_kg=_decimal(ambiente, "PESAGEM_BALANCA_PESO_MAXIMO_KG"),
        quantidade_leituras_estaveis=_inteiro(
            ambiente, "PESAGEM_BALANCA_QUANTIDADE_LEITURAS_ESTAVEIS", 1, 1_000
        ),
        variacao_maxima_kg=_decimal(ambiente, "PESAGEM_BALANCA_VARIACAO_MAXIMA_KG"),
        janela_estabilidade_ms=ms("PESAGEM_BALANCA_JANELA_ESTABILIDADE_MS"),
        # Único com padrão, dado pelo autor (RN-006): 20 kg.
        tolerancia_movimentacao_kg=_decimal(
            ambiente, "PESAGEM_PESAGEM_TOLERANCIA_MOVIMENTACAO_KG", "20"
        ),
        limiar_confianca=_decimal(ambiente, "PESAGEM_LPR_LIMIAR_CONFIANCA"),
        intervalo_analise_ms=ms("PESAGEM_CAMERA_INTERVALO_ANALISE_MS"),
        idade_maxima_imagem_ms=ms("PESAGEM_CAMERA_IDADE_MAXIMA_IMAGEM_MS"),
        intervalo_leitura_balanca_ms=ms("PESAGEM_BALANCA_INTERVALO_LEITURA_MS"),
        tempo_limite_posicionamento_ms=ms(
            "PESAGEM_OPERACAO_TEMPO_LIMITE_POSICIONAMENTO_MS"
        ),
        tempo_limite_pesagem_ms=ms("PESAGEM_OPERACAO_TEMPO_LIMITE_PESAGEM_MS"),
        tempo_limite_saida_balanca_ms=ms(
            "PESAGEM_OPERACAO_TEMPO_LIMITE_SAIDA_BALANCA_MS"
        ),
        heartbeat_ms=heartbeat,
        limite_sem_heartbeat_ms=limite,
        intervalo_peso_ms=ms("PESAGEM_TEMPO_REAL_INTERVALO_PESO_MS"),
        intervalo_imagem_ms=ms("PESAGEM_TEMPO_REAL_INTERVALO_IMAGEM_MS"),
    )


def ler_configuracao_banco(ambiente: Mapping[str, str]) -> ConfiguracaoBanco:
    return ConfiguracaoBanco(
        host=_obrigatoria(ambiente, "PESAGEM_BANCO_HOST"),
        porta=_inteiro(ambiente, "PESAGEM_BANCO_PORTA", 1, 65535),
        nome=_obrigatoria(ambiente, "PESAGEM_BANCO_NOME"),
        usuario=_obrigatoria(ambiente, "PESAGEM_BANCO_USUARIO"),
        senha=_obrigatoria(ambiente, "PESAGEM_BANCO_SENHA"),
    )


def _origens(ambiente: Mapping[str, str]) -> frozenset[str]:
    nome = "PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS"
    origens = [o.strip() for o in _obrigatoria(ambiente, nome).split(",")]
    for origem in origens:
        partes = urlsplit(origem)
        if (
            partes.scheme not in ("http", "https")
            or not partes.hostname
            or partes.path
            or partes.query
            or partes.fragment
        ):
            raise ErroConfiguracao(f"{nome}: cada origem é esquema://host[:porta]")
    return frozenset(origens)


def _autoatendimento(ambiente: Mapping[str, str]) -> ConfiguracaoAutoatendimento | None:
    nome = "PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES"
    texto = ambiente.get(nome, "").strip()
    if not texto:
        return None
    try:
        redes = tuple(ip_network(rede.strip()) for rede in texto.split(","))
    except ValueError:
        raise ErroConfiguracao(
            f"{nome}: cada item é uma rede IPv4 ou IPv6 em CIDR"
        ) from None
    um_ano_s = 365 * 24 * 3600
    return ConfiguracaoAutoatendimento(
        redes=redes,
        tentativas_maximas=_inteiro(
            ambiente, "PESAGEM_SEGURANCA_AUTOATENDIMENTO_TENTATIVAS_MAXIMAS", 1, 1_000
        ),
        bloqueio_s=_inteiro(
            ambiente, "PESAGEM_SEGURANCA_AUTOATENDIMENTO_BLOQUEIO_S", 1, um_ano_s
        ),
    )


def ler_configuracao(ambiente: Mapping[str, str]) -> Configuracao:
    """Tudo o que a partida exige; a primeira falta ou valor inválido interrompe."""
    fuso_nome = _obrigatoria(ambiente, "PESAGEM_PATIO_FUSO")
    try:
        fuso = ZoneInfo(fuso_nome)
    except (ZoneInfoNotFoundError, ValueError):
        raise ErroConfiguracao("PESAGEM_PATIO_FUSO não é um fuso conhecido") from None
    padrao = _inteiro(ambiente, "PESAGEM_GERAL_TAMANHO_PAGINA_PADRAO", 1, 10_000)
    maximo = _inteiro(ambiente, "PESAGEM_GERAL_TAMANHO_PAGINA_MAXIMO", 1, 10_000)
    if padrao > maximo:
        raise ErroConfiguracao(
            "PESAGEM_GERAL_TAMANHO_PAGINA_PADRAO maior que PESAGEM_GERAL_TAMANHO_PAGINA_MAXIMO"
        )
    um_ano_s = 365 * 24 * 3600
    return Configuracao(
        banco=ler_configuracao_banco(ambiente),
        seguranca=ConfiguracaoSeguranca(
            origens_permitidas=_origens(ambiente),
            sessao_tempo_sem_uso_s=_inteiro(
                ambiente, "PESAGEM_SEGURANCA_SESSAO_TEMPO_SEM_USO_S", 1, um_ano_s
            ),
            login_tentativas_maximas=_inteiro(
                ambiente, "PESAGEM_SEGURANCA_LOGIN_TENTATIVAS_MAXIMAS", 1, 1_000
            ),
            login_bloqueio_s=_inteiro(
                ambiente, "PESAGEM_SEGURANCA_LOGIN_BLOQUEIO_S", 1, um_ano_s
            ),
        ),
        patio_fuso=fuso,
        tamanho_pagina_padrao=padrao,
        tamanho_pagina_maximo=maximo,
        operacao=ler_configuracao_operacao(ambiente),
        autoatendimento=_autoatendimento(ambiente),
    )
