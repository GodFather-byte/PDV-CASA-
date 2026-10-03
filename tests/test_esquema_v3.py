"""Esquema v3: migração a partir de um banco v2, índices dos relatórios e filtros por dia sargáveis."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime

from src.controllers.caixa_controller import CaixaController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.turno_controller import TurnoController
from src.database.conexao import BancoDados
from tests.base import BaseTeste


class TesteMigracaoV3(unittest.TestCase):
    def test_v2_ganha_na_gaveta_e_os_indices_sem_perder_dados(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "v2.db")
            b = BancoDados(caminho)
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem) VALUES ('Visa Crédito', 20)")
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem, aciona_tef) VALUES ('Maquineta', 21, 1)")
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem) VALUES ('Voucher', 22)")
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem) VALUES ('Transferência', 23)")
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem) VALUES ('Crédito Loja', 24)")
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem) VALUES ('Cartela de Ticket', 25)")
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem) VALUES ('Cartão Elo', 26)")
            b.executar("INSERT INTO tipos_pagamento(tipo, ordem) VALUES ('PIX Pessoal', 27)")
            b.executar("DROP INDEX ix_vendas_cliente")
            b.executar("DROP INDEX ix_movest_ref")
            b.executar("ALTER TABLE tipos_pagamento DROP COLUMN na_gaveta")      # como era no banco v2
            b.executar("PRAGMA user_version = 2")
            b.fechar()

            b = BancoDados(caminho)
            try:
                self.assertEqual(b.valor("PRAGMA user_version"), 3)
                formas = {r["tipo"]: r["na_gaveta"] for r in b.todos("SELECT tipo, na_gaveta FROM tipos_pagamento")}
                # Sai da gaveta só o que é claramente eletrônico (cartão, Pix, transferência, TEF). O resto mantém o
                # comportamento antigo (fica); "Crédito Loja" e "Cartela de Ticket" não podem ser confundidos com cartão.
                self.assertEqual(formas, {
                    "Dinheiro": 1, "Cheque": 1, "Ticket": 1, "Contra Vale": 1, "Voucher": 1, "Visa Crédito": 1,
                    "Crédito Loja": 1, "Cartela de Ticket": 1,
                    "Cartão Débito": 0, "Cartão Crédito": 0, "Pix": 0, "Maquineta": 0, "Transferência": 0,
                    "Cartão Elo": 0, "PIX Pessoal": 0})
                indices = {r[1] for r in b.todos("PRAGMA index_list(vendas)")}
                self.assertIn("ix_vendas_cliente", indices)
                self.assertIn("ix_movest_ref", {r[1] for r in b.todos("PRAGMA index_list(movimentos_estoque)")})
            finally:
                b.fechar()

    def test_reabrir_um_banco_atual_nao_repete_a_migracao(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "atual.db")
            b = BancoDados(caminho)
            b.executar("UPDATE tipos_pagamento SET na_gaveta = 1 WHERE tipo = 'Pix'")     # escolha do administrador
            b.fechar()
            b = BancoDados(caminho)
            try:
                self.assertEqual(b.valor("SELECT na_gaveta FROM tipos_pagamento WHERE tipo = 'Pix'"), 1)
            finally:
                b.fechar()


class TesteIndicesEFiltros(BaseTeste):
    def setUp(self):
        super().setUp()
        self.adm = self.operador_adm()
        TurnoController(self.banco).abrir(self.adm, 1, 0)
        self.caixa = CaixaController(self.banco, self.adm)
        self.produto = self.novo_produto("SKOL", 1000)
        self.rel = RelatorioController(self.banco)

    def plano(self, sql, params=()):
        return " | ".join(r[3] for r in self.banco.todos("EXPLAIN QUERY PLAN " + sql, params))

    def vender_em(self, quando):
        self._hora["t"] = datetime.fromisoformat(quando)
        v = self.caixa.abrir_balcao()
        self.caixa.adicionar_item(v, self.produto, 1)
        self.caixa.adicionar_pagamento(v, self.tipo("Dinheiro"), 1000)
        self.caixa.fechar(v)

    def test_consultas_quentes_usam_indices(self):
        self.assertIn("ix_vendas_cliente", self.plano(
            "SELECT 1 FROM vendas v WHERE v.cliente_id = ? AND v.status = 'fechada' AND v.fechada_em >= ? AND v.fechada_em < ?",
            (1, "2026-01-01", "2026-02-01")))
        self.assertIn("ix_movest_ref", self.plano(       # confere a cada fechamento de venda se o estoque já baixou
            "SELECT 1 FROM movimentos_estoque WHERE ref_tipo = 'venda' AND ref_id = ? AND tipo = 'venda' LIMIT 1", (1,)))
        self.assertIn("ix_itens_produto", self.plano("SELECT SUM(quantidade) FROM itens_venda WHERE produto_id = ?", (1,)))
        self.assertIn("ix_vendas_turno", self.plano("SELECT COUNT(*) FROM vendas WHERE turno_id = ?", (1,)))
        self.assertIn("fechada_em>?", self.plano(
            "SELECT 1 FROM vendas v WHERE v.status IN ('fechada') AND v.fechada_em >= ? AND v.fechada_em < ?",
            ("2026-10-01", "2026-11-01")))

    def test_filtro_por_dia_inclui_o_dia_inteiro_e_nada_alem_dele(self):
        for quando in ("2026-10-02 23:59:59", "2026-10-03 00:00:00", "2026-10-03 12:00:00",
                       "2026-10-03 23:59:59", "2026-10-04 00:00:00"):
            self.vender_em(quando)
        dia = self.rel.cupons({"de": "2026-10-03", "ate": "2026-10-03"})
        self.assertEqual([c["fechada_em"] for c in dia],
                         ["2026-10-03 00:00:00", "2026-10-03 12:00:00", "2026-10-03 23:59:59"])
        self.assertEqual(len(self.rel.cupons({"de": "2026-10-03"})), 4)       # sem data final: até o fim
        self.assertEqual(len(self.rel.cupons({"ate": "2026-10-03"})), 4)      # sem data inicial: desde o começo
        self.assertEqual(len(self.rel.cupons({})), 5)

    def test_painel_conta_so_o_dia_de_hoje(self):
        for quando in ("2026-10-02 23:59:59", "2026-10-03 00:00:00", "2026-10-03 21:00:00", "2026-10-04 00:00:00"):
            self.vender_em(quando)
        self._hora["t"] = datetime(2026, 10, 3, 22, 0, 0)
        self.assertEqual(self.rel.painel()["vendas_dia"], 2)

    def test_clientes_inativos_e_extrato_respeitam_os_limites_do_periodo(self):
        from src.controllers.cadastro_controller import CadastroController
        from src.controllers.caderneta_controller import CadernetaController  # noqa: F401
        cliente = CadastroController(self.banco).salvar("clientes", {"numero_consulta": "1", "nome": "ANA"})
        self._hora["t"] = datetime(2026, 10, 3, 23, 59, 59)
        v = self.caixa.abrir_caderneta(cliente)
        self.caixa.adicionar_item(v, self.produto, 1)
        self.caixa.fechar(v)
        inativos = lambda desde, ate: [l[1] for l in self.rel.clientes_inativos(desde, ate).linhas]
        self.assertEqual(inativos("2026-10-03", "2026-10-03"), [])            # comprou no último segundo do período
        self.assertEqual(inativos("2026-10-04", "2026-10-10"), ["ANA"])
        self.assertEqual(inativos("2026-09-01", "2026-10-02"), ["ANA"])


if __name__ == "__main__":
    unittest.main()
