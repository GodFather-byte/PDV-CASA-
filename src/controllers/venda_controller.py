from src.database.conexao import BancoDados
from datetime import datetime

class VendaController:
    def __init__(self):
        self.banco = BancoDados()

    def iniciar_venda(self):
        """
        Cria uma 'cesta' vazia no banco de dados para começar a passar os produtos.
        Retorna o ID dessa nova venda.
        """
        try:
            # Cria o registro inicial (ainda sem valor, pois está em aberto)
            sql = "INSERT INTO vendas (data_venda, total_venda, sincronizado) VALUES (?, 0, 0)"
            data_agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor = self.banco.conexao.cursor()
            cursor.execute(sql, (data_agora,))
            self.banco.conexao.commit()
            
            venda_id = cursor.lastrowid
            return venda_id
        except Exception as e:
            print(f"Erro ao abrir venda: {e}")
            return None

    def adicionar_item(self, venda_id, produto_id, quantidade, preco_unitario):
        """
        Adiciona a cerveja ou o combo na lista de itens dessa venda.
        """
        try:
            sql = '''
                INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario)
                VALUES (?, ?, ?, ?)
            '''
            self.banco.conexao.cursor().execute(sql, (venda_id, produto_id, quantidade, preco_unitario))
            self.banco.conexao.commit()
            return True
        except Exception as e:
            print(f"Erro ao adicionar item: {e}")
            return False

    def finalizar_venda(self, venda_id, total_final, forma_pagamento):
        """
        O Momento da Verdade:
        1. Atualiza o total.
        2. Define como pagou (Pix/Dinheiro).
        3. Garante que 'sincronizado' seja 0 (para o robô pegar depois).
        """
        try:
            sql = '''
                UPDATE vendas 
                SET total_venda = ?, forma_pagamento = ?, sincronizado = 0
                WHERE id = ?
            '''
            self.banco.conexao.cursor().execute(sql, (total_final, forma_pagamento, venda_id))
            self.banco.conexao.commit()
            
            # AQUI SERIA O LUGAR PARA BAIXAR O ESTOQUE (Chamando o ProdutoController)
            print(f"Venda {venda_id} finalizada com sucesso! Pronta para sincronizar.")
            return True
        except Exception as e:
            print(f"Erro ao fechar venda: {e}")
            return False

    def listar_vendas_pendentes(self):
        """
        Essa função será usada pelo ROBÔ DE SINCRONIZAÇÃO.
        Ela busca tudo que ainda não subiu para a nuvem.
        """
        sql = "SELECT * FROM vendas WHERE sincronizado = 0"
        cursor = self.banco.conexao.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
      
