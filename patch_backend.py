import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports for templates and static files
imports = """from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from sqlalchemy import func

templates = Jinja2Templates(directory="backend/templates")
"""

if 'Jinja2Templates' not in content:
    content = content.replace('from sqlalchemy.orm import Session', 'from sqlalchemy.orm import Session\n' + imports)

# Add dashboard endpoints
endpoints = """
# ------------------------------------------------------------------- dashboard
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/v1/dashboard/resumo")
def dashboard_resumo(db: Session = Depends(get_db)):
    total_receita = db.query(func.sum(Venda.total_cent)).filter(Venda.status == "fechada").scalar() or 0
    total_cupons = db.query(Venda).filter(Venda.status == "fechada").count()
    ticket_medio = (total_receita / total_cupons) if total_cupons > 0 else 0
    
    # Produtos mais vendidos
    top_produtos = db.query(
        VendaItem.nome, 
        func.sum(VendaItem.quantidade).label('qtd'),
        func.sum(VendaItem.total_cent).label('total')
    ).join(Venda, Venda.uuid == VendaItem.venda_uuid)\\
     .filter(Venda.status == "fechada", VendaItem.cancelado == False)\\
     .group_by(VendaItem.nome)\\
     .order_by(func.sum(VendaItem.quantidade).desc())\\
     .limit(5).all()

    return {
        "receita_cent": total_receita,
        "cupons": total_cupons,
        "ticket_medio_cent": ticket_medio,
        "top_produtos": [{"nome": p.nome, "qtd": p.qtd, "total_cent": p.total} for p in top_produtos]
    }
"""

if '@app.get("/")' not in content:
    content = content + endpoints

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Backend atualizado com rotas do dashboard.')
