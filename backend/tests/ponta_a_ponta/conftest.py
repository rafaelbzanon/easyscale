"""Fixtures da integração (PostgreSQL em contêiner, relógio, cliente HTTP) e o `admin`.

Fica num pacote (`__init__.py`) para o módulo não se chamar `conftest` e não
atropelar o `from conftest import` dos testes de integração.
"""

from ponta_a_ponta.apoio import (  # noqa: F401
    admin,
    banco,
    cliente,
    configuracao_banco,
    engine,
    relogio,
)
