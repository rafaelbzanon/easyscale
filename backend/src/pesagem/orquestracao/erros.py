"""Erros da orquestração (`CONVENCOES.md` §4.5)."""


class ErroOrquestracao(Exception):
    """Base dos erros da orquestração."""


class ErroConfiguracaoOrquestracao(ErroOrquestracao):
    """Valor de configuração ausente ou inválido: o sistema não inicia."""


class ErroOperacaoNaoOcupaBalanca(ErroOrquestracao):
    """Liberação pedida para pesagem que não aguarda a balança (spec 015 §6.8)."""


class ErroLiberacaoEntrada(ErroOrquestracao):
    """Liberação manual de entrada recusada; `codigo` segue a spec 009 §6.4."""

    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo
