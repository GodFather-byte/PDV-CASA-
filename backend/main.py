from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime
from backend.database import SessionLocal, engine, Base

# Extending Base to add Venda, ItemVenda, Pagamento for Nuvem
class Venda(Base):
    __tablename__ = "vendas"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True)
    cupom = Column(Integer)
    turno = Column(Integer)
    terminal = Column(Integer)
    modalidade = Column(String)
    posicao = Column(String, nullable=True)
    status = Column(String)
    aberta_em = Column(String)
    fechada_em = Column(String)
    operador = Column(String)
    subtotal_cent = Column(Integer)
    desconto_cent = Column(Integer)
    servico_cent = Column(Integer)
    taxa_cent = Column(Integer)
    total_cent = Column(Integer)
    troco_cent = Column(Integer)
    vale_cent = Column(Integer)
    pessoas = Column(Integer)

class VendaItem(Base):
    __tablename__ = "vendas_itens"
    id = Column(Integer, primary_key=True, index=True)
    venda_uuid = Column(String, index=True) # Ligação com UUID
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

app = FastAPI(title="Evicommerce API - Sync")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas
class ItemSync(BaseModel):
    codigo: str
    nome: str
    quantidade: float
    preco_unit_cent: int
    total_cent: int
    cancelado: bool

class PagamentoSync(BaseModel):
    tipo: str
    valor_cent: int
    troco_cent: int

class VendaSync(BaseModel):
    uuid: str
    cupom: int
    turno: Optional[int]
    terminal: int
    modalidade: str
    posicao: Optional[str] = None
    status: str
    aberta_em: str
    fechada_em: str
    operador: str
    subtotal_cent: int
    desconto_cent: int
    servico_cent: int
    taxa_cent: int
    total_cent: int
    troco_cent: int
    vale_cent: int
    pessoas: int
    itens: List[ItemSync]
    pagamentos: List[PagamentoSync]

class LoteSync(BaseModel):
    chave_loja: str
    terminal: int
    enviado_em: str
    vendas: List[VendaSync]

class ResponseSync(BaseModel):
    aceitas: List[str]

@app.post("/v1/sincronizar", response_model=ResponseSync)
def sincronizar_vendas(
    lote: LoteSync, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    if authorization != "Bearer MeuTokenSuperSeguro":
        raise HTTPException(status_code=401, detail="Token invalido")
        
    if lote.chave_loja == "":
        raise HTTPException(status_code=400, detail="Chave da loja ausente")

    aceitas = []
    
    for venda_req in lote.vendas:
        # Check idempotency
        venda_existente = db.query(Venda).filter(Venda.uuid == venda_req.uuid).first()
        if venda_existente:
            aceitas.append(venda_req.uuid)
            continue
            
        try:
            nova_venda = Venda(
                uuid=venda_req.uuid,
                cupom=venda_req.cupom,
                turno=venda_req.turno,
                terminal=venda_req.terminal,
                modalidade=venda_req.modalidade,
                posicao=venda_req.posicao,
                status=venda_req.status,
                aberta_em=venda_req.aberta_em,
                fechada_em=venda_req.fechada_em,
                operador=venda_req.operador,
                subtotal_cent=venda_req.subtotal_cent,
                desconto_cent=venda_req.desconto_cent,
                servico_cent=venda_req.servico_cent,
                taxa_cent=venda_req.taxa_cent,
                total_cent=venda_req.total_cent,
                troco_cent=venda_req.troco_cent,
                vale_cent=venda_req.vale_cent,
                pessoas=venda_req.pessoas
            )
            db.add(nova_venda)
            
            for item_req in venda_req.itens:
                db.add(VendaItem(venda_uuid=venda_req.uuid, **item_req.model_dump()))
                
            for pag_req in venda_req.pagamentos:
                db.add(VendaPagamento(venda_uuid=venda_req.uuid, **pag_req.model_dump()))
                
            db.commit()
            aceitas.append(venda_req.uuid)
        except Exception as e:
            db.rollback()
            print(f"Erro processando venda {venda_req.uuid}: {e}")
            # we skip appending to 'aceitas', so client will retry it

    return {"aceitas": aceitas}
