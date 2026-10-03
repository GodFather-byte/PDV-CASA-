from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class Unidade(Base):
    __tablename__ = "unidades"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True) # Ex: Quilos, Litros, Unidade
    abreviatura = Column(String, index=True)
    produtos = relationship("Produto", back_populates="unidade")

class Grupo(Base):
    __tablename__ = "grupos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    subgrupos = relationship("Subgrupo", back_populates="grupo")

class Subgrupo(Base):
    __tablename__ = "subgrupos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"))
    imprime_em_outra_impressora = Column(Boolean, default=False)

    grupo = relationship("Grupo", back_populates="subgrupos")
    produtos = relationship("Produto", back_populates="subgrupo")

class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, unique=True)
    codigo = Column(String(13), unique=True, index=True) # Numérico max 13 casas
    codigo_barras = Column(String(13), unique=True, index=True, nullable=True) # EAN 13

    cobrar_servico = Column(Boolean, default=False)
    venda = Column(Boolean, default=True)
    aceita_decimal = Column(Boolean, default=False)
    preco_venda = Column(Float, default=0.0)
    aliquota = Column(String, default="II") # Ex: II (Isento), FF (Subst. Tributaria), 1800 (18%)

    # Estoque
    estoque_ativo = Column(Boolean, default=False)
    estoque_minimo = Column(Float, default=0.0)
    quantidade_atual = Column(Float, default=0.0)
    quantidade_inicial = Column(Float, default=0.0)
    ultimo_preco = Column(Float, default=0.0)
    ultima_atualizacao = Column(DateTime, default=datetime.datetime.utcnow)

    # Opções Pizzaria / Composições
    dividir_em = Column(Integer, default=1) # 1 a 55
    cobrar_pelo_maior = Column(Boolean, default=False)
    permite_montagem = Column(Boolean, default=False) # Para uso na montagem de outros

    unidade_id = Column(Integer, ForeignKey("unidades.id"))
    subgrupo_id = Column(Integer, ForeignKey("subgrupos.id"), nullable=True)

    unidade = relationship("Unidade", back_populates="produtos")
    subgrupo = relationship("Subgrupo", back_populates="produtos")

    composicoes_como_pai = relationship("Composicao", foreign_keys="[Composicao.produto_pai_id]", back_populates="produto_pai")
    composicoes_como_filho = relationship("Composicao", foreign_keys="[Composicao.produto_filho_id]", back_populates="produto_filho")

class Composicao(Base):
    __tablename__ = "composicoes"
    id = Column(Integer, primary_key=True, index=True)
    produto_pai_id = Column(Integer, ForeignKey("produtos.id"))
    produto_filho_id = Column(Integer, ForeignKey("produtos.id"))
    quantidade = Column(Float)

    produto_pai = relationship("Produto", foreign_keys=[produto_pai_id], back_populates="composicoes_como_pai")
    produto_filho = relationship("Produto", foreign_keys=[produto_filho_id], back_populates="composicoes_como_filho")

class Cargo(Base):
    __tablename__ = "cargos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    operadores = relationship("Operador", back_populates="cargo")

class Operador(Base):
    __tablename__ = "operadores"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    senha = Column(String(10)) # Máx 10 dígitos alfanuméricos
    nivel_acesso = Column(Integer, default=0) # 0 a 4
    cargo_id = Column(Integer, ForeignKey("cargos.id"))

    cargo = relationship("Cargo", back_populates="operadores")

class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    contato = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    celular = Column(String, nullable=True)
    ddd = Column(String, nullable=True)
    cgc = Column(String, nullable=True) # CNPJ
    endereco = Column(String, nullable=True)
    complemento = Column(String, nullable=True)
    bairro = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    estado = Column(String, nullable=True)
    email = Column(String, nullable=True)

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    numero_consulta = Column(String, index=True)
    endereco = Column(String, nullable=True)
    complemento = Column(String, nullable=True)
    cep = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    rg = Column(String, nullable=True)
    cpf = Column(String, nullable=True)
    email = Column(String, nullable=True)
    observacoes = Column(String, nullable=True)
    saldo = Column(Float, default=0.0) # Para controle de Caderneta

class TipoPagamento(Base):
    __tablename__ = "tipos_pagamento"
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String)
    saldo_inicial = Column(Float, default=0.0)
    ordem = Column(Integer)
    habilitado_caixa = Column(Boolean, default=True)
    emite_vale = Column(Boolean, default=False)
    tipo_tef = Column(String, nullable=True)

class PlanoContas(Base):
    __tablename__ = "planos_conta"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    codigo = Column(String, unique=True)
    debito = Column(Boolean, default=True) # True para saída, False para entrada
    afeta_resultado = Column(Boolean, default=True)

    subplanos = relationship("SubPlano", back_populates="plano")

class SubPlano(Base):
    __tablename__ = "subplanos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    plano_id = Column(Integer, ForeignKey("planos_conta.id"))

    plano = relationship("PlanoContas", back_populates="subplanos")
