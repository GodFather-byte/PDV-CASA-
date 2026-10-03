"""Comandas: a comanda 2 convive com a mesa 2, aparece na lista de mesas abertas e segue as regras de mesa."""
from __future__ import annotations

import os
import tempfile
import unittest

from src.controllers.config_controller import ConfigController
from src.controllers.impressao_controller import ImpressaoController
from src.controllers.relatorio_controller import RelatorioController
from src.core import formatacao as fmt
from src.core.erros import ErroNegocio, ErroValidacao
from src.core.posicao import interpretar, nome, parece_comanda, rotulo
from src.database.conexao import BancoDados
from src.database.esquema import VERSAO_ESQUEMA
from tests.test_caixa import BaseCaixa


class TesteNotacao(unittest.TestCase):
    def test_interpreta_mesa_e_comanda(self):
        self.assertEqual(interpretar("5"), (False, 5))
        self.assertEqual(interpretar(" 12 "), (False, 12))
        for texto in ("C2", "c2", "c 2", " C2 ", "C002"):
            self.assertEqual(interpretar(texto), (True, 2), texto)
        self.assertEqual(interpretar("0"), (False, 0))          # a tela usa 0 para o balcão

    def test_recusa_o_que_nao_e_posicao(self):
        for texto in ("", "abc", "C", "CC2", "2C", "C-2", "C2.5", "C0", None, "12345"):
            with self.assertRaises(ValueError, msg=repr(texto)):
                interpretar(texto)

    def test_parece_comanda_so_com_a_letra_c(self):
        self.assertTrue(parece_comanda("C2"))
        self.assertTrue(parece_comanda("c 12"))
        for texto in ("2", "SKOL", "", None):
            self.assertFalse(parece_comanda(texto), repr(texto))

    def test_rotulo_e_nome(self):
        self.assertEqual((rotulo(False, 5), rotulo(True, 5)), ("5", "C5"))
        self.assertEqual((nome(False, 5), nome(True, 5)), ("Mesa 5", "Comanda 5"))


class TesteComandas(BaseCaixa):
    def comanda(self, numero, *itens):
        vid, _ = self.caixa.abrir_mesa(numero, comanda=True)
        for pid, qtd in itens:
            self.caixa.adicionar_item(vid, pid, qtd)
        return vid

    def abertas(self):
        return [(m["rotulo"], m["subtotal_cent"]) for m in self.caixa.mesas()]

    def fechar(self, vid, forma="Dinheiro"):
        self.pagar(vid, forma, self.caixa.obter(vid)["total_cent"])
        return self.caixa.fechar(vid)

    # ------------------------------------------------------------- abertura
    def test_skol_na_comanda_2_aparece_como_uma_mesa_aberta(self):
        vid = self.comanda(2, (self.skol, 1))
        abertas = [(m["id"], m["rotulo"], m["comanda"], m["posicao"], m["status"], m["n_itens"]) for m in self.caixa.mesas()]
        self.assertEqual(abertas, [(vid, "C2", 1, 2, "aberta", 1)])
        self.assertEqual(self.caixa.obter(vid)["total_cent"], 880)          # 8,00 + 10% de serviço

    def test_comanda_2_e_mesa_2_coexistem(self):
        mesa, _ = self.caixa.abrir_mesa(2)
        comanda, criada = self.caixa.abrir_mesa(2, comanda=True)
        self.assertTrue(criada)
        self.assertNotEqual(mesa, comanda)
        self.assertEqual(self.caixa.abrir_mesa(2), (mesa, False))
        self.assertEqual(self.caixa.abrir_mesa(2, comanda=True), (comanda, False))
        self.assertEqual([m["rotulo"] for m in self.caixa.mesas()], ["2", "C2"])      # mesas primeiro

    def test_nao_ha_duas_comandas_abertas_com_o_mesmo_numero(self):
        self.caixa.abrir_mesa(7, comanda=True)
        with self.assertRaises(Exception):
            self.banco.inserir("vendas", {"uuid": "x", "modalidade": "mesa", "posicao": 7, "comanda": 1,
                                          "aberta_em": "2026-10-03 21:00:00"})

    def test_comanda_fechada_libera_o_numero_para_outro_cliente(self):
        vid = self.comanda(2, (self.skol, 1))
        self.fechar(vid)
        novo, criada = self.caixa.abrir_mesa(2, comanda=True)
        self.assertTrue(criada)
        self.assertNotEqual(novo, vid)

    def test_numero_da_comanda_respeita_a_configuracao(self):
        for invalido in (0, 201):
            with self.assertRaises(ErroNegocio):
                self.caixa.abrir_mesa(invalido, comanda=True)
        self.banco.cfg_set("num_comandas", 5)
        self.assertTrue(self.caixa.abrir_mesa(5, comanda=True)[1])
        with self.assertRaises(ErroNegocio):
            self.caixa.abrir_mesa(6, comanda=True)
        self.assertTrue(self.caixa.abrir_mesa(30)[1])                       # o limite das mesas é outro

    def test_comandas_desligadas_nao_afetam_as_mesas(self):
        self.banco.cfg_set("num_comandas", 0)
        with self.assertRaises(ErroNegocio) as e:
            self.caixa.abrir_mesa(1, comanda=True)
        self.assertIn("desligadas", str(e.exception))
        self.assertTrue(self.caixa.abrir_mesa(1)[1])

    # -------------------------------------------------------------- serviço
    def test_servico_da_comanda_e_o_da_mesa_sao_independentes(self):
        self.banco.cfg_set("cobra_servico_comanda", "N")
        c = self.comanda(3, (self.skol, 5))
        m = self.vender((self.skol, 5), mesa=3)
        self.assertEqual((self.caixa.obter(c)["total_cent"], self.caixa.obter(m)["total_cent"]), (4000, 4400))
        self.banco.cfg_set("cobra_servico_comanda", "S")
        self.banco.cfg_set("cobra_servico_mesa", "N")
        self.caixa.recalcular(c)
        self.caixa.recalcular(m)
        self.assertEqual((self.caixa.obter(c)["total_cent"], self.caixa.obter(m)["total_cent"]), (4400, 4000))

    # ------------------------------------------------- pré-conta e fechamento
    def test_pre_conta_cupom_e_fechamento_da_comanda(self):
        vid = self.comanda(2, (self.skol, 2))
        imp = ImpressaoController(self.banco)
        self.caixa.enviar_conta(vid)
        pre = imp.pre_conta(vid)
        self.assertIn("CONTA DA COMANDA", pre)
        self.assertIn("Comanda 2", pre)
        self.assertNotIn("CONTA DA MESA", pre)
        v = self.fechar(vid)
        self.assertEqual((v["status"], v["modalidade"], v["comanda"]), ("fechada", "mesa", 1))
        cupom = imp.cupom(vid)
        self.assertIn("Comanda 2", cupom)
        self.assertNotIn("Mesa 2", cupom)
        self.assertTrue(all(len(l) <= 40 for l in cupom.splitlines()))

    def test_pre_conta_da_mesa_continua_igual(self):
        vid = self.vender((self.skol, 1), mesa=2)
        pre = ImpressaoController(self.banco).pre_conta(vid)
        self.assertIn("CONTA DA MESA", pre)
        self.assertIn("Mesa 2", pre)

    # --------------------------------------------------------- transferências
    def test_transferir_mesa_para_comanda_livre_e_de_volta(self):
        vid = self.vender((self.skol, 2), mesa=5)
        self.assertEqual(self.caixa.transferir_mesa(5, "C2"), vid)
        v = self.caixa.obter(vid)
        self.assertEqual((v["comanda"], v["posicao"]), (1, 2))
        self.assertEqual(self.abertas(), [("C2", 1600)])
        self.assertEqual(self.caixa.transferir_mesa((True, 2), 5), vid)
        self.assertEqual(self.abertas(), [("5", 1600)])

    def test_transferir_para_posicao_aberta_soma_os_itens(self):
        self.vender((self.skol, 2), mesa=2)
        self.comanda(2, (self.agua, 1))
        self.caixa.transferir_mesa(2, "C2")             # mesma numeração, tipos diferentes
        self.assertEqual(self.abertas(), [("C2", 1950)])

    def test_transferencia_recusa_origem_igual_ou_fechada(self):
        self.comanda(2, (self.skol, 1))
        with self.assertRaises(ErroNegocio):
            self.caixa.transferir_mesa("C2", "C2")
        with self.assertRaises(ErroNegocio) as e:
            self.caixa.transferir_mesa("C9", 3)
        self.assertIn("comanda 9 não está aberta", str(e.exception))
        with self.assertRaises(ErroNegocio):
            self.caixa.transferir_mesa(2, 3)            # a mesa 2 não existe: só a comanda 2
        with self.assertRaises(ErroNegocio):
            self.caixa.transferir_mesa("C2", "C999")    # fora do limite de comandas
        self.assertEqual(self.abertas(), [("C2", 800)])

    def test_transferir_varias_aceita_mesas_e_comandas(self):
        self.vender((self.skol, 1), mesa=3)
        self.comanda(1, (self.skol, 2))
        self.comanda(4, (self.agua, 1))
        destino = self.caixa.transferir_varias([3, "C1", (True, 4)], "C9")
        self.assertEqual(self.caixa.obter(destino)["subtotal_cent"], 800 + 1600 + 350)
        self.assertEqual(self.abertas(), [("C9", 2750)])

    def test_transferir_varias_nao_move_nada_se_uma_origem_falha(self):
        self.comanda(1, (self.skol, 1))
        with self.assertRaises(ErroNegocio):
            self.caixa.transferir_varias(["C1", "C8"], 5)
        self.assertEqual(self.abertas(), [("C1", 800)])

    def test_transferir_parte_dos_itens_para_comanda(self):
        vid = self.vender((self.skol, 5), mesa=10)
        item = self.caixa.itens(vid)[0]["id"]
        self.caixa.transferir_item(item, "C2", 2)
        self.assertEqual(self.abertas(), [("10", 2400), ("C2", 1600)])
        with self.assertRaises(ErroNegocio):
            self.caixa.transferir_item(item, 10, 1)     # a mesma mesa
        self.assertEqual(self.abertas(), [("10", 2400), ("C2", 1600)])

    # ------------------------------------------------ repique, turno, relatórios
    def test_repique_da_comanda_fica_ligado_a_venda_da_comanda(self):
        mesa = self.vender((self.skol, 1), mesa=2)
        comanda = self.comanda(2, (self.skol, 1))
        self.turnos.repique(self.turno, self.adm, 2, 300, comanda=True)
        self.turnos.repique(self.turno, self.adm, 2, 200)
        repiques = {r["valor_cent"]: r["venda_id"] for r in self.banco.todos("SELECT valor_cent, venda_id FROM repiques")}
        self.assertEqual(repiques, {300: comanda, 200: mesa})

    def test_turno_conta_mesa_2_e_comanda_2_como_posicoes_diferentes(self):
        self.fechar(self.vender((self.skol, 1), mesa=2))
        self.fechar(self.comanda(2, (self.skol, 1)))
        self.assertEqual(self.turnos.resumo(self.turno)["posicoes"], 2)

    def test_relatorios_listam_comandas_junto_das_mesas(self):
        for vid in (self.vender((self.skol, 1), mesa=2), self.comanda(2, (self.agua, 1))):
            self.pagar(vid, "Dinheiro", self.caixa.obter(vid)["total_cent"])
            self.caixa.fechar(vid, garcom_id=self.adm)
        rel = RelatorioController(self.banco)
        f = {"de": fmt.hoje(), "ate": fmt.hoje()}
        r = rel.comandas(f)
        self.assertEqual(r.titulo, "Mesas e comandas")
        self.assertEqual([(l[0], l[-1]) for l in r.linhas], [("2", "8,80"), ("C2", "3,85")])
        self.assertEqual(rel.garcons(f).linhas[0][:3], ["ADM", "2", "2"])       # 2 cupons em 2 posições

    def test_filtro_de_modalidade_separa_comanda_de_mesa(self):
        self.fechar(self.vender((self.skol, 1), mesa=2))
        self.fechar(self.comanda(2, (self.agua, 1)))
        self.fechar(self.vender((self.skol, 1)))
        rel = RelatorioController(self.banco)
        f = {"de": fmt.hoje(), "ate": fmt.hoje()}

        def cupons(modalidade):
            return [(c["modalidade"], c["comanda"], c["posicao"]) for c in rel.cupons({**f, "modalidade": modalidade})]
        self.assertEqual(cupons("mesa"), [("mesa", 0, 2)])
        self.assertEqual(cupons("comanda"), [("mesa", 1, 2)])
        self.assertEqual(cupons("balcao"), [("balcao", 0, 0)])
        self.assertEqual(len(rel.cupons(f)), 3)
        self.assertEqual(dict(rel.vendas_periodo(f).rodape)["  Mesa/Comanda/Balcão"], "19,50")

    def test_comanda_vai_para_a_nuvem_como_mesa(self):
        from src.controllers.sync_controller import SyncController
        self.fechar(self.comanda(6, (self.skol, 1)))
        vendas = SyncController(self.banco).montar_lote()["vendas"]
        self.assertEqual([(v["modalidade"], v["posicao"]) for v in vendas], [("mesa", 6)])


class TesteConfigComandas(BaseCaixa):
    def test_configuracao_de_comandas(self):
        cfg = ConfigController(self.banco)
        cfg.salvar_config({"num_comandas": "0", "cobra_servico_comanda": "N", "painel_mesas_fixo": "N"})
        self.assertEqual((self.banco.cfg_int("num_comandas", 200), self.banco.cfg_bool("cobra_servico_comanda", True),
                          self.banco.cfg_bool("painel_mesas_fixo", True)), (0, False, False))
        for invalido in ("-1", "10000", "abc"):
            with self.assertRaises(ErroValidacao, msg=invalido):
                cfg.salvar_config({"num_comandas": invalido})
        self.assertNotIn("controle_comandas", cfg.todas())      # campo antigo, sem efeito, trocado por num_comandas


class TesteMigracaoV4(unittest.TestCase):
    def test_banco_v3_ganha_a_coluna_comanda_sem_perder_mesas_abertas(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "v3.db")
            b = BancoDados(caminho)
            # volta ao desenho da v3: sem a coluna e com o índice que só olhava a posição
            b.executar("DROP INDEX ix_posicao_aberta")
            b.executar("ALTER TABLE vendas DROP COLUMN comanda")
            b.executar("""CREATE UNIQUE INDEX ix_mesa_aberta ON vendas(posicao)
                          WHERE modalidade = 'mesa' AND status IN ('aberta','conta_enviada')""")
            b.executar("PRAGMA user_version = 3")
            b.inserir("vendas", {"uuid": "mesa-2", "modalidade": "mesa", "posicao": 2, "aberta_em": "2026-10-03 21:00:00"})
            b.fechar()

            b = BancoDados(caminho)
            try:
                self.assertEqual(b.valor("PRAGMA user_version"), VERSAO_ESQUEMA)
                self.assertEqual(b.valor("SELECT comanda FROM vendas WHERE uuid = 'mesa-2'"), 0)
                indices = {r[1] for r in b.todos("PRAGMA index_list(vendas)")}
                self.assertIn("ix_posicao_aberta", indices)
                self.assertNotIn("ix_mesa_aberta", indices)
                comanda = {"modalidade": "mesa", "posicao": 2, "comanda": 1, "aberta_em": "2026-10-03 21:05:00"}
                b.inserir("vendas", {"uuid": "comanda-2", **comanda})      # convive com a mesa 2 já aberta
                with self.assertRaises(Exception):
                    b.inserir("vendas", {"uuid": "comanda-2-de-novo", **comanda})
            finally:
                b.fechar()


if __name__ == "__main__":
    unittest.main()
