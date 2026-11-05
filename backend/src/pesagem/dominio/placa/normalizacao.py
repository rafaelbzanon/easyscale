"""Normalização da placa lida pelo OCR (spec 003; RF-008, RN-017).

Só corrige o que a tabela da spec §5.1 prevê, e só nas posições cujo tipo
(letra ou dígito) é igual nos formatos antigo e Mercosul. A posição 5 nunca é
corrigida: ela é o que distingue os dois formatos. Na dúvida, rejeita
(fail-safe, RNF-009); uma rejeição nunca traz palpite de placa.
"""

from dataclasses import dataclass
from enum import StrEnum

SEPARADORES = frozenset(" -.")
LETRAS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITOS = frozenset("0123456789")
# Conjunto ASCII explícito: `str.upper()` transformaria "ß" em "SS" e "ı" em "I".
CARACTERES_PERMITIDOS = LETRAS | DIGITOS | frozenset("abcdefghijklmnopqrstuvwxyz")

COMPRIMENTO_PLACA = 7
POSICOES_LETRA = (1, 2, 3)
POSICOES_DIGITO = (4, 6, 7)
POSICAO_FORMATO = 5

# Spec §5.1 (P-1): pares de confusão do OCR, em mão dupla.
DIGITO_PARA_LETRA = {
    "0": "O",
    "1": "I",
    "8": "B",
    "5": "S",
    "2": "Z",
    "6": "G",
    "4": "A",
    "7": "T",
}
LETRA_PARA_DIGITO = {letra: digito for digito, letra in DIGITO_PARA_LETRA.items()}

# Resolução CONTRAN nº 780/2019, Anexo II: conversão da posição 5 da placa
# antiga para a Mercosul (spec §5.2, P-3).
CONVERSAO_MERCOSUL = dict(zip("0123456789", "ABCDEFGHIJ", strict=True))


class FormatoPlaca(StrEnum):
    ANTIGO = "ANTIGO"
    MERCOSUL = "MERCOSUL"


class MotivoRejeicaoPlaca(StrEnum):
    VAZIA = "VAZIA"
    CARACTERE_INVALIDO = "CARACTERE_INVALIDO"
    COMPRIMENTO_INVALIDO = "COMPRIMENTO_INVALIDO"
    FORMATO_INVALIDO = "FORMATO_INVALIDO"


@dataclass(frozen=True)
class CorrecaoCaractere:
    posicao: int
    lido: str
    corrigido: str


@dataclass(frozen=True)
class PlacaNormalizada:
    placa_normalizada: str
    formato: FormatoPlaca
    correcoes: tuple[CorrecaoCaractere, ...]
    chave_comparacao: str


@dataclass(frozen=True)
class RejeicaoPlaca:
    motivo: MotivoRejeicaoPlaca
    placa_lida: str


def normalizar_placa(placa_lida: str) -> PlacaNormalizada | RejeicaoPlaca:
    """Normaliza a placa lida; motivos de rejeição na ordem da spec §6."""
    caracteres: list[str] = []
    for caractere in placa_lida:
        if caractere in SEPARADORES:
            continue
        if caractere not in CARACTERES_PERMITIDOS:
            return _rejeitar(placa_lida, MotivoRejeicaoPlaca.CARACTERE_INVALIDO)
        caracteres.append(caractere.upper())

    if not caracteres:
        return _rejeitar(placa_lida, MotivoRejeicaoPlaca.VAZIA)
    if len(caracteres) != COMPRIMENTO_PLACA:
        return _rejeitar(placa_lida, MotivoRejeicaoPlaca.COMPRIMENTO_INVALIDO)

    correcoes: list[CorrecaoCaractere] = []
    for posicao in POSICOES_LETRA:
        if not _ajustar(caracteres, posicao, LETRAS, DIGITO_PARA_LETRA, correcoes):
            return _rejeitar(placa_lida, MotivoRejeicaoPlaca.FORMATO_INVALIDO)
    for posicao in POSICOES_DIGITO:
        if not _ajustar(caracteres, posicao, DIGITOS, LETRA_PARA_DIGITO, correcoes):
            return _rejeitar(placa_lida, MotivoRejeicaoPlaca.FORMATO_INVALIDO)

    placa = "".join(caracteres)
    caractere_formato = placa[POSICAO_FORMATO - 1]
    if caractere_formato in DIGITOS:
        formato = FormatoPlaca.ANTIGO
        chave = _trocar(placa, POSICAO_FORMATO, CONVERSAO_MERCOSUL[caractere_formato])
    else:
        formato = FormatoPlaca.MERCOSUL
        chave = placa
    return PlacaNormalizada(placa, formato, tuple(correcoes), chave)


def _ajustar(
    caracteres: list[str],
    posicao: int,
    esperados: frozenset[str],
    tabela: dict[str, str],
    correcoes: list[CorrecaoCaractere],
) -> bool:
    lido = caracteres[posicao - 1]
    if lido in esperados:
        return True
    corrigido = tabela.get(lido)
    if corrigido is None:
        return False
    caracteres[posicao - 1] = corrigido
    correcoes.append(CorrecaoCaractere(posicao, lido, corrigido))
    return True


def _trocar(placa: str, posicao: int, caractere: str) -> str:
    return placa[: posicao - 1] + caractere + placa[posicao:]


def _rejeitar(placa_lida: str, motivo: MotivoRejeicaoPlaca) -> RejeicaoPlaca:
    return RejeicaoPlaca(motivo, placa_lida)
