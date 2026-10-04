"""Código 1002: libera a saída de quem não consumiu nada e imprime o comprovante de saída."""
from __future__ import annotations

from src.controllers.config_controller import ConfigController
from src.controllers.impressao_controller import ImpressaoController
from src.core.erros import ErroNegocio, ErroValidacao
from tests.test_caixa import BaseCaixa


class TesteSaidaSemConsumo(BaseCaixa):
    def test_comanda_aberta_vazia_e_liberada_e_registrada_no_turno(self):
        self.caixa.abrir_mesa(180, comanda=True)
        info = self.caixa.liberar_saida(True, 180)
        self.assertEqual((info["nome"], info["rotulo"], info["turno"]), ("Comanda 180", "180", 1))
        self.assertEqual(self.caixa.mesas(), [])                               # a posição ficou livre
        saidas = self.caixa.saidas_liberadas(self.turno)
        self.assertEqual([(s["rotulo"], s["operador"]) for s in saidas], [("180", "ADM")])

    def test_comanda_que_nunca_foi_aberta_tambem_libera(self):
        self.assertEqual(self.caixa.liberar_saida(True, 77)["nome"], "Comanda 77")
        self.assertEqual(len(self.caixa.saidas_liberadas(self.turno)), 1)

    def test_com_consumo_ou_pagamento_recusa(self):
        vid = self.vender((self.skol, 1), mesa=12)
        with self.assertRaisesRegex(ErroNegocio, "consumo de R\\$ 8,80"):
            self.caixa.liberar_saida(False, 12)
        vazia, _ = self.caixa.abrir_mesa(13)
        self.caixa.adicionar_pagamento(vazia, self.tipo("Dinheiro"), 1000)
        with self.assertRaisesRegex(ErroNegocio, "pagamento lançado"):
            self.caixa.liberar_saida(False, 13)
        self.assertEqual(self.caixa.saidas_liberadas(self.turno), [])
        self.assertEqual(self.caixa.obter(vid)["status"], "aberta")

    def test_itens_cancelados_contam_como_sem_consumo(self):
        vid = self.vender((self.skol, 1), mesa=12)
        self.caixa.cancelar_item(self.caixa.itens(vid)[0]["id"])
        self.caixa.liberar_saida(False, 12)
        self.assertEqual(self.caixa.obter(vid)["status"], "cancelada")

    def test_exige_turno_aberto(self):
        self.turnos.fechar(self.turno, self.adm, 10000)
        with self.assertRaises(ErroNegocio):
            self.caixa.liberar_saida(True, 5)

    def test_codigo_configuravel(self):
        self.assertTrue(self.caixa.eh_codigo_saida("1002"))
        self.assertTrue(self.caixa.eh_codigo_saida("01002"))
        self.assertFalse(self.caixa.eh_codigo_saida("1003"))
        cfg = ConfigController(self.banco)
        cfg.salvar_config({"codigo_saida": "999"})
        self.assertTrue(self.caixa.eh_codigo_saida("999"))
        with self.assertRaises(ErroValidacao):
            cfg.salvar_config({"codigo_saida": "50"})                      # já é o da comissão
        cfg.salvar_config({"codigo_saida": ""})
        self.assertFalse(self.caixa.eh_codigo_saida("1002"))

    def test_comprovante_tem_a_casa_a_comanda_a_data_e_a_hora(self):
        self.banco.atualizar("loja", 1, {"nome_fantasia": "Boate Estrela"})
        info = self.caixa.liberar_saida(True, 180)
        texto = ImpressaoController(self.banco).comprovante_saida(info, "ADM")
        for trecho in ("BOATE ESTRELA", "COMPROVANTE DE SAÍDA", "COMANDA 180", "03/10/2026", "21:00", "SEM CONSUMO", "ADM"):
            self.assertIn(trecho, texto)


try:
    from tests.test_comissao_na_tela import BaseNaTela
    from tests.ui_robo import clicar, entradas
except ImportError:                       # sem Tkinter só rodam as regras
    BaseNaTela = None

if BaseNaTela is not None:
    class TesteSaidaNaTelaDoCaixa(BaseNaTela):
        def test_1002_na_comanda_imprime_a_saida_e_libera(self):
            self.posicao("180")                                              # chama a comanda 180 (vazia)
            impressos = []
            self.robo.quando("Visualizador", lambda w: (impressos.append(w.texto), w.destroy()))
            self.digitar_codigo("1002")
            self.assertEqual(len(impressos), 1)
            self.assertIn("COMPROVANTE DE SAÍDA", impressos[0])
            self.assertIn("COMANDA 180", impressos[0])
            self.assertIn("Saída liberada", self.status())
            self.assertEqual(self.ctx.caixa.mesas(), [])
            self.sem_travar()

        def test_1002_com_consumo_avisa_e_nao_imprime(self):
            self.posicao("180")
            self.cx.var_cod.set("1"); self.cx._enter_codigo(); self.cx.update()
            self.valor("1")                                                  # 1 SKOL na comanda
            avisos, impressos = [], []
            self.dialogos({"Atenção": lambda w: (avisos.extend(self.textos(w)), clicar(w, "OK"))})
            self.robo.quando("Visualizador", lambda w: (impressos.append(w.texto), w.destroy()))
            self.digitar_codigo("1002")
            self.assertTrue(any("tem consumo" in a for a in avisos), avisos)
            self.assertEqual(impressos, [])
            self.sem_travar()

        def test_1002_no_balcao_pergunta_a_comanda(self):
            self.posicao("0")
            impressos = []
            self.dialogos({"Saída sem consumo": lambda w: (entradas(w)[0].insert(0, "55"), clicar(w, "OK"))})
            self.robo.quando("Visualizador", lambda w: (impressos.append(w.texto), w.destroy()))
            self.digitar_codigo("1002")
            self.assertIn("COMANDA 55", impressos[0])
            self.sem_travar()
