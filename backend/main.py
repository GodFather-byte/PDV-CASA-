"""API de nuvem do PDV (FastAPI): recebe lotes de vendas do PDV, de forma idempotente por UUID.

Como rodar, na raiz do repositório:
    $env:PDV_API_TOKEN = "um-segredo-longo-e-aleatorio"
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

O PDV usa o mesmo valor em Configurações > Nuvem (Token da API) e envia `Authorization: Bearer <token>`.
Sem PDV_API_TOKEN o servidor recusa os lotes (503): não existe token padrão.
Contrato completo em docs/COORDENACAO.md.
"""
from __future__ import annotations

import hmac
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Float, Integer, String, func
from sqlalchemy.orm import Session

from backend.database import Base, SessionLocal, engine

log = logging.getLogger("pdv.nuvem")

PAGINA_PAINEL = Path(__file__).resolve().parent / "templates" / "dashboard.html"
DATA_HORA = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
# Uma venda só avança no tempo: fechada -> cancelada. Reenvio com estado igual ou anterior não muda nada.
ORDEM_STATUS = {"fechada": 1, "cancelada": 2}


class Venda(Base):
    __tablename__ = "vendas"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True)
    chave_loja = Column(String, index=True)
    cupom = Column(Integer)
    turno = Column(Integer, nullable=True)
    terminal = Column(Integer)
    modalidade = Column(String)
    posicao = Column(Integer, nullable=True)
    status = Column(String)
    aberta_em = Column(String)
    fechada_em = Column(String)
    operador = Column(String, nullable=True)
    subtotal_cent = Column(Integer)
    desconto_cent = Column(Integer)
    servico_cent = Column(Integer)
    taxa_cent = Column(Integer)
    total_cent = Column(Integer)
    troco_cent = Column(Integer)
    vale_cent = Column(Integer)
    pessoas = Column(Integer)
    recebida_em = Column(String)
    atualizada_em = Column(String)


class VendaItem(Base):
    __tablename__ = "vendas_itens"
    id = Column(Integer, primary_key=True, index=True)
    venda_uuid = Column(String, index=True)  # Ligação com UUID
    codigo = Column(String)
    nome = Column(String)
    quantidade = Column(Float)
    preco_unit_cent = Column(Integer)
    total_cent = Column(Integer)
    cancelado = Column(Boolean)


class VendaPagamento(Base):
    __tablename__ = "vendas_pagamentos"
    id = Column(Integer, primary_key=True, index=True)
    venda_uuid = Column(String, index=True)
    tipo = Column(String)
    valor_cent = Column(Integer)
    troco_cent = Column(Integer)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="WillPDV - API de nuvem")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def exigir_token(authorization: Optional[str] = Header(None)) -> None:
    esperado = os.environ.get("PDV_API_TOKEN", "")
    if not esperado:
        raise HTTPException(status_code=503, detail="Servidor sem PDV_API_TOKEN configurado.")
    if not authorization or not hmac.compare_digest(authorization.encode(), f"Bearer {esperado}".encode()):
        raise HTTPException(status_code=401, detail="Token invalido")


# ---------------------------------------------------------------- esquemas
class ItemSync(BaseModel):
    codigo: str
    nome: str
    quantidade: float = Field(gt=0)
    preco_unit_cent: int = Field(ge=0)
    total_cent: int = Field(ge=0)
    cancelado: bool


class PagamentoSync(BaseModel):
    tipo: str
    valor_cent: int = Field(gt=0)
    troco_cent: int = Field(ge=0)


class VendaSync(BaseModel):
    uuid: str = Field(min_length=1, max_length=64)
    cupom: int = Field(ge=1)
    turno: Optional[int] = None
    terminal: int = Field(ge=1)
    modalidade: Literal["balcao", "mesa", "caderneta", "entrega"]
    posicao: Optional[int] = None
    status: Literal["fechada", "cancelada"]
    aberta_em: str = Field(pattern=DATA_HORA)
    fechada_em: str = Field(pattern=DATA_HORA)
    operador: Optional[str] = None
    subtotal_cent: int = Field(ge=0)
    desconto_cent: int = Field(ge=0)
    servico_cent: int = Field(ge=0)
    taxa_cent: int = Field(ge=0)
    total_cent: int = Field(ge=0)
    troco_cent: int = Field(ge=0)
    vale_cent: int = Field(ge=0)
    pessoas: int = Field(ge=0)
    itens: List[ItemSync]
    pagamentos: List[PagamentoSync]


class LoteSync(BaseModel):
    chave_loja: str = Field(min_length=1, max_length=64)
    terminal: int = Field(ge=1)
    enviado_em: str
    vendas: List[VendaSync] = Field(max_length=500)


class ResponseSync(BaseModel):
    aceitas: List[str]


# ------------------------------------------------------------------- rotas
@app.get("/v1/saude")
def saude():
    return {"status": "ok"}


@app.post("/v1/sincronizar", response_model=ResponseSync, dependencies=[Depends(exigir_token)])
def sincronizar_vendas(lote: LoteSync, db: Session = Depends(get_db)):
    """Grava cada venda do lote por UUID. `aceitas` traz só os UUIDs que a nuvem já tem (novos ou repetidos)."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uuids = [v.uuid for v in lote.vendas]
    existentes = {v.uuid: v for v in db.query(Venda).filter(Venda.uuid.in_(uuids)).all()} if uuids else {}
    aceitas: list[str] = []

    for req in lote.vendas:
        try:
            atual = existentes.get(req.uuid)
            if atual is not None:
                if atual.chave_loja and atual.chave_loja != lote.chave_loja:
                    log.warning("UUID %s já pertence a outra loja; não confirmado.", req.uuid)
                    continue
                if ORDEM_STATUS[req.status] > ORDEM_STATUS.get(atual.status, 0):  # cancelamento depois do envio
                    atual.status = req.status
                    atual.atualizada_em = agora
                    db.commit()
                aceitas.append(req.uuid)
                continue

            nova = Venda(
                uuid=req.uuid, chave_loja=lote.chave_loja, cupom=req.cupom, turno=req.turno, terminal=req.terminal,
                modalidade=req.modalidade, posicao=req.posicao, status=req.status, aberta_em=req.aberta_em,
                fechada_em=req.fechada_em, operador=req.operador, subtotal_cent=req.subtotal_cent,
                desconto_cent=req.desconto_cent, servico_cent=req.servico_cent, taxa_cent=req.taxa_cent,
                total_cent=req.total_cent, troco_cent=req.troco_cent, vale_cent=req.vale_cent, pessoas=req.pessoas,
                recebida_em=agora, atualizada_em=agora)
            db.add(nova)
            db.add_all(VendaItem(venda_uuid=req.uuid, **i.model_dump()) for i in req.itens)
            db.add_all(VendaPagamento(venda_uuid=req.uuid, **p.model_dump()) for p in req.pagamentos)
            db.commit()
            existentes[req.uuid] = nova
            aceitas.append(req.uuid)
        except Exception:
            db.rollback()
            log.exception("Erro processando a venda %s; o PDV vai reenviar.", req.uuid)  # sem aceite = o PDV tenta de novo

    return {"aceitas": aceitas}

# ------------------------------------------------------------ painel do dono
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def painel():
    """Página do painel. Ela não traz dados: pede o token e consulta /v1/dashboard/resumo."""
    return HTMLResponse(PAGINA_PAINEL.read_text(encoding="utf-8"))


@app.get("/v1/dashboard/resumo", dependencies=[Depends(exigir_token)])
def dashboard_resumo(dia: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                     chave_loja: Optional[str] = Query(None, max_length=64),
                     db: Session = Depends(get_db)):
    """Faturamento, cupons, ticket médio e mais vendidos de um dia. Sem `dia`, vale o da venda mais recente
    (assim o painel não depende do fuso do servidor). Só vendas fechadas com itens; recebimentos de
    caderneta (subtotal 0) e cancelamentos ficam de fora, como no painel do PDV."""
    base = [Venda.status == "fechada", Venda.subtotal_cent > 0]        # filtros que valem também para achar o dia padrão
    if chave_loja:
        base.append(Venda.chave_loja == chave_loja)
    if dia is None:
        ultima = db.query(func.max(Venda.fechada_em)).filter(*base).scalar()
        dia = ultima[:10] if ultima else date.today().isoformat()
    try:
        inicio = date.fromisoformat(dia)
    except ValueError:
        raise HTTPException(status_code=422, detail="dia inválido")
    filtro = [*base,
              Venda.fechada_em >= f"{inicio.isoformat()} 00:00:00",
              Venda.fechada_em < f"{(inicio + timedelta(days=1)).isoformat()} 00:00:00"]
    receita, cupons = db.query(func.coalesce(func.sum(Venda.total_cent), 0), func.count(Venda.id)).filter(*filtro).one()
    mais_vendidos = (db.query(VendaItem.nome, func.sum(VendaItem.quantidade), func.sum(VendaItem.total_cent))
                     .join(Venda, Venda.uuid == VendaItem.venda_uuid)
                     .filter(*filtro, VendaItem.cancelado.is_(False))
                     .group_by(VendaItem.nome).order_by(func.sum(VendaItem.quantidade).desc()).limit(5).all())
    return {
        "dia": dia, "receita_cent": int(receita), "cupons": cupons,
        "ticket_medio_cent": (int(receita) + cupons // 2) // cupons if cupons else 0,   # centavos inteiros
        "top_produtos": [{"nome": n, "qtd": float(q), "total_cent": int(t)} for n, q, t in mais_vendidos],
    }
