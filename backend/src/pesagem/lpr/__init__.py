"""Reconhecimento de placas: fonte de imagem, ROIs e OCR (spec 005, `pipeline-lpr`).

Só informa o que leu; não normaliza, não aplica limiar e não decide
autorização (`AMBIENTE.md` §4.1). Única camada que importa `cv2` e `easyocr`
(`CONVENCOES.md` P-6). Não grava imagens nem registra placas em log (RNF-013).
"""
