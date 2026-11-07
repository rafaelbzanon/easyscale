"""Agregado usuário: usuários, perfis e sessões (spec 012; ADR-0004)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Connection, text

from pesagem.persistencia.erros import ErroNaoEncontrado


@dataclass(frozen=True)
class Usuario:
    id: int
    nome: str
    login: str
    perfil: str
    ativo: bool
    criado_em: datetime


@dataclass(frozen=True)
class CredencialUsuario:
    usuario_id: int
    senha_hash: str
    ativo: bool


@dataclass(frozen=True)
class SessaoAtual:
    usuario: Usuario
    permissoes: tuple[str, ...]


_USUARIO = (
    "SELECT u.id, u.nome, u.login, p.codigo, u.ativo, u.criado_em "
    "FROM usuario u JOIN perfil p ON p.id = u.perfil_id"
)


class RepositorioUsuario:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def buscar_credencial(self, login: str) -> CredencialUsuario | None:
        linha = self._conexao.execute(
            text(
                "SELECT id, senha_hash, ativo FROM usuario WHERE lower(login) = lower(:l)"
            ),
            {"l": login},
        ).one_or_none()
        return None if linha is None else CredencialUsuario(*linha)

    def obter_usuario(self, usuario_id: int) -> Usuario:
        linha = self._conexao.execute(
            text(f"{_USUARIO} WHERE u.id = :id"), {"id": usuario_id}
        ).one_or_none()
        if linha is None:
            raise ErroNaoEncontrado(str(usuario_id))
        return Usuario(*linha)

    def listar_usuarios(
        self,
        ativo: bool | None,
        perfil: str | None,
        busca: str | None,
        pagina: int,
        tamanho_pagina: int,
    ) -> tuple[list[Usuario], int]:
        condicao = (
            "(CAST(:ativo AS BOOLEAN) IS NULL OR u.ativo = :ativo) "
            "AND (CAST(:perfil AS TEXT) IS NULL OR p.codigo = :perfil) "
            "AND (CAST(:busca AS TEXT) IS NULL OR u.nome ILIKE :busca OR u.login ILIKE :busca)"
        )
        parametros = {
            "ativo": ativo,
            "perfil": perfil,
            "busca": None if busca is None else f"%{_escapar_like(busca)}%",
            "limite": tamanho_pagina,
            "deslocamento": (pagina - 1) * tamanho_pagina,
        }
        linhas = self._conexao.execute(
            text(
                f"{_USUARIO} WHERE {condicao} ORDER BY u.nome, u.id "
                "LIMIT :limite OFFSET :deslocamento"
            ),
            parametros,
        ).all()
        total = self._conexao.execute(
            text(
                "SELECT count(*) FROM usuario u JOIN perfil p ON p.id = u.perfil_id "
                f"WHERE {condicao}"
            ),
            parametros,
        ).scalar_one()
        return [Usuario(*linha) for linha in linhas], int(total)

    def criar_usuario(
        self, nome: str, login: str, senha_hash: str, perfil: str
    ) -> int | None:
        """Devolve `None` se o perfil não existe."""
        criado = self._conexao.execute(
            text(
                "INSERT INTO usuario (nome, login, senha_hash, perfil_id) "
                "SELECT :n, :l, :s, id FROM perfil WHERE codigo = :p RETURNING id"
            ),
            {"n": nome, "l": login, "s": senha_hash, "p": perfil},
        ).scalar_one_or_none()
        return None if criado is None else int(criado)

    def existe_administrador_ativo(self) -> bool:
        return bool(
            self._conexao.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM usuario u JOIN perfil p "
                    "ON p.id = u.perfil_id WHERE p.codigo = 'ADMINISTRADOR' AND u.ativo)"
                )
            ).scalar_one()
        )

    def alterar_ativo(self, usuario_id: int, ativo: bool, em: datetime) -> None:
        """Desativar encerra na hora todas as sessões (spec 012 §6.5)."""
        self._conexao.execute(
            text("UPDATE usuario SET ativo = :a WHERE id = :id"),
            {"a": ativo, "id": usuario_id},
        )
        if not ativo:
            self.encerrar_sessoes_do_usuario(usuario_id, em)

    def redefinir_senha(self, usuario_id: int, senha_hash: str, em: datetime) -> None:
        self._conexao.execute(
            text("UPDATE usuario SET senha_hash = :s WHERE id = :id"),
            {"s": senha_hash, "id": usuario_id},
        )
        self.encerrar_sessoes_do_usuario(usuario_id, em)

    def listar_perfis(self) -> list[tuple[str, tuple[str, ...]]]:
        linhas = self._conexao.execute(
            text(
                "SELECT p.codigo, coalesce(array_agg(pp.permissao ORDER BY pp.permissao) "
                "FILTER (WHERE pp.permissao IS NOT NULL), '{}') FROM perfil p "
                "LEFT JOIN perfil_permissao pp ON pp.perfil_id = p.id "
                "GROUP BY p.codigo ORDER BY p.codigo"
            )
        ).all()
        return [(codigo, tuple(permissoes)) for codigo, permissoes in linhas]

    def criar_sessao(
        self, usuario_id: int, hash_identificador: str, em: datetime
    ) -> None:
        self._conexao.execute(
            text(
                "INSERT INTO sessao (usuario_id, hash_identificador, criada_em, ultimo_uso_em) "
                "VALUES (:u, :h, :em, :em)"
            ),
            {"u": usuario_id, "h": hash_identificador, "em": em},
        )

    def buscar_sessao_valida(
        self,
        hash_identificador: str,
        agora: datetime,
        tempo_sem_uso_s: int,
        renovar: bool,
    ) -> SessaoAtual | None:
        """Aberta, dentro do tempo sem uso e de usuário ativo (spec 012 §6.2, §6.3).

        As permissões vêm do perfil atual, a cada chamada (CA-011).
        """
        linha = self._conexao.execute(
            text(
                "SELECT s.id, s.usuario_id FROM sessao s JOIN usuario u ON u.id = s.usuario_id "
                "WHERE s.hash_identificador = :h AND s.encerrada_em IS NULL AND u.ativo "
                "AND s.ultimo_uso_em > :limite FOR UPDATE OF s"
            ),
            {
                "h": hash_identificador,
                "limite": agora - timedelta(seconds=tempo_sem_uso_s),
            },
        ).one_or_none()
        if linha is None:
            return None
        if renovar:
            self._conexao.execute(
                text("UPDATE sessao SET ultimo_uso_em = :em WHERE id = :id"),
                {"em": agora, "id": linha.id},
            )
        usuario = self.obter_usuario(linha.usuario_id)
        permissoes = self._conexao.execute(
            text(
                "SELECT pp.permissao FROM perfil_permissao pp JOIN perfil p "
                "ON p.id = pp.perfil_id WHERE p.codigo = :p ORDER BY 1"
            ),
            {"p": usuario.perfil},
        ).scalars()
        return SessaoAtual(usuario, tuple(permissoes))

    def encerrar_sessao(self, hash_identificador: str, em: datetime) -> int | None:
        """Devolve o usuário da sessão encerrada, ou `None` se não havia sessão aberta."""
        usuario_id = self._conexao.execute(
            text(
                "UPDATE sessao SET encerrada_em = :em WHERE hash_identificador = :h "
                "AND encerrada_em IS NULL RETURNING usuario_id"
            ),
            {"h": hash_identificador, "em": em},
        ).scalar_one_or_none()
        return None if usuario_id is None else int(usuario_id)

    def encerrar_sessoes_do_usuario(self, usuario_id: int, em: datetime) -> None:
        self._conexao.execute(
            text(
                "UPDATE sessao SET encerrada_em = :em WHERE usuario_id = :u "
                "AND encerrada_em IS NULL"
            ),
            {"u": usuario_id, "em": em},
        )


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
