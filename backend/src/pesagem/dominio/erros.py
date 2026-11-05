"""Erros do domínio (`CONVENCOES.md` §4.5)."""


class ErroDominio(Exception):
    """Base dos erros do domínio."""


class ErroParametrosInvalidos(ErroDominio):
    """Configuração incoerente: o sistema não deve operar com ela (fail-safe)."""


class ErroTipoOperacaoInvalido(ErroDominio):
    """`tipo_operacao` fora de `CARGA`/`DESCARGA`."""
