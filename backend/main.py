"""API de nuvem do PDV (FastAPI): recebe lotes de vendas do PDV, de forma idempotente por UUID.

Cada loja tem o SEU token. A loja é identificada pelo token, nunca pelo que o lote diz: o token da loja A não
envia vendas em nome da loja B nem vê o painel dela. Cadastro das lojas (o token aparece uma única vez):
    python -m backend.lojas criar BOATE-CENTRO "Boate Centro"

Como rodar, na raiz do repositório:
    $env:PDV_API_TOKEN = "um-segredo-longo-e-aleatorio"      # token do ADMINISTRADOR (painel de todas as lojas)
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

O PDV usa o token da loja em Configurações > Nuvem (Token da API) e envia `Authorization: Bearer <token>`.
O token do administrador só consulta o painel: não envia vendas. Sem nenhuma loja e sem PDV_API_TOKEN o servidor
recusa tudo (503): não existe token padrão. Contrato completo em docs/COORDENACAO.md.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Float, Integer, String, func
from sqlalchemy.orm import Session

from backend.database import Base, SessionLocal, engine
from src.versao import chave, mais_nova, valida      # a mesma regra de comparação de versões do PDV

log = logging.getLogger("pdv.nuvem")

PAGINA_PAINEL = Path(__file__).resolve().parent / "templates" / "dashboard.html"
DATA_HORA = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
# Uma venda só avança no tempo: fechada -> cancelada. Reenvio com estado igual ou anterior não muda nada.
ORDEM_STATUS = {"fechada": 1, "cancelada": 2}


def virada_padrao() -> int:
    """Hora em que o "dia" do painel vira (PDV_NUVEM_VIRADA_HORA, padrão 6): a noite da boate não se divide à meia-noite."""
    try:
        hora = int(os.environ.get("PDV_NUVEM_VIRADA_HORA", "6"))
    except ValueError:
        return 6
    return hora if 0 <= hora <= 23 else 6


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


@app.post("/v1/sincronizar", response_model=ResponseSync)
def sincronizar_vendas(lote: LoteSync, acesso: Acesso = Depends(autenticar), db: Session = Depends(get_db)):
    """Grava cada venda do lote por UUID. `aceitas` traz só os UUIDs que a nuvem já tem (novos ou repetidos)."""
    if acesso.admin:
        raise HTTPException(status_code=403, detail="O token do administrador não envia vendas: use o token da loja.")
    if lote.chave_loja != acesso.loja:
        log.warning("Token da loja %s tentou enviar vendas como %s.", acesso.loja, lote.chave_loja)
        raise HTTPException(status_code=403, detail=f"Este token é da loja {acesso.loja}, não de {lote.chave_loja}.")
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


@app.get("/v1/dashboard/resumo")
def dashboard_resumo(dia: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                     chave_loja: Optional[str] = Query(None, max_length=64),
                     virada: Optional[int] = Query(None, ge=0, le=23),
                     acesso: Acesso = Depends(autenticar), db: Session = Depends(get_db)):
    """Faturamento, cupons, ticket médio e mais vendidos de um dia. Sem `dia`, vale o da venda mais recente
    (assim o painel não depende do fuso do servidor). Só vendas fechadas com itens; recebimentos de
    caderneta (subtotal 0) e cancelamentos ficam de fora, como no painel do PDV.
    O token de uma loja só vê a própria loja; o do administrador vê todas ou a pedida em `chave_loja`.
    O dia vai da hora de `virada` (padrão PDV_NUVEM_VIRADA_HORA, 6) até a mesma hora do dia seguinte: a venda das
    2h de sábado conta na noite de sexta."""
    if not acesso.admin:
        if chave_loja and chave_loja != acesso.loja:
            raise HTTPException(status_code=403, detail="Este token só consulta a própria loja.")
        chave_loja = acesso.loja
    base = [Venda.status == "fechada", Venda.subtotal_cent > 0]        # filtros que valem também para achar o dia padrão
    if chave_loja:
        base.append(Venda.chave_loja == chave_loja)
    virada = virada_padrao() if virada is None else virada
    if dia is None:
        ultima = db.query(func.max(Venda.fechada_em)).filter(*base).scalar()
        dia = ((datetime.strptime(ultima[:19], "%Y-%m-%d %H:%M:%S") - timedelta(hours=virada)).date().isoformat()
               if ultima else date.today().isoformat())
    try:
        inicio = date.fromisoformat(dia)
    except ValueError:
        raise HTTPException(status_code=422, detail="dia inválido")
    filtro = [*base,
              Venda.fechada_em >= f"{inicio.isoformat()} {virada:02d}:00:00",
              Venda.fechada_em < f"{(inicio + timedelta(days=1)).isoformat()} {virada:02d}:00:00"]
    receita, cupons = db.query(func.coalesce(func.sum(Venda.total_cent), 0), func.count(Venda.id)).filter(*filtro).one()
    mais_vendidos = (db.query(VendaItem.nome, func.sum(VendaItem.quantidade), func.sum(VendaItem.total_cent))
                     .join(Venda, Venda.uuid == VendaItem.venda_uuid)
                     .filter(*filtro, VendaItem.cancelado.is_(False))
                     .group_by(VendaItem.nome).order_by(func.sum(VendaItem.quantidade).desc()).limit(5).all())
    return {
        "dia": dia, "virada": virada, "receita_cent": int(receita), "cupons": cupons,
        "ticket_medio_cent": (int(receita) + cupons // 2) // cupons if cupons else 0,   # centavos inteiros
        "top_produtos": [{"nome": n, "qtd": float(q), "total_cent": int(t)} for n, q, t in mais_vendidos],
    }


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

