"""Cria o primeiro administrador (spec 012 §6.10; ADR-0004 §4.1 item 7).

Uso, na instalação: `python -m pesagem.api.criar_administrador`, com as
variáveis `PESAGEM_BANCO_*`. A senha só é pedida no terminal, sem eco, duas
vezes: nunca por argumento nem por variável de ambiente.
"""

import getpass
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime

from pesagem.api.senha import gerar_hash_senha
from pesagem.config import ErroConfiguracao, ler_configuracao_banco
from pesagem.persistencia.banco import Engine, criar_engine, transacao
from pesagem.persistencia.erros import ErroDuplicidade, ErroPersistencia


class ErroCriacaoAdministrador(Exception):
    pass


def criar_administrador(
    engine: Engine,
    perguntar: Callable[[str], str] = input,
    perguntar_senha: Callable[[str], str] = getpass.getpass,
) -> int:
    nome = perguntar("Nome: ").strip()
    login = perguntar("Login: ").strip()
    senha = perguntar_senha("Senha: ")
    if not nome or not login or " " in login:
        raise ErroCriacaoAdministrador(
            "nome e login são obrigatórios; login sem espaço"
        )
    if not senha:
        raise ErroCriacaoAdministrador("a senha não pode ser vazia")
    if perguntar_senha("Repita a senha: ") != senha:
        raise ErroCriacaoAdministrador("as senhas não conferem")
    try:
        with transacao(engine) as t:
            # P-7: só sem administrador ativo; a checagem e a criação vão juntas.
            if t.usuarios.existe_administrador_ativo():
                raise ErroCriacaoAdministrador("já existe um administrador ativo")
            usuario_id = t.usuarios.criar_usuario(
                nome, login, gerar_hash_senha(senha), "ADMINISTRADOR"
            )
            if usuario_id is None:
                raise ErroCriacaoAdministrador(
                    "perfil ADMINISTRADOR ausente: rode as migrações"
                )
            t.acesso.auditar(
                "USUARIO_CRIADO", datetime.now(UTC), usuario_afetado_id=usuario_id
            )
    except ErroDuplicidade:
        raise ErroCriacaoAdministrador("login já existe") from None
    return usuario_id


def main(argumentos: list[str]) -> int:
    if argumentos:
        print(
            "Este comando não aceita argumentos: a senha é pedida no terminal.",
            file=sys.stderr,
        )
        return 2
    try:
        engine = criar_engine(ler_configuracao_banco(os.environ))
        usuario_id = criar_administrador(engine)
    except (ErroCriacaoAdministrador, ErroConfiguracao, ErroPersistencia) as erro:
        print(f"Nada foi criado: {erro}.", file=sys.stderr)
        return 1
    print(f"Administrador criado (id {usuario_id}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
