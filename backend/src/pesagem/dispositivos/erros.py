"""Erros de configuração da camada de dispositivos (`CONVENCOES.md` §4.5).

Falhas de operação do equipamento são resultados, não exceções (spec 004, P-2).
"""


class ErroDispositivo(Exception):
    """Base dos erros da camada de dispositivos."""


class ErroConfiguracaoDispositivo(ErroDispositivo):
    """Valor de configuração inválido: o sistema não inicia com ele."""


class ErroModoIndisponivel(ErroDispositivo):
    """Modo `REAL` pedido sem implementação real: nunca cai para o simulado."""
