"""Fonte de posição simulada (spec 015 §5.2). Sem I/O e sem espera real."""

from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum

from pesagem.lpr.fontes.interface import ImagemCapturada
from pesagem.lpr.posicao.interface import LeituraPosicao, ResultadoPosicao
from pesagem.lpr.reconhecedor_simulado import imagem_sintetica

ORIGEM = "posicao-simulada"


class CenarioPosicao(StrEnum):
    CONFIRMADA = "CONFIRMADA"
    AUSENTE = "AUSENTE"
    INCONCLUSIVA = "INCONCLUSIVA"


class FontePosicaoSimulada:
    def __init__(
        self,
        cenario: CenarioPosicao,
        relogio: Callable[[], datetime],
        atraso_captura_ms: int = 0,
    ) -> None:
        self._cenario = cenario
        self._relogio = relogio
        # Simula uma imagem antiga, para testar o limite de idade (ADR-0005 §4.1).
        self._atraso = timedelta(milliseconds=atraso_captura_ms)

    def definir_cenario(self, cenario: CenarioPosicao) -> None:
        self._cenario = cenario

    async def analisar_posicao(self) -> LeituraPosicao:
        capturada_em = self._relogio() - self._atraso
        resultado = ResultadoPosicao[self._cenario.name]
        if resultado is ResultadoPosicao.INCONCLUSIVA:
            return LeituraPosicao(resultado, capturada_em, None)
        imagem = ImagemCapturada(imagem_sintetica(), capturada_em, ORIGEM)
        return LeituraPosicao(resultado, capturada_em, imagem)
