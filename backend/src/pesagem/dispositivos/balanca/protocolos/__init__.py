"""Registro dos protocolos de balança: nome em `PESAGEM_BALANCA_PROTOCOLO` → classe
(RF-030; spec 029 §5.3).

Vazio de propósito: nenhum modelo foi integrado (Q-01), então o modo `REAL` não
sobe. Cada modelo entra como `<modelo>.py` + uma linha aqui, testado com quadros
reais de `docs/equipamentos/` (roteiro em `docs/equipamentos/README.md`).
"""

from pesagem.dispositivos.balanca.interface import ProtocoloBalanca

PROTOCOLOS: dict[str, type[ProtocoloBalanca]] = {}
