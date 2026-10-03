import sqlite3
from uuid import uuid4

from src.controllers.produto_controller import ProdutoController
from src.core.formatacao import agora, mult_cent, para_centavos, para_qtd
from src.database.conexao import BancoDados


class VendaController:
    def __init__(self, banco: BancoDados | None = None):
        self.banco = banco or BancoDados()

    def iniciar_venda(self):
        try:
            with self.banco.transacao():
                cursor = self.banco.executar(
                    """INSERT INTO vendas (uuid, aberta_em, ultimo_lancamento_em)
                       VALUES (?, ?, ?)""",
                    (str(uuid4()), agora(), agora()),
                )
                return cursor.lastrowid
        except sqlite3.Error as erro:
            print(f"Erro ao abrir venda: {erro}")
            return None

    def adicionar_item(self, venda_id, produto_id, quantidade, preco_unitario):
        try:
            qtd = para_qtd(quantidade)
            preco_cent = para_centavos(preco_unitario)
            if qtd <= 0 or preco_cent < 0:
                return False

            with self.banco.transacao():
                venda = self.banco.um(
                    "SELECT status FROM vendas WHERE id = ?", (venda_id,)
                )
                produto = self.banco.um(
                    "SELECT * FROM produtos WHERE id = ? AND ativo = 1 AND venda = 1",
                    (produto_id,),
                )
                if not venda or venda[0] != "aberta" or not produto:
                    return False

                dados_produto = dict(produto)
                preco_cent = ProdutoController(self.banco).preco_vigente(dados_produto)
                controla_estoque = dados_produto["controla_estoque"]
                if controla_estoque and dados_produto["qt_atual"] < qtd:
                    return False

                total_cent = mult_cent(preco_cent, qtd)
                criado_em = agora()
                self.banco.executar(
                    """INSERT INTO itens_venda
                       (venda_id, produto_id, quantidade, preco_unit_cent, total_cent,
                        cobra_servico, criado_em)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        venda_id, produto_id, qtd, preco_cent, total_cent,
                        dados_produto["cobrar_servico"], criado_em,
                    ),
                )
                self.banco.executar(
                    """UPDATE vendas
                       SET subtotal_cent = subtotal_cent + ?, total_cent = total_cent + ?,
                           ultimo_lancamento_em = ?
                       WHERE id = ? AND status = 'aberta'""",
                    (total_cent, total_cent, criado_em, venda_id),
                )
                if controla_estoque:
                    estoque_apos = dados_produto["qt_atual"] - qtd
                    self.banco.executar(
                        "UPDATE produtos SET qt_atual = ? WHERE id = ?",
                        (estoque_apos, produto_id),
                    )
                    self.banco.executar(
                        """INSERT INTO movimentos_estoque
                           (produto_id, tipo, quantidade, qt_apos, ref_tipo, ref_id, criado_em)
                           VALUES (?, 'venda', ?, ?, 'venda', ?, ?)""",
                        (produto_id, -qtd, estoque_apos, venda_id, criado_em),
                    )
            return True
        except (ValueError, sqlite3.Error) as erro:
            print(f"Erro ao adicionar item: {erro}")
            return False

    def finalizar_venda(self, venda_id, total_final, forma_pagamento):
        pagamento = (forma_pagamento or "").strip()
        try:
            total_solicitado = para_centavos(total_final)
            if not pagamento:
                return False
            with self.banco.transacao():
                venda = self.banco.um(
                    "SELECT total_cent, status FROM vendas WHERE id = ?", (venda_id,)
                )
                if not venda or venda[1] != "aberta" or venda[0] <= 0:
                    return False
                if total_solicitado != venda[0]:
                    return False

                self.banco.executar(
                    "INSERT OR IGNORE INTO tipos_pagamento (tipo) VALUES (?)",
                    (pagamento,),
                )
                tipo_id = self.banco.valor(
                    "SELECT id FROM tipos_pagamento WHERE tipo = ?", (pagamento,)
                )
                fechado_em = agora()
                self.banco.executar(
                    """INSERT INTO pagamentos_venda
                       (venda_id, tipo_pagamento_id, valor_cent, criado_em)
                       VALUES (?, ?, ?, ?)""",
                    (venda_id, tipo_id, venda[0], fechado_em),
                )
                self.banco.executar(
                    """UPDATE vendas SET status = 'fechada', fechada_em = ?,
                       pago_cent = ?, sincronizado = 0 WHERE id = ?""",
                    (fechado_em, venda[0], venda_id),
                )
            return True
        except (ValueError, sqlite3.Error) as erro:
            print(f"Erro ao fechar venda: {erro}")
            return False

    def listar_vendas_pendentes(self):
        return self.banco.todos(
            """SELECT id, uuid, total_cent, status FROM vendas
               WHERE sincronizado = 0 AND status = 'fechada'
               ORDER BY id"""
        )
