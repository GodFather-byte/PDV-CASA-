"""Comissão das garotas na própria tela do caixa: o código 50 na linha de entrada, F12 e Delete na comanda da garota,
a via impressa a cada lançamento e as garotas como ícones no rodapé, ao lado do balcão."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from tkinter import ttk
from unittest import mock

from src.ui.painel_mesas import montar_tiles
from tests.test_ui import BaseUI
from tests.ui_robo import clicar, entradas


class BaseNaTela(BaseUI):
    def setUp(self):
        super().setUp()
        self.abrir_turno()
        from src.ui.caixa_ui import JanelaCaixa
        self.cx = JanelaCaixa(self.root, self.ctx)
        self.cx.update()
        self.com = self.ctx.comissoes
        self.turno = self.ctx.turnos.atual()["id"]

    # ---------------------------------------------------------------- ajudantes
    def posicao(self, texto):
        self.cx.var_pos.set(texto); self.cx.chamar_mesa(); self.cx.update()

    def digitar_codigo(self, texto):
        self.cx.var_cod.set(texto); self.cx._enter_codigo(); self.cx.update()

    def valor(self, texto):
        self.cx.var_qtd.set(texto); self.cx.confirmar_item(); self.cx.update()

    def cadastrar(self, numero, nome, ativa="S"):
        self.ctx.cadastros.salvar("garotas", {"numero": numero, "nome": nome, "ativo": ativa})

    def dar(self, garota, reais):
        return self.com.lancar(garota, round(reais * 100), self.turno, self.ctx.operador_id)

    def lancar_pela_linha(self, garota, reais, comanda=True):
        """O fluxo do operador: comanda da garota (ou balcão), código 50, número (se preciso) e valor."""
        self.posicao(str(garota) if comanda else "0")
        self.digitar_codigo("50")
        if not comanda:
            self.digitar_codigo(str(garota))
        self.valor(reais)

    def status(self):
        return self.cx.status.cget("text")

    def linhas(self):
        return [[str(c) for c in self.cx.grade.valores(i)] for i in self.cx.grade.tree.get_children()]

    def tiles(self):
        self.cx.carregar_mesas()
        return {t["chave"]: t for t in self.cx.painel_mesas.tiles()}

    @staticmethod
    def textos(janela):
        achados = []

        def varre(w):
            for f in w.winfo_children():
                if isinstance(f, ttk.Label):
                    achados.append(str(f.cget("text")))
                varre(f)
        varre(janela)
        return achados

    def dialogos(self, regras: dict, vezes: int = 400):
        """Responde aos diálogos pelo título (valor = função(janela) ou o texto do botão que será clicado)."""
        self.robo.regras[:] = [r for r in self.robo.regras if r[0] != "Dialogo"]
        feitos = set()

        def acao(w):
            alvo = next((v for t, v in regras.items() if w.title().startswith(t)), None)
            if alvo is None or str(w) in feitos:
                return
            feitos.add(str(w))
            alvo(w) if callable(alvo) else clicar(w, alvo)
        self.robo.quando("Dialogo", acao, vezes=vezes)

    def configurar_termica(self):
        pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, pasta, True)
        saida = os.path.join(pasta, "saida.prn")
        self.ctx.impressao.pasta_saida = lambda: Path(pasta)
        self.ctx.config.salvar_maquina({"modo_impressao": "termica", "impressora_termica_conexao": "arquivo",
                                        "impressora_termica_endereco": saida, "impressora_termica_gaveta": "S"})
        return Path(saida)


class TesteLancarNaLinhaDeEntrada(BaseNaTela):
    def test_50_na_comanda_da_garota_traz_o_numero_e_pede_so_o_valor(self):
        cx = self.cx
        with mock.patch("src.ui.comissao_ui.dialogo_comissao", side_effect=AssertionError("abriu a janela")):
            self.posicao("180")
            self.digitar_codigo("50")
            self.assertTrue(cx.modo_comissao)
            self.assertEqual((cx.lbl_cod_titulo.cget("text"), cx.lbl_qtd_titulo.cget("text")), ("Garota nº", "Valor (R$)"))
            self.assertEqual(cx.var_cod.get(), "180")                             # a comanda é a garota
            self.assertEqual(str(cx.ent_qtd.cget("state")), "normal")
            self.assertIs(cx.focus_lastfor(), cx.ent_qtd)                         # já no valor
            self.valor("25,00")
        c = self.banco.um("SELECT garota, valor_cent, status, turno_id, operador_id FROM comissoes_garotas")
        self.assertEqual(tuple(c), (180, 2500, "pendente", self.turno, self.ctx.operador_id))
        self.assertIn("Comissão de R$ 25,00 lançada para a garota 180", self.status())
        self.assertIn("A pagar a ela: R$ 25,00", self.status())
        self.assertFalse(cx.modo_comissao)                                         # a linha volta ao normal
        self.assertEqual((cx.lbl_cod_titulo.cget("text"), cx.lbl_qtd_titulo.cget("text")), ("Código", "Quantidade"))
        self.assertEqual((cx.var_cod.get(), cx.var_qtd.get(), str(cx.ent_qtd.cget("state"))), ("", "", "disabled"))
        self.assertIs(cx.focus_lastfor(), cx.ent_codigo)
        self.assertEqual(cx.grade.total(), 1)                                      # a comissão aparece marcada na comanda
        self.assertEqual(cx.lbl_total.cget("text"), "0,00")                        # e não é venda
        self.assertIsNone(cx.produto)
        self.sem_travar()

    def test_fora_de_comanda_pergunta_a_garota_e_depois_o_valor(self):
        cx = self.cx
        self.posicao("0")
        self.digitar_codigo("50")
        self.assertTrue(cx.modo_comissao)
        self.assertEqual(cx.var_cod.get(), "")
        self.assertIs(cx.focus_lastfor(), cx.ent_codigo)                           # começa pela garota
        self.assertEqual(cx.lbl_desc.cget("text"), "COMISSÃO - digite a garota")
        self.digitar_codigo("180")                                                 # Enter na garota vai para o valor
        self.assertTrue(cx.modo_comissao)
        self.assertIs(cx.focus_lastfor(), cx.ent_qtd)
        self.valor("30,00")
        self.assertEqual(self.com.pendente(180), 3000)
        self.assertFalse(cx.modo_comissao)
        self.sem_travar()

    def test_numero_invalido_nao_avanca_para_o_valor(self):
        cx = self.cx
        self.posicao("0")
        self.digitar_codigo("50")
        self.digitar_codigo("abc")
        self.assertIn("somente números", self.status())
        self.assertTrue(cx.modo_comissao)
        self.assertIs(cx.focus_lastfor(), cx.ent_codigo)
        self.sem_travar()

    def test_da_para_voltar_do_valor_ao_numero_e_lancar_em_outra_garota(self):
        cx = self.cx
        self.posicao("25")                                                         # a comanda de um cliente
        self.digitar_codigo("50")
        self.assertEqual(cx.var_cod.get(), "25")
        self.assertEqual(cx._cima_valor(), "break")                                # seta para cima no valor
        self.assertIs(cx.focus_lastfor(), cx.ent_codigo)
        cx.var_cod.set("180")
        cx._enter_codigo()
        self.valor("30,00")
        self.assertEqual((self.com.pendente(180), self.com.pendente(25)), (3000, 0))
        self.assertEqual(cx.venda()["posicao"], 25)                                # a comanda do cliente continua na tela
        self.sem_travar()

    def test_a_seta_para_cima_fora_da_comissao_nao_faz_nada(self):
        self.assertIsNone(self.cx._cima_valor())

    def test_o_nome_da_garota_aparece_na_descricao_conforme_se_digita(self):
        cx = self.cx
        self.posicao("0")
        self.digitar_codigo("50")
        cx.var_cod.set("180")
        self.assertEqual(cx.lbl_desc.cget("text"), "COMISSÃO - garota 180")          # cadastro vazio: não cobra cadastro
        self.cadastrar(180, "MARIA"); self.cadastrar(7, "ANA", ativa="N")
        cx.var_cod.set("180")
        self.assertEqual(cx.lbl_desc.cget("text"), "COMISSÃO - MARIA")
        cx.var_cod.set("7")
        self.assertEqual(cx.lbl_desc.cget("text"), "COMISSÃO - ANA (inativa)")
        cx.var_cod.set("99")
        self.assertEqual(cx.lbl_desc.cget("text"), "COMISSÃO - não cadastrada")
        cx.var_cod.set("")
        self.assertEqual(cx.lbl_desc.cget("text"), "COMISSÃO - digite a garota")

    def test_esc_cancela_a_comissao_sem_sair_da_comanda(self):
        cx = self.cx
        self.posicao("180")
        self.digitar_codigo("50")
        cx.var_qtd.set("25,00")
        cx._esc_codigo()
        self.assertFalse(cx.modo_comissao)
        self.assertEqual((cx.var_cod.get(), cx.var_qtd.get(), cx.lbl_desc.cget("text")), ("", "", ""))
        self.assertEqual((cx.lbl_cod_titulo.cget("text"), cx.lbl_qtd_titulo.cget("text")), ("Código", "Quantidade"))
        self.assertEqual(cx.venda()["posicao"], 180)                               # o Esc só cancelou a comissão
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM comissoes_garotas"), 0)
        self.sem_travar()

    def test_esc_no_campo_do_valor_tambem_cancela(self):
        self.posicao("180")
        self.digitar_codigo("50")
        self.cx.cancelar_item_pendente()                                           # o que o Esc do campo do valor chama
        self.assertFalse(self.cx.modo_comissao)
        self.assertIs(self.cx.focus_lastfor(), self.cx.ent_codigo)
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM comissoes_garotas"), 0)

    def test_valor_invalido_ou_zero_nao_lanca_e_deixa_corrigir(self):
        cx = self.cx
        self.posicao("180")
        self.digitar_codigo("50")
        self.valor("abc")
        self.assertIn("Valor inválido", self.status())
        self.valor("0")
        self.assertIn("Informe o valor da comissão", self.status())
        self.assertTrue(cx.modo_comissao)
        self.assertIs(cx.focus_lastfor(), cx.ent_qtd)
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM comissoes_garotas"), 0)
        self.valor("12,00")                                                        # corrigiu: agora vai
        self.assertEqual(self.com.pendente(180), 1200)
        self.sem_travar()

    def test_garota_nao_cadastrada_pergunta_antes_de_lancar(self):
        self.cadastrar(1, "OUTRA")                                                 # há cadastro, mas a 180 não está nele
        perguntas = []

        def nao(w):
            perguntas.append(self.textos(w)); clicar(w, "Não")
        self.dialogos({"Garota não cadastrada": nao})
        self.posicao("180")
        self.digitar_codigo("50")
        self.valor("25,00")
        self.assertTrue(any("A garota 180 não está cadastrada." in t for t in perguntas[0]), perguntas)
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM comissoes_garotas"), 0)
        self.assertTrue(self.cx.modo_comissao)
        self.assertIs(self.cx.focus_lastfor(), self.cx.ent_codigo)                 # o erro provável é o número
        self.dialogos({"Garota não cadastrada": "Sim"})
        self.valor("25,00")
        self.assertEqual(self.com.pendente(180), 2500)
        self.sem_travar()

    def test_garota_inativa_pergunta_antes_de_lancar(self):
        self.cadastrar(180, "MARIA", ativa="N")
        self.dialogos({"Garota inativa": "Não"})
        self.posicao("180")
        self.digitar_codigo("50")
        self.valor("25,00")
        self.assertEqual(self.com.pendente(180), 0)
        self.dialogos({"Garota inativa": "Sim"})
        self.valor("25,00")
        self.assertEqual(self.com.pendente(180), 2500)
        self.sem_travar()

    def test_valor_alto_pede_confirmacao(self):
        self.dialogos({"Confirma o valor": "Não"})
        self.posicao("180")
        self.digitar_codigo("50")
        self.valor("600,00")
        self.assertEqual(self.com.pendente(180), 0)
        self.assertIs(self.cx.focus_lastfor(), self.cx.ent_qtd)                    # o erro provável é o valor
        self.dialogos({"Confirma o valor": "Sim"})
        self.valor("600,00")
        self.assertEqual(self.com.pendente(180), 60000)
        self.sem_travar()

    def test_sem_turno_aberto_avisa_e_nao_entra_no_modo(self):
        self.ctx.turnos.fechar(self.turno, self.ctx.operador_id, 10000)
        avisos = []
        self.dialogos({"Aviso": lambda w: (avisos.append(self.textos(w)), clicar(w, "OK"))})
        self.digitar_codigo("50")
        self.assertFalse(self.cx.modo_comissao)
        self.assertTrue(any("Abra o turno" in t for t in avisos[0]), avisos)
        self.sem_travar()

    def test_exige_senha_de_supervisor_do_operador_so_caixa(self):
        self.ctx.cadastros.salvar("operadores", {"nome": "BAR", "senha": "1", "nivel": "0"})
        self.ctx.operador = self.ctx.acesso.autenticar("BAR", "1")
        self.banco.cfg_set("exigir_senha_comissao", "S")
        pedidas = []

        def senha(w):
            pedidas.append(w.title())
            entradas(w)[0].insert(0, "ADM"); clicar(w, "OK")
        self.dialogos({"Autorização": senha})
        self.posicao("180")
        self.digitar_codigo("50")
        self.assertEqual(pedidas, ["Autorização"])
        self.assertTrue(self.cx.modo_comissao)
        self.sem_travar()

    def test_negada_a_senha_nao_entra_no_modo(self):
        self.ctx.cadastros.salvar("operadores", {"nome": "BAR", "senha": "1", "nivel": "0"})
        self.ctx.operador = self.ctx.acesso.autenticar("BAR", "1")
        self.banco.cfg_set("exigir_senha_comissao", "S")
        self.dialogos({"Autorização": "Cancelar"})
        self.posicao("180")
        self.digitar_codigo("50")
        self.assertFalse(self.cx.modo_comissao)
        self.sem_travar()

    def test_escolher_um_produto_no_meio_da_comissao_descarta_a_comissao(self):
        self.posicao("0")
        self.digitar_codigo("50")
        self.cx.selecionar_produto(self.ctx.produtos.por_id(self.skol))
        self.assertFalse(self.cx.modo_comissao)
        self.assertEqual(self.cx.lbl_desc.cget("text"), "SKOL")
        self.assertEqual((self.cx.lbl_cod_titulo.cget("text"), self.cx.lbl_qtd_titulo.cget("text")), ("Código", "Quantidade"))
        self.sem_travar()

    def test_trocar_de_comanda_no_meio_da_comissao_descarta_a_comissao(self):
        self.posicao("180")
        self.digitar_codigo("50")
        self.posicao("181")                                                        # o número 180 não pode valer na 181
        self.assertFalse(self.cx.modo_comissao)
        self.assertEqual(self.cx.var_cod.get(), "")
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM comissoes_garotas"), 0)

    def test_o_produto_continua_funcionando_depois_da_comissao(self):
        self.lancar_pela_linha(180, "25,00")
        self.digitar_codigo("1")
        self.assertEqual(self.cx.produto["nome"], "SKOL")
        self.valor("2")
        self.assertEqual(self.ctx.caixa.itens(self.cx.venda_id)[0]["quantidade"], 2)
        self.assertEqual(self.cx.lbl_total.cget("text"), "17,60")                  # 2 x 8,00 + 10% de serviço; a comissão fica de fora
        self.sem_travar()

    def test_com_a_opcao_desligada_o_codigo_50_volta_a_abrir_a_janela(self):
        self.banco.cfg_set("comissao_na_linha", "N")
        aberta = []

        def lancando(w):
            aberta.append(w.title())
            ents = entradas(w)
            ents[1].insert(0, "25,00")
            w.after(10, lambda: clicar(w, "Lançar"))
        self.dialogos({"Comissão da garota": lancando})
        self.posicao("180")
        self.digitar_codigo("50")
        self.assertEqual(aberta, ["Comissão da garota"])
        self.assertFalse(self.cx.modo_comissao)
        self.assertEqual(self.com.pendente(180), 2500)
        self.sem_travar()


class TesteViaDaGarota(BaseNaTela):
    def test_a_via_sai_na_termica_a_cada_comissao_lancada(self):
        saida = self.configurar_termica()
        self.cadastrar(180, "MARIA")
        self.lancar_pela_linha(180, "25,00")
        self.lancar_pela_linha(180, "30,00")
        self.ctx.impressao.fila.processar()
        dados = saida.read_bytes()
        self.assertEqual(dados.count("VIA DA GAROTA".encode("cp850")), 2)           # uma via por lançamento
        self.assertIn("Garota: 180 MARIA".encode("cp850"), dados)
        self.assertIn("TOTAL A RECEBER (2)".encode("cp850"), dados)                 # a segunda já traz o acumulado
        self.assertIn("Via da garota enviada para a impressora.", self.status())
        self.assertNotIn(b"\x1bp", dados)                                           # via não abre a gaveta
        self.sem_travar()

    def test_a_via_traz_o_valor_do_lancamento_e_o_que_ela_tem_a_receber(self):
        saida = self.configurar_termica()
        self.lancar_pela_linha(180, "25,00")
        self.lancar_pela_linha(180, "30,00")
        self.ctx.impressao.fila.processar()
        texto = saida.read_bytes().decode("cp850", "replace")
        segunda = texto.split("COMISS")[2]                                          # o texto da 2ª via
        for trecho in ("Valor desta comiss", "30,00", "25,00", "55,00"):
            self.assertIn(trecho, segunda)

    def test_sem_impressora_a_via_fica_no_historico_e_o_status_avisa(self):
        self.lancar_pela_linha(180, "25,00")                                        # modo tela (padrão dos testes)
        self.assertIn("Sem impressora configurada: a via ficou só no histórico.", self.status())
        arquivos = list(Path(self.pasta_impressao).glob("*via_comissao_180_*.txt"))
        self.assertEqual(len(arquivos), 1)
        self.assertIn("VIA DA GAROTA", arquivos[0].read_text(encoding="utf-8"))
        self.sem_travar()                                                           # e nenhuma janela abriu no caixa

    def test_via_desligada_nao_imprime_nem_comenta(self):
        saida = self.configurar_termica()
        self.banco.cfg_set("imprimir_via_comissao", "N")
        self.lancar_pela_linha(180, "25,00")
        self.ctx.impressao.fila.processar()
        self.assertFalse(saida.exists())
        self.assertNotIn("Via da garota", self.status())
        self.assertEqual(self.com.pendente(180), 2500)

    def test_falha_na_impressora_nao_desfaz_a_comissao_e_avisa(self):
        self.configurar_termica()
        with mock.patch.object(type(self.ctx.impressao), "enviar", side_effect=OSError("sem papel no spooler")):
            self.lancar_pela_linha(180, "25,00")
        self.assertEqual(self.com.pendente(180), 2500)                               # a comissão está gravada
        self.assertIn("ATENÇÃO: a via da garota não foi impressa (sem papel no spooler)", self.status())
        self.sem_travar()

    def test_pela_janela_a_via_tambem_sai(self):
        saida = self.configurar_termica()
        self.banco.cfg_set("comissao_na_linha", "N")

        def lancando(w):
            entradas(w)[1].insert(0, "25,00")
            w.after(10, lambda: clicar(w, "Lançar"))
        self.dialogos({"Comissão da garota": lancando})
        self.posicao("180")
        self.digitar_codigo("50")
        self.ctx.impressao.fila.processar()
        self.assertIn("VIA DA GAROTA".encode("cp850"), saida.read_bytes())


class TestePagarECancelarNaComandaDaGarota(BaseNaTela):
    def test_f12_na_comanda_so_com_comissao_paga_a_garota_tira_do_caixa_e_da_recibo(self):
        self.cadastrar(180, "MARIA")
        self.dar(180, 25); self.dar(180, 30)
        esperado = self.ctx.turnos.resumo(self.turno)["esperado"]
        recibos = []
        self.robo.quando("Visualizador", lambda w: (recibos.append(w.texto), w.destroy()))
        self.dialogos({"Pagar comissão": "Pagar"})
        self.posicao("180")
        self.cx.pagar(); self.cx.update()
        self.assertEqual(self.com.pendente(180), 0)
        m = self.banco.um("SELECT tipo, valor_cent, descricao FROM movimentos_caixa")
        self.assertEqual(tuple(m), ("saida", 5500, "Comissão garota 180 MARIA"))
        self.assertEqual(self.ctx.turnos.resumo(self.turno)["esperado"], esperado - 5500)
        self.assertIn("RECIBO DE COMISSÃO", recibos[0])
        self.assertIn("55,00", recibos[0])
        self.assertIn("Comissão de R$ 55,00 paga à garota 180", self.status())
        self.assertEqual([l[1] for l in self.linhas()], ["COMISSÃO (paga)", "COMISSÃO (paga)"])
        faixa = self.cx.faixa.cget("text")
        self.assertIn("Paga neste turno: R$ 55,00", faixa)
        self.assertNotIn("F12", faixa)                                               # nada mais a pagar
        self.sem_travar()

    def test_f12_desistindo_nao_paga_nada(self):
        self.dar(180, 25)
        self.dialogos({"Pagar comissão": "Cancelar"})
        self.posicao("180")
        self.cx.pagar()
        self.assertEqual(self.com.pendente(180), 2500)
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM movimentos_caixa"), 0)
        self.assertIs(self.cx.focus_lastfor(), self.cx.ent_codigo)
        self.sem_travar()

    def test_f12_pagando_fora_do_caixa_nao_registra_sangria(self):
        self.dar(180, 25)
        self.robo.quando("Visualizador", lambda w: w.destroy())

        def pagar_fora(w):
            [c for c in w.winfo_children()[0].winfo_children() if isinstance(c, ttk.Checkbutton)][0].invoke()
            clicar(w, "Pagar")
        self.dialogos({"Pagar comissão": pagar_fora})
        self.posicao("180")
        self.cx.pagar()
        self.assertEqual(self.com.pendente(180), 0)
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM movimentos_caixa"), 0)
        self.sem_travar()

    def test_f12_pede_senha_de_supervisor_do_operador_so_caixa(self):
        self.dar(180, 25)
        self.ctx.cadastros.salvar("operadores", {"nome": "BAR", "senha": "1", "nivel": "0"})
        self.ctx.operador = self.ctx.acesso.autenticar("BAR", "1")
        pedidas = []

        def senha(w):
            pedidas.append(w.title())
            entradas(w)[0].insert(0, "ADM"); clicar(w, "OK")
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.dialogos({"Autorização": senha, "Pagar comissão": "Pagar"})
        self.posicao("180")
        self.cx.pagar()
        self.assertEqual(pedidas, ["Autorização"])
        self.assertEqual(self.com.pendente(180), 0)
        self.sem_travar()

    def test_f12_com_consumo_e_comissao_pergunta_o_que_pagar_e_paga_a_comissao(self):
        self.dar(180, 25)
        self.posicao("180")
        self.digitar_codigo("1"); self.valor("1")                                    # a SKOL de R$ 8,00 (+ serviço) na mesma comanda
        perguntas = []

        def escolhendo(master, titulo, itens, *args, **kwargs):
            perguntas.append([texto for _, texto in itens])
            return "comissao"
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.dialogos({"Pagar comissão": "Pagar"})
        with mock.patch("src.ui.caixa_ui.tema.escolher", side_effect=escolhendo):
            self.cx.pagar()
        self.assertEqual(perguntas, [["Pagar a comanda (R$ 8,80)", "Pagar a comissão da garota (R$ 25,00)"]])
        self.assertEqual(self.com.pendente(180), 0)
        self.assertEqual(len(self.ctx.caixa.itens(self.cx.venda_id)), 1)             # o consumo continua aberto
        self.assertEqual(self.cx.venda()["status"], "aberta")
        self.sem_travar()

    def test_f12_com_consumo_e_comissao_desistindo_da_pergunta_nao_faz_nada(self):
        self.dar(180, 25)
        self.posicao("180")
        self.digitar_codigo("1"); self.valor("1")
        with mock.patch("src.ui.caixa_ui.tema.escolher", return_value=None):
            self.cx.pagar()
        self.assertEqual(self.com.pendente(180), 2500)
        self.assertEqual(self.cx.venda()["status"], "aberta")
        self.sem_travar()

    def test_f12_com_consumo_e_sem_comissao_pagar_nao_pergunta_nada(self):
        self.posicao("180")
        self.digitar_codigo("1"); self.valor("1")
        with mock.patch("src.ui.caixa_ui.tema.escolher", side_effect=AssertionError("perguntou")), \
                mock.patch("src.ui.caixa_ui.JanelaPagamento") as janela:
            janela.return_value.fechou = False
            self.cx.pagar()
        janela.assert_called_once()                                                  # foi direto para o pagamento do consumo

    def test_f12_sem_nada_a_pagar_segue_avisando_que_falta_item(self):
        avisos = []
        self.dialogos({"Aviso": lambda w: (avisos.append(self.textos(w)), clicar(w, "OK"))})
        self.posicao("180")
        self.cx.pagar()
        self.assertTrue(any("Lance ao menos um item" in t for t in avisos[0]), avisos)

    def test_f12_com_a_opcao_desligada_orienta_a_usar_o_botao_comissoes(self):
        self.banco.cfg_set("comissao_na_linha", "N")
        self.dar(180, 25)
        avisos = []
        self.dialogos({"Aviso": lambda w: (avisos.append(self.textos(w)), clicar(w, "OK"))})
        self.posicao("180")
        self.cx.pagar()
        self.assertTrue(any("botão Comissões" in t for t in avisos[0]), avisos)
        self.assertEqual(self.com.pendente(180), 2500)
        self.assertNotIn("F12", self.cx.faixa.cget("text"))                          # a dica de F12 só existe no modo novo

    # ---------------------------------------------------------------- Delete na linha de comissão
    def test_delete_na_linha_da_comissao_cancela_so_aquele_lancamento(self):
        primeiro = self.dar(180, 25); self.dar(180, 30)
        self.dialogos({"Cancelar comissão": "Sim"})
        self.posicao("180")
        self.cx.grade.selecionar(f"c{primeiro}")
        self.cx.cancelar_item_selecionado(); self.cx.update()
        c = self.banco.um("SELECT status, cancelada_por, motivo_cancelamento FROM comissoes_garotas WHERE id = ?", (primeiro,))
        self.assertEqual((c["status"], c["cancelada_por"], c["motivo_cancelamento"]),
                         ("cancelada", self.ctx.operador_id, "cancelado no caixa"))
        self.assertEqual(self.com.pendente(180), 3000)
        self.assertEqual(self.cx.grade.total(), 1)                                   # a outra continua marcada
        self.assertIn("Comissão cancelada", self.status())
        self.sem_travar()

    def test_delete_pergunta_antes_e_o_nao_preserva_a_comissao(self):
        c = self.dar(180, 25)
        perguntas = []

        def nao(w):
            perguntas.append(self.textos(w)); clicar(w, "Não")
        self.dialogos({"Cancelar comissão": nao})
        self.posicao("180")
        self.cx.grade.selecionar(f"c{c}")
        self.cx.cancelar_item_selecionado()
        self.assertTrue(any("R$ 25,00 da garota 180" in t for t in perguntas[0]), perguntas)
        self.assertEqual(self.com.pendente(180), 2500)

    def test_delete_em_comissao_ja_paga_so_avisa(self):
        c = self.dar(180, 25)
        self.com.pagar(180, self.turno, self.ctx.operador_id, False)
        avisos = []
        self.dialogos({"Aviso": lambda w: (avisos.append(self.textos(w)), clicar(w, "OK")),
                       "Cancelar comissão": lambda w: avisos.append(["PERGUNTOU"])})
        self.posicao("180")
        self.cx.grade.selecionar(f"c{c}")
        self.cx.cancelar_item_selecionado()
        self.assertEqual(len(avisos), 1, avisos)
        self.assertTrue(any("já foi paga" in t for t in avisos[0]), avisos)
        self.assertEqual(self.banco.valor("SELECT status FROM comissoes_garotas WHERE id = ?", (c,)), "paga")

    def test_delete_pede_senha_de_cancelamento_do_operador_so_caixa(self):
        c = self.dar(180, 25)
        self.ctx.cadastros.salvar("operadores", {"nome": "BAR", "senha": "1", "nivel": "0"})
        self.ctx.operador = self.ctx.acesso.autenticar("BAR", "1")
        self.banco.cfg_set("exigir_senha_cancelamento", "S")
        pedidas = []

        def senha(w):
            pedidas.append(w.title())
            entradas(w)[0].insert(0, "ADM"); clicar(w, "OK")
        self.dialogos({"Autorização": senha, "Cancelar comissão": "Sim"})
        self.posicao("180")
        self.cx.grade.selecionar(f"c{c}")
        self.cx.cancelar_item_selecionado()
        self.assertEqual(pedidas, ["Autorização"])
        self.assertEqual(self.com.pendente(180), 0)
        self.sem_travar()

    def test_delete_no_modo_cancelar_nao_pede_a_senha_duas_vezes(self):
        c = self.dar(180, 25)
        self.ctx.cadastros.salvar("operadores", {"nome": "BAR", "senha": "1", "nivel": "0"})
        self.ctx.operador = self.ctx.acesso.autenticar("BAR", "1")
        self.banco.cfg_set("exigir_senha_cancelamento", "S")
        pedidas = []
        self.dialogos({"Autorização": lambda w: pedidas.append(w.title()), "Cancelar comissão": "Sim"})
        self.posicao("180")
        self.cx.modo_cancelar = True                                                 # o operador já se autorizou pelo menu Cancelar
        self.cx.grade.selecionar(f"c{c}")
        self.cx.cancelar_item_selecionado()
        self.assertEqual(pedidas, [])
        self.assertEqual(self.com.pendente(180), 0)
        self.assertFalse(self.cx.modo_cancelar)

    def test_delete_num_item_comum_continua_cancelando_o_item(self):
        self.dar(180, 25)
        self.posicao("180")
        self.digitar_codigo("1"); self.valor("1")
        self.dialogos({"Cancela Item": "Sim"})
        item = self.ctx.caixa.itens(self.cx.venda_id)[0]["id"]
        self.cx.grade.selecionar(item)
        self.cx.cancelar_item_selecionado()
        self.assertEqual(self.ctx.caixa.itens(self.cx.venda_id), [])
        self.assertEqual(self.com.pendente(180), 2500)                               # a comissão não foi tocada
        self.sem_travar()

    def test_observacao_e_transferencia_na_linha_de_comissao_explicam_o_que_fazer(self):
        c = self.dar(180, 25)
        avisos = []
        self.dialogos({"Aviso": lambda w: (avisos.append(self.textos(w)), clicar(w, "OK"))})
        self.posicao("180")
        self.cx.grade.selecionar(f"c{c}")
        self.cx.observacao_item()
        self.cx.transferir_item()
        self.assertEqual(len(avisos), 2)
        self.assertTrue(all(any("F12" in t and "Delete" in t for t in a) for a in avisos), avisos)


class TesteGarotasNoRodape(BaseNaTela):
    def test_garota_com_comissao_a_pagar_vira_icone_depois_do_balcao(self):
        self.dar(180, 25); self.dar(180, 30); self.dar(156, 40)
        tiles = self.tiles()
        self.assertEqual([k for k in tiles][:1], ["0"])                              # o balcão continua primeiro
        self.assertEqual((tiles["180"]["tipo"], tiles["180"]["total"], tiles["180"]["estado"]), ("garota", "55,00", "garota"))
        self.assertEqual((tiles["156"]["tipo"], tiles["156"]["total"]), ("garota", "40,00"))

    def test_lancar_pela_linha_ja_mostra_o_icone_sem_sair_da_tela(self):
        self.lancar_pela_linha(180, "25,00")
        self.assertEqual(self.tiles()["180"]["total"], "25,00")
        self.posicao("0")                                                            # sai da comanda vazia dela: ela some, o ícone fica
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM vendas"), 0)
        self.assertEqual(self.tiles()["180"]["tipo"], "garota")

    def test_clicar_no_icone_abre_a_comanda_da_garota_com_as_comissoes(self):
        self.dar(180, 25)
        self.cx._tile_escolhido("180")
        self.cx.update()
        v = self.cx.venda()
        self.assertEqual((v["modalidade"], v["comanda"], v["posicao"]), ("mesa", 1, 180))
        self.assertEqual(self.cx.grade.total(), 1)
        self.assertIn("COMISSÃO MARCADA NA COMANDA 180", self.cx.faixa.cget("text"))
        self.assertIn("F12 paga a garota", self.cx.faixa.cget("text"))

    def test_garota_que_tambem_consome_ganha_o_selo_na_propria_comanda(self):
        self.posicao("180")
        self.digitar_codigo("1"); self.valor("1")                                    # um item na comanda 180
        self.dar(180, 25)
        self.cx.recarregar()
        tiles = self.tiles()
        self.assertEqual([t["tipo"] for t in tiles.values()].count("garota"), 0)     # um ícone só, o da comanda
        self.assertEqual((tiles["180"]["tipo"], tiles["180"]["garota"]), ("comanda", "25,00"))

    def test_pagando_a_comissao_o_icone_some(self):
        self.dar(180, 25)
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.dialogos({"Pagar comissão": "Pagar"})
        self.posicao("180")
        self.cx.pagar()
        self.cx.update()
        self.assertNotIn("garota", [t["tipo"] for t in self.tiles().values()])
        self.sem_travar()

    def test_cancelando_a_comissao_o_icone_some(self):
        c = self.dar(180, 25)
        self.dialogos({"Cancelar comissão": "Sim"})
        self.posicao("180")
        self.cx.grade.selecionar(f"c{c}")
        self.cx.cancelar_item_selecionado()
        self.assertNotIn("garota", [t["tipo"] for t in self.tiles().values()])
        self.assertEqual(self.com.pendente(180), 0)
        self.sem_travar()

    def test_desligado_nas_configuracoes_nao_mostra_as_garotas(self):
        self.banco.cfg_set("painel_mostra_garotas", "N")
        self.dar(180, 25)
        self.assertNotIn("180", self.tiles())

    def test_t_no_icone_da_garota_nao_transfere_nada_para_ela(self):
        from types import SimpleNamespace
        self.dar(180, 25)
        v, _ = self.ctx.caixa.abrir_mesa(12, comanda=True)
        self.ctx.caixa.adicionar_item(v, self.agua, 1)
        self.tiles()
        chamadas = []
        painel = self.cx.painel_mesas
        painel._ao_transferir = chamadas.append
        painel.focar("180")                                                          # o ícone da garota
        painel._tecla(SimpleNamespace(keysym="t", char="t"))
        self.assertEqual(chamadas, [])
        painel.focar("12")                                                           # uma comanda comum continua transferindo
        painel._tecla(SimpleNamespace(keysym="T", char="T"))
        self.assertEqual(chamadas, ["12"])


class TesteModeloDosIconesDasGarotas(unittest.TestCase):
    MESAS = [{"rotulo": "12", "comanda": 1, "status": "aberta", "inativa": 0, "total_cent": 880, "minutos_parada": 1, "n_itens": 1},
             {"rotulo": "180", "comanda": 1, "status": "aberta", "inativa": 0, "total_cent": 350, "minutos_parada": 2, "n_itens": 1}]

    def test_sem_garotas_o_modelo_e_o_de_sempre(self):
        antes = montar_tiles(self.MESAS, None)
        self.assertEqual(montar_tiles(self.MESAS, None, ()), antes)
        self.assertTrue(all("garota" not in t for t in antes))

    def test_garota_sem_consumo_aberto_ganha_icone_proprio_no_fim(self):
        tiles = montar_tiles(self.MESAS, None, [{"rotulo": "156", "total_cent": 4000}])
        self.assertEqual([t["chave"] for t in tiles], ["0", "12", "180", "156"])
        self.assertEqual(tiles[-1], {"chave": "156", "rotulo": "156", "tipo": "garota", "estado": "garota",
                                     "total": "40,00", "minutos": 0})

    def test_garota_com_consumo_aberto_vira_selo_e_nao_duplica_a_chave(self):
        tiles = montar_tiles(self.MESAS, None, [{"rotulo": "180", "total_cent": 5500}])
        self.assertEqual([t["chave"] for t in tiles], ["0", "12", "180"])
        self.assertEqual((tiles[2]["tipo"], tiles[2]["total"], tiles[2]["garota"]), ("comanda", "3,50", "55,00"))
        self.assertNotIn("garota", tiles[1])

    def test_comanda_da_garota_aberta_mas_vazia_mostra_o_icone_da_garota(self):
        mesas = [{"rotulo": "180", "comanda": 1, "status": "aberta", "inativa": 1, "total_cent": 0, "minutos_parada": 45, "n_itens": 0}]
        tiles = montar_tiles(mesas, None, [{"rotulo": "180", "total_cent": 5500}])
        self.assertEqual(tiles[1], {"chave": "180", "rotulo": "180", "tipo": "garota", "estado": "garota",
                                    "total": "55,00", "minutos": 0})                 # sem relógio de mesa parada

    def test_mesa_com_o_mesmo_numero_nao_recebe_o_selo(self):
        mesas = [{"rotulo": "M5", "comanda": 0, "status": "aberta", "inativa": 0, "total_cent": 100, "minutos_parada": 0, "n_itens": 1}]
        tiles = montar_tiles(mesas, None, [{"rotulo": "M5", "total_cent": 500}])
        self.assertEqual([t["tipo"] for t in tiles], ["balcao", "mesa", "garota"])


if __name__ == "__main__":
    unittest.main()


class TesteComissaoEmPontosNaTela(BaseNaTela):
    def setUp(self):
        super().setUp()
        self.banco.cfg_set("comissao_em_pontos", "S")

    def test_0_3_na_linha_do_caixa_vira_15_reais(self):
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.posicao("180")
        self.digitar_codigo("50")
        self.assertEqual(self.cx.lbl_qtd_titulo.cget("text"), "Pontos (0,1 = R$ 5,00)")
        self.valor("0,3")
        self.assertEqual(self.banco.valor("SELECT valor_cent FROM comissoes_garotas"), 1500)
        self.sem_travar()

    def test_fracao_invalida_avisa_e_nao_grava(self):
        self.posicao("180")
        self.digitar_codigo("50")
        self.valor("0,15")
        self.assertIn("0,1 em 0,1", self.status())
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM comissoes_garotas"), 0)
        self.sem_travar()
