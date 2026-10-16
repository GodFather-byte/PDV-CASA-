"""Excluir um produto do cadastro: sem venda apaga de verdade; já vendido fica guardado inativo e libera o código."""
from __future__ import annotations

from src.controllers.cadastro_controller import CadastroController
from src.core.erros import ErroNegocio
from tests.test_excluir_produtos import BaseExcluir


class TesteExcluirProdutoCadastrado(BaseExcluir):
    def setUp(self):
        super().setUp()
        self.cad = CadastroController(self.banco)

    def test_sem_venda_apaga_de_verdade_e_o_codigo_volta_a_ficar_livre(self):
        codigo = self.prod.por_id(self.skol)["codigo"]
        self.assertIsNone(self.cad.excluir("produtos", self.skol))
        self.assertIsNone(self.prod.por_id(self.skol))
        self.assertIsNone(self.banco.um("SELECT 1 FROM produtos WHERE codigo = ?", (codigo,)))

    def test_ja_vendido_fica_guardado_inativo_e_libera_o_codigo(self):
        antes = self.prod.por_id(self.skol)
        self.vender_e_fechar(self.skol)
        aviso = self.cad.excluir("produtos", self.skol)
        self.assertIn("já foi vendido", aviso)
        p = self.prod.por_id(self.skol)
        self.assertEqual(p["ativo"], 0)
        self.assertNotEqual(p["codigo"], antes["codigo"])
        self.assertNotEqual(p["nome"], antes["nome"])
        # o código e o nome antigos já servem para um produto novo
        novo = self.novo_produto(antes["nome"], 500, codigo=antes["codigo"])
        self.assertEqual(self.prod.por_id(novo)["codigo"], antes["codigo"])

    def test_o_historico_da_venda_continua(self):
        vid = self.vender_e_fechar(self.skol)
        self.cad.excluir("produtos", self.skol)
        self.assertEqual(len(self.caixa.itens(vid)), 1)

    def test_recusa_se_esta_numa_venda_aberta(self):
        self.vender((self.skol, 1))
        with self.assertRaises(ErroNegocio):
            self.cad.excluir("produtos", self.skol)
        self.assertEqual(self.prod.por_id(self.skol)["ativo"], 1)

    def test_apaga_tambem_o_estoque_dele(self):
        self.cad.excluir("produtos", self.skol)
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM movimentos_estoque WHERE produto_id = ?", (self.skol,)), 0)
