"""Tentativas de acesso e auditoria geral (spec 012 §6.8 e §6.11; spec 013)."""

from datetime import datetime, timedelta

from sqlalchemy import Connection, text


class RepositorioAcesso:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def esta_bloqueado(self, tipo: str, chave: str, agora: datetime) -> bool:
        bloqueado_ate = self._conexao.execute(
            text(
                "SELECT bloqueado_ate FROM tentativa_acesso WHERE tipo = :t AND chave = :c"
            ),
            {"t": tipo, "c": chave},
        ).scalar_one_or_none()
        return bloqueado_ate is not None and bloqueado_ate > agora

    def registrar_falha(
        self, tipo: str, chave: str, maximo: int, bloqueio_s: int, agora: datetime
    ) -> None:
        """Soma uma falha; ao chegar ao máximo, bloqueia. Bloqueio vencido recomeça do zero.

        O `ON CONFLICT` deixa duas falhas simultâneas somarem as duas.
        """
        self._conexao.execute(
            text(
                "INSERT INTO tentativa_acesso AS t (tipo, chave, falhas_seguidas, bloqueado_ate) "
                "VALUES (:t, :c, 1, CASE WHEN 1 >= :max THEN CAST(:ate AS TIMESTAMPTZ) END) "
                "ON CONFLICT (tipo, chave) DO UPDATE SET "
                "falhas_seguidas = CASE WHEN t.bloqueado_ate <= :agora THEN 1 "
                "ELSE t.falhas_seguidas + 1 END, "
                "bloqueado_ate = CASE WHEN (CASE WHEN t.bloqueado_ate <= :agora THEN 1 "
                "ELSE t.falhas_seguidas + 1 END) >= :max THEN CAST(:ate AS TIMESTAMPTZ) END"
            ),
            {
                "t": tipo,
                "c": chave,
                "max": maximo,
                "agora": agora,
                "ate": agora + timedelta(seconds=bloqueio_s),
            },
        )

    def zerar(self, tipo: str, chave: str) -> None:
        self._conexao.execute(
            text("DELETE FROM tentativa_acesso WHERE tipo = :t AND chave = :c"),
            {"t": tipo, "c": chave},
        )

    def auditar(
        self,
        tipo: str,
        em: datetime,
        responsavel_id: int | None = None,
        usuario_afetado_id: int | None = None,
        agendamento_id: int | None = None,
        endereco_origem: str | None = None,
    ) -> None:
        """Sem texto livre: nunca senha, cookie, sessão ou dado digitado (RNF-013)."""
        self._conexao.execute(
            text(
                "INSERT INTO registro_auditoria (tipo, responsavel_id, usuario_afetado_id, "
                "agendamento_id, endereco_origem, ocorrido_em) VALUES (:t, :r, :u, :a, :o, :em)"
            ),
            {
                "t": tipo,
                "r": responsavel_id,
                "u": usuario_afetado_id,
                "a": agendamento_id,
                "o": endereco_origem,
                "em": em,
            },
        )
