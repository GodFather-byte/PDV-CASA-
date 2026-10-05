"""API de nuvem do PDV (FastAPI): aviso de versão nova do PDV (a licença é do servidor /validar, fora deste projeto).

A nuvem NÃO recebe vendas nem tem painel de faturamento: o PDV funciona sozinho em cada boate. Ela só guarda a lista de
lojas (cada uma com o SEU token) e publica as versões novas do PDV. Cadastro das lojas (o token aparece uma única vez):
    python -m backend.lojas criar BOATE-CENTRO "Boate Centro"

Como rodar, na raiz do repositório:
    $env:PDV_API_TOKEN = "um-segredo-longo-e-aleatorio"      # token do ADMINISTRADOR (lista de lojas)
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

O PDV usa o token da loja em Configurações > Nuvem (Token da API) e envia `Authorization: Bearer <token>`. Sem nenhuma
loja e sem PDV_API_TOKEN o servidor recusa tudo (503): não existe token padrão.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import Session

from backend.database import Base, SessionLocal, engine
from src.versao import chave, mais_nova, valida      # a mesma regra de comparação de versões do PDV

log = logging.getLogger("pdv.nuvem")

class Loja(Base):
    """Uma loja cliente da nuvem. Guarda só o SHA-256 do token (aleatório e longo), nunca o token."""
    __tablename__ = "lojas"
    id = Column(Integer, primary_key=True, index=True)
    chave_loja = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    ativa = Column(Boolean, nullable=False, default=True)
    criada_em = Column(String)


class Versao(Base):
    """Versão do PDV publicada pelo fornecedor (python -m backend.atualizacoes). Os caixas consultam /v1/atualizacoes."""
    __tablename__ = "versoes"
    id = Column(Integer, primary_key=True, index=True)
    versao = Column(String, unique=True, index=True, nullable=False)
    notas = Column(String, nullable=False)
    url_download = Column(String, nullable=True)
    critica = Column(Boolean, nullable=False, default=False)
    publicada_em = Column(String)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


Base.metadata.create_all(bind=engine)

app = FastAPI(title="WillPDV - API de nuvem")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass(frozen=True)
class Acesso:
    """Quem chamou: uma loja (pelo token dela) ou o administrador (PDV_API_TOKEN), que tem `loja` None."""
    loja: Optional[str]

    @property
    def admin(self) -> bool:
        return self.loja is None


def autenticar(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Acesso:
    admin = os.environ.get("PDV_API_TOKEN", "")
    token = authorization[7:].strip() if authorization and authorization.startswith("Bearer ") else ""
    if token:
        if admin and hmac.compare_digest(token.encode("utf-8"), admin.encode("utf-8")):
            return Acesso(None)
        loja = db.query(Loja).filter(Loja.token_hash == hash_token(token)).first()
        if loja is not None:
            if not loja.ativa:
                raise HTTPException(status_code=403, detail="Loja desativada na nuvem.")
            return Acesso(loja.chave_loja)
    if not admin and db.query(Loja.id).first() is None:
        raise HTTPException(status_code=503, detail="Servidor sem lojas cadastradas nem PDV_API_TOKEN configurado.")
    raise HTTPException(status_code=401, detail="Token invalido")


@app.get("/v1/saude")
def saude():
    return {"status": "ok"}


@app.get("/v1/admin/lojas")
def admin_lojas(acesso: Acesso = Depends(autenticar), db: Session = Depends(get_db)):
    """Lista do fornecedor (só com o PDV_API_TOKEN): cada loja e se está ativa. É o 'lojas listar' na tela, para quem
    não tem terminal no servidor (ex.: Render grátis)."""
    if not acesso.admin:
        raise HTTPException(status_code=403, detail="Só o token do administrador vê a lista de lojas.")
    return {"lojas": [
        {"chave_loja": l.chave_loja, "nome": l.nome, "ativa": bool(l.ativa)}
        for l in db.query(Loja).order_by(Loja.chave_loja).all()]}


# ------------------------------------------------------------ atualizações
@app.get("/v1/atualizacoes")
def atualizacoes(versao: str = Query(..., max_length=20), acesso: Acesso = Depends(autenticar),
                 db: Session = Depends(get_db)):
    """O que há de novo para um PDV na `versao` informada: as versões mais novas publicadas, da mais nova para a
    mais antiga, com as notas. `critica` diz se alguma delas é correção que não deve esperar."""
    if not valida(versao):
        raise HTTPException(status_code=422, detail="versão inválida")
    novas = sorted((v for v in db.query(Versao).all() if mais_nova(v.versao, versao)),
                   key=lambda v: chave(v.versao), reverse=True)
    return {
        "versao_atual": versao,
        "disponivel": bool(novas),
        "ultima": novas[0].versao if novas else None,
        "critica": any(v.critica for v in novas),
        "url_download": next((v.url_download for v in novas if v.url_download), None),
        "versoes": [{"versao": v.versao, "notas": v.notas, "critica": bool(v.critica), "publicada_em": v.publicada_em}
                    for v in novas[:20]],
    }
