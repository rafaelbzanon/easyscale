"""Imagens das decisões, no banco e na mesma transação da decisão (RN-022; spec 014 §10)."""

from datetime import datetime

from sqlalchemy import Connection, RowMapping, text


class RepositorioImagem:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def salvar(
        self,
        conteudo: bytes,
        origem: str,
        capturada_em: datetime,
        roi: tuple[int, int, int, int] | None = None,
    ) -> int:
        """`roi` é (x, y, largura, altura), em pixels da imagem."""
        x, y, largura, altura = roi if roi is not None else (None, None, None, None)
        id_criado: int = self._conexao.execute(
            text(
                "INSERT INTO imagem_decisao (conteudo, origem, capturada_em, roi_x, "
                "roi_y, roi_largura, roi_altura) VALUES (:c, :o, :em, :x, :y, :l, :a) "
                "RETURNING id"
            ),
            {
                "c": conteudo,
                "o": origem,
                "em": capturada_em,
                "x": x,
                "y": y,
                "l": largura,
                "a": altura,
            },
        ).scalar_one()
        return id_criado

    def obter(self, imagem_id: int) -> RowMapping | None:
        """Dados da imagem (spec 011 §5.3), sem os bytes."""
        return (
            self._conexao.execute(
                text(
                    "SELECT i.id, i.origem, i.capturada_em, i.roi_x, i.roi_y, i.roi_largura, "
                    "i.roi_altura, i.conteudo IS NULL AS excluida, i.excluida_por, "
                    "u.nome AS excluida_por_nome, i.excluida_em, i.motivo_exclusao "
                    "FROM imagem_decisao i LEFT JOIN usuario u ON u.id = i.excluida_por "
                    "WHERE i.id = :id"
                ),
                {"id": imagem_id},
            )
            .mappings()
            .one_or_none()
        )

    def conteudo(self, imagem_id: int) -> bytes | None:
        """`None` se a imagem não existe ou foi excluída; quem chama distingue pelo `obter`."""
        dados = self._conexao.execute(
            text("SELECT conteudo FROM imagem_decisao WHERE id = :id"),
            {"id": imagem_id},
        ).scalar_one_or_none()
        return None if dados is None else bytes(dados)

    def excluir(
        self, imagem_id: int, responsavel_id: int, motivo: str, em: datetime
    ) -> bool:
        """Apaga só os bytes (RN-022). Um único UPDATE condicional: de duas exclusões
        simultâneas, só uma acha os bytes (spec 011)."""
        return (
            self._conexao.execute(
                text(
                    "UPDATE imagem_decisao SET conteudo = NULL, excluida_por = :r, "
                    "excluida_em = :em, motivo_exclusao = :m WHERE id = :id "
                    "AND conteudo IS NOT NULL RETURNING id"
                ),
                {"id": imagem_id, "r": responsavel_id, "m": motivo, "em": em},
            ).one_or_none()
            is not None
        )
