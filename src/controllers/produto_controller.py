from src.database.conexao import BancoDados

class ProdutoController:
    def __init__(self):
        # Toda vez que chamamos o controlador, ele prepara o banco
        self.banco = BancoDados()

    def cadastrar_produto(self, nome, preco, codigo_barras, estoque_inicial=0):
        """
        Cadastra um novo produto no banco local.
        Retorna True se der certo, ou o erro se falhar (ex: código repetido).
        """
        try:
            sql = '''
                INSERT INTO produtos (nome, preco, codigo_barras, estoque_atual)
                VALUES (?, ?, ?, ?)
            '''
            self.banco.cursor.execute(sql, (nome, preco, codigo_barras, estoque_inicial))
            self.banco.conexao.commit()
            return True, "Produto cadastrado com sucesso!"
        except Exception as e:
            return False, f"Erro ao cadastrar: {str(e)}"

    def buscar_por_codigo(self, codigo):
        """
        Usado na TELA DE VENDA. Quando o leitor bipa, essa função roda.
        """
        sql = 'SELECT * FROM produtos WHERE codigo_barras = ?'
        self.banco.cursor.execute(sql, (codigo,))
        return self.banco.cursor.fetchone()

    def listar_todos(self):
        """
        Para ver o relatório de estoque ou preencher a tabela de cadastro.
        """
        sql = 'SELECT * FROM produtos'
        self.banco.cursor.execute(sql)
        return self.banco.cursor.fetchall()

    def atualizar_estoque(self, produto_id, quantidade_vendida):
        """
        Baixa o estoque após a venda.
        """
        try:
            sql = 'UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE id = ?'
            self.banco.cursor.execute(sql, (quantidade_vendida, produto_id))
            self.banco.conexao.commit()
            return True
        except Exception as e:
            return False

# DICA: Não esqueça de fechar a conexão no final do uso se for instanciar direto!
