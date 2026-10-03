import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.controllers.produto_controller import ProdutoController
from src.controllers.venda_controller import VendaController
from src.database.conexao import BancoDados
from src.database.esquema import VERSAO_ESQUEMA
from tests.base import BaseTeste


class BancoSQLiteTests(BaseTeste):
    def test_adaptador_do_caixa_cadastra_e_busca_no_esquema_atual(self):
        produtos = ProdutoController(self.banco)
        sucesso, mensagem = produtos.cadastrar_produto(
            "Refrigerante", "8,50", "789", estoque_inicial=4
        )
        self.assertTrue(sucesso, mensagem)
        produto = produtos.buscar_por_codigo("789")
        self.assertEqual(produto[2:5], ("Refrigerante", 8.5, 4))

    def test_esquema_novo_e_venda_completa(self):
        produto_id = self.novo_produto(
            "Refrigerante", preco=850, codigo="789", estoque=True, qt=2,
            promo_de="03/10/2026", promo_ate="03/10/2026", promo_preco_cent="7,50",
        )
        produtos = ProdutoController(self.banco)
        vendas = VendaController(self.banco)
        produto = produtos.buscar_codigo("789")
        self.assertEqual(produto["nome"], "Refrigerante")
        self.assertEqual(produtos.preco_vigente(produto), 750)
        venda_id = vendas.iniciar_venda()
        self.assertIsNotNone(venda_id)
        self.assertTrue(vendas.adicionar_item(venda_id, produto_id, 1, 8.5))
        self.assertEqual(produtos.por_id(produto_id)["qt_atual"], 1)
        self.assertEqual(
            self.banco.valor(
                "SELECT total_cent FROM vendas WHERE id = ?", (venda_id,)
            ),
            750,
        )

        self.assertTrue(vendas.finalizar_venda(venda_id, 7.5, "Pix"))
        pendentes = vendas.listar_vendas_pendentes()
        self.assertEqual(len(pendentes), 1)
        self.assertEqual((pendentes[0][2], pendentes[0][3]), (750, "fechada"))

    def test_nao_permite_vender_mais_que_o_estoque(self):
        produto_id = self.novo_produto(
            "Agua", preco=300, codigo="123", estoque=True, qt=1
        )
        produtos = ProdutoController(self.banco)
        vendas = VendaController(self.banco)
        venda_id = vendas.iniciar_venda()

        self.assertFalse(vendas.adicionar_item(venda_id, produto_id, 2, 3))
        self.assertEqual(produtos.por_id(produto_id)["qt_atual"], 1)
        self.assertEqual(
            self.banco.valor(
                "SELECT COUNT(*) FROM itens_venda WHERE venda_id = ?", (venda_id,)
            ),
            0,
        )

    def test_arquiva_banco_legado_e_cria_esquema_novo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "legado.db"
            legado = sqlite3.connect(caminho)
            legado.executescript(
                """
                CREATE TABLE produtos (
                    id INTEGER PRIMARY KEY, codigo_barras TEXT, nome TEXT,
                    preco REAL, estoque_atual INTEGER
                );
                CREATE TABLE vendas (
                    id INTEGER PRIMARY KEY, data_venda TEXT, total_venda REAL,
                    forma_pagamento TEXT, sincronizado INTEGER
                );
                CREATE TABLE itens_venda (
                    id INTEGER PRIMARY KEY, venda_id INTEGER, produto_id INTEGER,
                    quantidade INTEGER, preco_unitario REAL
                );
                CREATE TABLE config (
                    id INTEGER PRIMARY KEY, chave_loja TEXT, licenca_ativa INTEGER
                );
                INSERT INTO produtos VALUES (4, '789', 'Refrigerante', 8.5, 7);
                INSERT INTO vendas VALUES
                    (9, '2026-10-03 09:00:00', 8.5, 'Dinheiro', 0);
                INSERT INTO itens_venda VALUES (12, 9, 4, 1, 8.5);
                INSERT INTO config VALUES (1, 'loja-teste', 1);
                """
            )
            legado.close()

            banco = BancoDados(caminho)
            try:
                self.assertEqual(
                    banco.valor("SELECT COUNT(*) FROM produtos"),
                    0,
                )
                self.assertEqual(
                    banco.conexao.execute("PRAGMA user_version").fetchone()[0],
                    VERSAO_ESQUEMA,
                )
            finally:
                banco.fechar()

            arquivo_backup = next(Path(pasta).glob("legado.db.legado-*.bak"))
            backup = sqlite3.connect(arquivo_backup)
            try:
                self.assertEqual(
                    backup.execute(
                        "SELECT nome, preco FROM produtos WHERE id = 4"
                    ).fetchone(),
                    ("Refrigerante", 8.5),
                )
                self.assertEqual(
                    backup.execute(
                        "SELECT total_venda, forma_pagamento FROM vendas WHERE id = 9"
                    ).fetchone(),
                    (8.5, "Dinheiro"),
                )
            finally:
                backup.close()


if __name__ == "__main__":
    unittest.main()
