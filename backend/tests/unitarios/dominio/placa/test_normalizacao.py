"""Testes da normalização de placa (spec 003, `normalizacao-placa`)."""

import pytest

from pesagem.dominio.placa.normalizacao import (
    CorrecaoCaractere,
    FormatoPlaca,
    MotivoRejeicaoPlaca,
    PlacaNormalizada,
    RejeicaoPlaca,
    normalizar_placa,
)

PARES_CONFUSAO = [
    ("0", "O"),
    ("1", "I"),
    ("8", "B"),
    ("5", "S"),
    ("2", "Z"),
    ("6", "G"),
    ("4", "A"),
    ("7", "T"),
]


def normalizada(placa_lida: str) -> PlacaNormalizada:
    resultado = normalizar_placa(placa_lida)
    assert isinstance(resultado, PlacaNormalizada), resultado
    return resultado


def rejeitada(placa_lida: str) -> RejeicaoPlaca:
    resultado = normalizar_placa(placa_lida)
    assert isinstance(resultado, RejeicaoPlaca), resultado
    return resultado


def test_aceita_placa_antiga_sem_correcao() -> None:
    """CA-001, RN-017."""
    resultado = normalizada("ABC1234")
    assert resultado.placa_normalizada == "ABC1234"
    assert resultado.formato is FormatoPlaca.ANTIGO
    assert resultado.correcoes == ()


def test_aceita_placa_mercosul_sem_correcao() -> None:
    """CA-002, RN-017."""
    resultado = normalizada("ABC1D23")
    assert resultado.placa_normalizada == "ABC1D23"
    assert resultado.formato is FormatoPlaca.MERCOSUL
    assert resultado.correcoes == ()


@pytest.mark.parametrize(
    "placa_lida", ["abc-1234", " ABC 1234 ", "ABC.1234", "a.b c-1 2.3 4"]
)
def test_remove_separadores_e_minusculas_sem_registrar_correcao(
    placa_lida: str,
) -> None:
    """CA-003 (P-4)."""
    resultado = normalizada(placa_lida)
    assert resultado.placa_normalizada == "ABC1234"
    assert resultado.correcoes == ()


@pytest.mark.parametrize(("digito", "letra"), PARES_CONFUSAO)
@pytest.mark.parametrize("posicao", [1, 2, 3])
def test_corrige_digito_em_posicao_de_letra(
    posicao: int, digito: str, letra: str
) -> None:
    """CA-004 (spec §5.1)."""
    esperada = list("XYW1234")
    esperada[posicao - 1] = letra
    lida = esperada.copy()
    lida[posicao - 1] = digito
    resultado = normalizada("".join(lida))
    assert resultado.placa_normalizada == "".join(esperada)
    assert resultado.correcoes == (CorrecaoCaractere(posicao, digito, letra),)


@pytest.mark.parametrize(("digito", "letra"), PARES_CONFUSAO)
@pytest.mark.parametrize("posicao", [4, 6, 7])
def test_corrige_letra_em_posicao_de_digito(
    posicao: int, digito: str, letra: str
) -> None:
    """CA-004, CA-006 (spec §5.1)."""
    esperada = list("XYW9C99")
    esperada[posicao - 1] = digito
    lida = esperada.copy()
    lida[posicao - 1] = letra
    resultado = normalizada("".join(lida))
    assert resultado.placa_normalizada == "".join(esperada)
    assert resultado.correcoes == (CorrecaoCaractere(posicao, letra, digito),)


def test_exemplo_da_spec_a8c1234() -> None:
    """CA-004."""
    resultado = normalizada("A8C1234")
    assert resultado.placa_normalizada == "ABC1234"
    assert resultado.correcoes == (CorrecaoCaractere(2, "8", "B"),)


def test_registra_varias_correcoes_em_ordem_de_posicao() -> None:
    """CA-004, CA-014."""
    resultado = normalizada("0BCI2S4")
    assert resultado.placa_normalizada == "OBC1254"
    assert resultado.correcoes == (
        CorrecaoCaractere(1, "0", "O"),
        CorrecaoCaractere(4, "I", "1"),
        CorrecaoCaractere(6, "S", "5"),
    )


@pytest.mark.parametrize(
    ("placa_lida", "formato"),
    [("ABC1O23", FormatoPlaca.MERCOSUL), ("ABC1023", FormatoPlaca.ANTIGO)],
)
def test_nao_corrige_posicao_5(placa_lida: str, formato: FormatoPlaca) -> None:
    """CA-005."""
    resultado = normalizada(placa_lida)
    assert resultado.placa_normalizada == placa_lida
    assert resultado.formato is formato
    assert resultado.correcoes == ()


def test_corrige_s_na_posicao_6() -> None:
    """CA-007."""
    resultado = normalizada("ABC53S4")
    assert resultado.placa_normalizada == "ABC5354"
    assert resultado.correcoes == (CorrecaoCaractere(6, "S", "5"),)


def test_s_na_posicao_5_indica_mercosul_sem_correcao() -> None:
    """CA-005, CA-007: o exemplo original da spec, com o S na posição 5."""
    resultado = normalizada("ABC5S34")
    assert resultado.placa_normalizada == "ABC5S34"
    assert resultado.formato is FormatoPlaca.MERCOSUL
    assert resultado.correcoes == ()


@pytest.mark.parametrize("placa_lida", ["ABCQ234", "AB91234", "ABC12K4", "ABC123X"])
def test_rejeita_caractere_fora_da_tabela_em_posicao_errada(placa_lida: str) -> None:
    """CA-007."""
    assert rejeitada(placa_lida).motivo is MotivoRejeicaoPlaca.FORMATO_INVALIDO


@pytest.mark.parametrize("placa_lida", ["", " ", " - ", "..."])
def test_rejeita_placa_vazia(placa_lida: str) -> None:
    """CA-008."""
    assert rejeitada(placa_lida).motivo is MotivoRejeicaoPlaca.VAZIA


@pytest.mark.parametrize(
    "placa_lida",
    ["ABC*234", "ÁBC1234", "|ABC1234", "ABC1234\t", "ABC_1234", "ABCß234", "ıBC1234"],
)
def test_rejeita_caractere_invalido(placa_lida: str) -> None:
    """CA-009 (P-4: só espaço, hífen e ponto são separadores)."""
    assert rejeitada(placa_lida).motivo is MotivoRejeicaoPlaca.CARACTERE_INVALIDO


@pytest.mark.parametrize("placa_lida", ["ABC123", "ABC12345", "A"])
def test_rejeita_comprimento_invalido(placa_lida: str) -> None:
    """CA-010."""
    assert rejeitada(placa_lida).motivo is MotivoRejeicaoPlaca.COMPRIMENTO_INVALIDO


@pytest.mark.parametrize(
    ("placa_lida", "motivo"),
    [
        ("ABC*2345", MotivoRejeicaoPlaca.CARACTERE_INVALIDO),
        ("ABCQ2345", MotivoRejeicaoPlaca.COMPRIMENTO_INVALIDO),
        ("*", MotivoRejeicaoPlaca.CARACTERE_INVALIDO),
    ],
)
def test_devolve_o_primeiro_motivo_na_ordem_da_spec(
    placa_lida: str, motivo: MotivoRejeicaoPlaca
) -> None:
    """CA-011."""
    assert rejeitada(placa_lida).motivo is motivo


@pytest.mark.parametrize("placa_lida", ["ABC*234", " abc-12 ", "ABCQ234", ""])
def test_rejeicao_preserva_placa_lida(placa_lida: str) -> None:
    """CA-012."""
    assert rejeitada(placa_lida).placa_lida == placa_lida


@pytest.mark.parametrize(
    ("digito", "letra"), list(zip("0123456789", "ABCDEFGHIJ", strict=True))
)
def test_chave_converte_placa_antiga_conforme_anexo_ii(digito: str, letra: str) -> None:
    """CA-013 (Resolução CONTRAN nº 780/2019, Anexo II)."""
    antiga = normalizada(f"ABC1{digito}34")
    mercosul = normalizada(f"ABC1{letra}34")
    assert antiga.chave_comparacao == f"ABC1{letra}34"
    assert antiga.placa_normalizada == f"ABC1{digito}34"
    assert mercosul.chave_comparacao == mercosul.placa_normalizada
    assert antiga.chave_comparacao == mercosul.chave_comparacao


def test_chave_do_exemplo_oficial() -> None:
    """CA-013: exemplo do Anexo II, ABC1234 -> ABC1C34."""
    assert normalizada("ABC1234").chave_comparacao == "ABC1C34"
    assert normalizada("ABC1C34").chave_comparacao == "ABC1C34"


@pytest.mark.parametrize("letra", list("KLMNOPQRSTUVWXYZ"))
def test_chave_de_mercosul_com_letra_k_a_z_e_a_propria_placa(letra: str) -> None:
    """CA-013."""
    assert normalizada(f"ABC1{letra}34").chave_comparacao == f"ABC1{letra}34"


def test_chave_nao_entra_nas_correcoes() -> None:
    """CA-013: a conversão da chave não é correção."""
    resultado = normalizada("ABC1234")
    assert resultado.correcoes == ()
    assert resultado.placa_normalizada == "ABC1234"


def test_placa_corrigida_nao_e_marcada_para_operador() -> None:
    """CA-014 (P-2): o resultado só traz as correções, sem bloquear a autorização."""
    resultado = normalizada("A8C1234")
    assert set(vars(resultado)) == {
        "placa_normalizada",
        "formato",
        "correcoes",
        "chave_comparacao",
    }
