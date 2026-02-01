import sqlite3
import os

class BancoDados:
    def __init__(self):
        # 1. Define o caminho do banco de dados
        # Isso garante que o arquivo .db seja criado na raiz do projeto, fora da pasta de código
        pasta_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_banco = os.path.join(pasta_atual, '..', '..', 'loja_offline.db')
        
        # 2. Conecta ao banco (cria se não existir)
        self.conexao = sqlite3.connect(caminho_banco)
        self.cursor = self.conexao.cursor()
        self.criar_tabelas()

    def criar_tabelas(self):
        # TABELA PRODUTOS (O Estoque Local)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_barras TEXT UNIQUE,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                estoque_atual INTEGER DEFAULT 0
            )
        ''')

        # TABELA VENDAS (O Financeiro)
        # O campo 'sincronizado' é o segredo do offline: 0 = Pendente, 1 = Enviado pra nuvem
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_venda DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_venda REAL,
                forma_pagamento TEXT,
                sincronizado INTEGER DEFAULT 0 
            )
        ''')

        # TABELA ITENS_VENDA (O que foi vendido em cada compra)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS itens_venda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venda_id INTEGER,
                produto_id INTEGER,
                quantidade INTEGER,
                preco_unitario REAL,
                FOREIGN KEY(venda_id) REFERENCES vendas(id),
                FOREIGN KEY(produto_id) REFERENCES produtos(id)
            )
        ''')

        # TABELA CONFIGURAÇÃO (Sua segurança dos R$ 150/mês)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chave_loja TEXT,
                licenca_ativa INTEGER DEFAULT 1
            )
        ''')
        
        self.conexao.commit()

    def fechar(self):
        self.conexao.close()

# Teste rápido: se rodar esse arquivo, ele cria o banco
if __name__ == "__main__":
    banco = BancoDados()
    print("Banco de dados criado/conectado com sucesso na raiz do projeto!")
    banco.fechar()
  
