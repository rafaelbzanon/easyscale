"""Hash de senha e de identificador de sessão (spec 012 §6.1, §6.7; ADR-0004 §4.1).

Só a biblioteca padrão. O hash guarda o algoritmo e os parâmetros, para que
valores maiores no futuro não invalidem as senhas existentes.
"""

import base64
import hashlib
import hmac
import secrets

_N, _R, _P, _DKLEN, _SAL_BYTES = 2**14, 8, 5, 64, 16


def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode()


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(_SAL_BYTES)
    derivada = hashlib.scrypt(senha.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${_b64(sal)}${_b64(derivada)}"


def conferir_senha(senha: str, senha_hash: str) -> bool:
    """Hash em formato desconhecido nunca confere (na dúvida, sem acesso)."""
    partes = senha_hash.split("$")
    if len(partes) != 6 or partes[0] != "scrypt":
        return False
    n, r, p = (int(x) for x in partes[1:4])
    esperada = base64.b64decode(partes[5])
    derivada = hashlib.scrypt(
        senha.encode(),
        salt=base64.b64decode(partes[4]),
        n=n,
        r=r,
        p=p,
        dklen=len(esperada),
    )
    return hmac.compare_digest(derivada, esperada)


# Login inexistente também paga um scrypt, para o tempo não revelar nada (§6.8).
HASH_FICTICIO = gerar_hash_senha(secrets.token_urlsafe(16))


def novo_identificador_sessao() -> str:
    return secrets.token_urlsafe(32)


def resumo(texto: str) -> str:
    """SHA-256 em hexadecimal: o banco guarda só isto da sessão e da chave de tentativa."""
    return hashlib.sha256(texto.encode()).hexdigest()
