"""Testes da localização com OpenCV (spec 005 §6.2, passo 2; P-1).

As imagens são sintéticas, geradas pelo próprio teste: não há dado pessoal
(P-7). Os parâmetros valem só para estas imagens; não são valores calibrados.
"""

import math

import cv2
import numpy as np
import pytest
from cv2.typing import MatLike

from pesagem.lpr.erros import ErroConfiguracaoLpr
from pesagem.lpr.localizacao import ParametrosLocalizacao, localizar_placas
from pesagem.lpr.resultado import Roi

PARAMETROS = ParametrosLocalizacao(
    limiar_bordas_inferior=50,
    limiar_bordas_superior=150,
    area_minima_px=2000,
    proporcao_minima=2.0,
    proporcao_maxima=6.0,
    maximo_rois=5,
)
# Retângulo da placa desenhada: canto superior esquerdo e inferior direito.
PLACA_X1, PLACA_Y1, PLACA_X2, PLACA_Y2 = 200, 200, 459, 259


def imagem_com_placa() -> MatLike:
    imagem = np.full((480, 640, 3), 100, np.uint8)
    cv2.rectangle(imagem, (PLACA_X1, PLACA_Y1), (PLACA_X2, PLACA_Y2), (255,) * 3, -1)
    cv2.rectangle(imagem, (PLACA_X1, PLACA_Y1), (PLACA_X2, PLACA_Y2), (0,) * 3, 3)
    cv2.putText(
        imagem, "ABC1D23", (215, 245), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,) * 3, 3
    )
    return imagem


def contem_placa(roi: Roi) -> bool:
    return (
        roi.x <= PLACA_X1
        and roi.y <= PLACA_Y1
        and roi.x + roi.largura > PLACA_X2
        and roi.y + roi.altura > PLACA_Y2
    )


def test_encontra_roi_que_contem_a_placa() -> None:
    """CA-006."""
    rois = localizar_placas(imagem_com_placa(), PARAMETROS)
    assert any(contem_placa(roi) for roi in rois)


def test_imagem_em_tons_de_cinza_tambem_e_aceita() -> None:
    """CA-006: o pré-processamento aceita imagem já em cinza."""
    cinza = cv2.cvtColor(imagem_com_placa(), cv2.COLOR_BGR2GRAY)
    assert any(contem_placa(roi) for roi in localizar_placas(cinza, PARAMETROS))


def test_imagem_sem_placa_nao_tem_roi() -> None:
    """CA-007."""
    assert localizar_placas(np.full((480, 640, 3), 100, np.uint8), PARAMETROS) == ()


def test_rois_ordenadas_pela_maior_area_e_limitadas() -> None:
    """§6.2: maior área primeiro, até `maximo_rois`."""
    imagem = np.full((480, 640, 3), 100, np.uint8)
    cv2.rectangle(imagem, (20, 20), (219, 79), (255,) * 3, -1)
    cv2.rectangle(imagem, (20, 300), (339, 389), (255,) * 3, -1)
    rois = localizar_placas(imagem, PARAMETROS)
    areas = [roi.largura * roi.altura for roi in rois]
    assert len(rois) >= 2
    assert areas == sorted(areas, reverse=True)

    so_uma = ParametrosLocalizacao(50, 150, 2000, 2.0, 6.0, maximo_rois=1)
    assert localizar_placas(imagem, so_uma) == rois[:1]


def test_descarta_contornos_fora_da_proporcao_ou_pequenos() -> None:
    """§6.2: um quadrado e um retângulo pequeno não viram ROI."""
    imagem = np.full((480, 640, 3), 100, np.uint8)
    cv2.rectangle(imagem, (50, 50), (249, 249), (255,) * 3, -1)
    cv2.rectangle(imagem, (400, 400), (439, 414), (255,) * 3, -1)
    assert localizar_placas(imagem, PARAMETROS) == ()


@pytest.mark.parametrize(
    "parametros",
    [
        (math.nan, 150, 2000, 2.0, 6.0, 5),
        (50, math.inf, 2000, 2.0, 6.0, 5),
        (-1, 150, 2000, 2.0, 6.0, 5),
        (150, 150, 2000, 2.0, 6.0, 5),
        (50, 150, 0, 2.0, 6.0, 5),
        (50, 150, 2000, 0.0, 6.0, 5),
        (50, 150, 2000, 6.0, 2.0, 5),
        (50, 150, 2000, 2.0, 6.0, 0),
    ],
)
def test_parametros_invalidos_levantam_erro(
    parametros: tuple[float, float, int, float, float, int],
) -> None:
    """§5.2: sem valor "chutado"; o sistema não inicia."""
    with pytest.raises(ErroConfiguracaoLpr):
        ParametrosLocalizacao(*parametros)
