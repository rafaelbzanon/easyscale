"""Validação de CPF, CNPJ e placa digitada (spec 007 §5 e §6.1)."""

from pesagem.dominio.placa.normalizacao import PlacaNormalizada, normalizar_placa

_PESOS_CNPJ = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _digito_mod11(valores: list[int], pesos: tuple[int, ...] | range) -> int:
    resto = sum(v * p for v, p in zip(valores, pesos, strict=False)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit() or len(set(cpf)) == 1:
        return False
    numeros = [int(c) for c in cpf]
    primeiro = _digito_mod11(numeros[:9], range(10, 1, -1))
    segundo = _digito_mod11(numeros[:10], range(11, 1, -1))
    return numeros[9:] == [primeiro, segundo]


def cnpj_valido(cnpj: str) -> bool:
    """Aceita o CNPJ alfanumérico da Receita: 12 posições de 0-9 ou A-Z e 2 dígitos
    verificadores numéricos, com o valor de cada caractere = código ASCII − 48
    (IN RFB nº 2.229/2024). Para CNPJ só numérico, o cálculo é o tradicional."""
    if len(cnpj) != 14 or not cnpj[12:].isdigit() or len(set(cnpj)) == 1:
        return False
    if not all(c.isdigit() or "A" <= c <= "Z" for c in cnpj[:12]):
        return False
    valores = [ord(c) - 48 for c in cnpj]
    primeiro = _digito_mod11(valores[:12], _PESOS_CNPJ[1:])
    segundo = _digito_mod11(valores[:13], _PESOS_CNPJ)
    return valores[12:] == [primeiro, segundo]


def mascarar_cpf(cpf: str) -> str:
    """Esconde os 3 primeiros dígitos e o verificador: `***.456.789-**`."""
    return f"***.{cpf[3:6]}.{cpf[6:9]}-**"


def normalizar_placa_digitada(placa: str) -> PlacaNormalizada | None:
    """Placa digitada não recebe correção de OCR: se precisaria, é inválida (§6.1)."""
    resultado = normalizar_placa(placa)
    if not isinstance(resultado, PlacaNormalizada) or resultado.correcoes:
        return None
    return resultado


def so_digitos(valor: str) -> str:
    if not valor.isdigit():
        raise ValueError("só dígitos")
    return valor


def email_valido(valor: str) -> str:
    """Formato básico: algo@dominio.tld, sem espaço (spec 007 §5.1)."""
    usuario, arroba, dominio = valor.partition("@")
    if not arroba or not usuario or "." not in dominio.strip(".") or " " in valor:
        raise ValueError("e-mail inválido")
    return valor
