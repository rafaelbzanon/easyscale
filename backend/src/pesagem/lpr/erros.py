"""Erros de configuração do LPR (`CONVENCOES.md` §4.5).

Falhas de operação (imagem, leitor) são resultados, não exceções (spec 005 §7).
"""


class ErroLpr(Exception):
    """Base dos erros do LPR."""


class ErroConfiguracaoLpr(ErroLpr):
    """Valor de configuração inválido: o sistema não inicia com ele."""
