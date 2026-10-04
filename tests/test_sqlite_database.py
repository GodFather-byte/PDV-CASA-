import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.controllers.produto_controller import ProdutoController
from src.database.conexao import BancoDados
from src.database.esquema import VERSAO_ESQUEMA
from tests.base import BaseTeste


class BancoSQLiteTests(BaseTeste):
    def test_busca_por_codigo_e_preco_promocional(self):
        self.novo_produto("Refrigerante", preco=850, codigo="789", promo_de="03/10/2026", promo_ate="03/10/2026",
                          promo_preco_cent="7,50")
        produtos = ProdutoController(self.banco)
        produto = produtos.buscar_codigo("789")
        self.assertEqual(produto["nome"], "Refrigerante")
        self.assertEqual(produtos.preco_vigente(produto), 750)

    def test_tabela_mesas_do_prototipo_some_na_v10(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "v9.db"
            b = BancoDados(caminho)
            b.executar("CREATE TABLE mesas (id INTEGER PRIMARY KEY, numero INTEGER)")    # como estava no banco v9
            b.executar("PRAGMA user_version = 9")
            b.fechar()
            b = BancoDados(caminho)
            try:
                self.assertEqual(b.valor("PRAGMA user_version"), VERSAO_ESQUEMA)
                self.assertIsNone(b.valor("SELECT name FROM sqlite_master WHERE name = 'mesas'"))
            finally:
                b.fechar()

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
