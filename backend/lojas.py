"""Cadastro das lojas da nuvem. Cada loja tem o próprio token; o token aparece UMA vez e só o hash fica guardado.

    python -m backend.lojas criar BOATE-CENTRO "Boate Centro"   # mostra o token da loja
    python -m backend.lojas listar                              # todas as lojas e se estão ativas
    python -m backend.lojas novo-token BOATE-CENTRO             # troca o token (o antigo para de funcionar)
    python -m backend.lojas desativar BOATE-CENTRO              # a loja deixa de receber avisos de versão
    python -m backend.lojas ativar BOATE-CENTRO

No PDV da loja, em Configurações > Nuvem: a chave da loja (ex.: BOATE-CENTRO) e o token mostrado aqui.
Usa o mesmo banco da API (PDV_NUVEM_DB_URL).
"""
from __future__ import annotations

import re
import secrets
import sys
from datetime import datetime

from sqlalchemy.orm import Session

from backend.main import Loja, SessionLocal, hash_token

CHAVE_VALIDA = re.compile(r"[A-Za-z0-9._-]{1,64}")


class ErroLoja(Exception):
    pass


def _gerar_token() -> str:
    return secrets.token_urlsafe(32)


def _obter(db: Session, chave: str) -> Loja:
    loja = db.query(Loja).filter(Loja.chave_loja == chave).first()
    if loja is None:
        raise ErroLoja(f"Loja {chave} não encontrada.")
    return loja


def criar(db: Session, chave: str, nome: str) -> str:
    """Cadastra a loja e devolve o token (a única vez em que ele aparece)."""
    chave, nome = (chave or "").strip(), (nome or "").strip()
    if not CHAVE_VALIDA.fullmatch(chave):
        raise ErroLoja("A chave da loja deve ter de 1 a 64 letras, números, ponto, hífen ou sublinhado.")
    if not nome:
        raise ErroLoja("Informe o nome da loja.")
    if db.query(Loja).filter(Loja.chave_loja == chave).first() is not None:
        raise ErroLoja(f"A loja {chave} já existe. Para um token novo use: novo-token {chave}")
    token = _gerar_token()
    db.add(Loja(chave_loja=chave, nome=nome, token_hash=hash_token(token), ativa=True,
                criada_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    return token


def novo_token(db: Session, chave: str) -> str:
    loja = _obter(db, chave)
    token = _gerar_token()
    loja.token_hash = hash_token(token)
    db.commit()
    return token


def definir_ativa(db: Session, chave: str, ativa: bool) -> None:
    _obter(db, chave).ativa = ativa
    db.commit()


def listar(db: Session) -> list[Loja]:
    return db.query(Loja).order_by(Loja.chave_loja).all()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    comando, resto = (args[0], args[1:]) if args else ("", [])
    db = SessionLocal()
    try:
        if comando == "criar" and len(resto) == 2:
            token = criar(db, resto[0], resto[1])
            print(f"Loja {resto[0].strip()} criada. Token (guarde agora, ele não aparece de novo):\n{token}")
        elif comando == "novo-token" and len(resto) == 1:
            print(f"Token novo da loja {resto[0]} (o antigo deixou de valer):\n{novo_token(db, resto[0])}")
        elif comando in ("ativar", "desativar") and len(resto) == 1:
            definir_ativa(db, resto[0], comando == "ativar")
            print(f"Loja {resto[0]} {'ativada' if comando == 'ativar' else 'desativada'}.")
        elif comando == "listar" and not resto:
            lojas = listar(db)
            for loja in lojas:
                print(f"{loja.chave_loja:<24} {'ativa  ' if loja.ativa else 'INATIVA'}  {loja.nome}")
            if not lojas:
                print("Nenhuma loja cadastrada.")
        else:
            print(__doc__)
            return 2
    except ErroLoja as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
