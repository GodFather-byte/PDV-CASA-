"""Senhas de operadores: guardadas com PBKDF2 + sal e comparadas sem diferenciar
maiúsculas de minúsculas (requisito do manual: 'não há diferença entre letras
maiúsculas e minúsculas' na escolha do funcionário e da senha)."""
from __future__ import annotations

import hashlib
import hmac
import os

_ITERACOES = 60_000


def _normalizar(senha: str) -> bytes:
    return (senha or "").strip().upper().encode("utf-8")


def gerar_hash(senha: str) -> str:
    sal = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", _normalizar(senha), sal, _ITERACOES)
    return f"pbkdf2${_ITERACOES}${sal.hex()}${h.hex()}"


def conferir(senha: str, armazenado: str | None) -> bool:
    if not armazenado:
        return False
    try:
        _, iteracoes, sal_hex, hash_hex = armazenado.split("$")
        h = hashlib.pbkdf2_hmac("sha256", _normalizar(senha), bytes.fromhex(sal_hex), int(iteracoes))
        return hmac.compare_digest(h.hex(), hash_hex)
    except (ValueError, TypeError):
        return False
