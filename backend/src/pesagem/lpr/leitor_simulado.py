"""Leitor de placa simulado: testa o pipeline sem o EasyOCR (spec 005 §5.2)."""

from collections.abc import Sequence

from cv2.typing import MatLike

from pesagem.lpr.resultado import TextoOcr


class LeitorPlacaSimulado:
    def __init__(self, respostas: Sequence[Sequence[TextoOcr] | Exception]) -> None:
        self._respostas = list(respostas)
        # Largura e altura de cada recorte recebido, na ordem.
        self.recortes_recebidos: list[tuple[int, int]] = []

    def ler(self, recorte: MatLike) -> Sequence[TextoOcr]:
        altura, largura = recorte.shape[:2]
        self.recortes_recebidos.append((largura, altura))
        if not self._respostas:
            return ()
        resposta = self._respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta
