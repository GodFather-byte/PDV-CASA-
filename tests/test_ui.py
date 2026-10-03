"""Testes de interface Tkinter: abrem as telas com dados reais e conduzem os fluxos do caixa.
Pulados automaticamente se não houver ambiente gráfico."""
from __future__ import annotations

import tempfile
import tkinter as tk
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from tkinter import ttk
from unittest import mock

from src.controllers.cadastro_controller import CadastroController
from src.controllers.entidades import ENTIDADES
from src.core import formatacao as fmt
from src.database.conexao import BancoDados
from src.ui import tema
from src.ui.contexto import Contexto
from tests.ui_robo import Robo, clicar, entradas


def _tk_disponivel() -> bool:
    try:
        r = tk.Tk()
        r.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_disponivel(), "sem ambiente gráfico")
class BaseUI(unittest.TestCase):
    def setUp(self):
        fmt.definir_relogio(None)
        self.banco = BancoDados(":memory:")
        self.ctx = Contexto(self.banco)
        self.ctx.operador = self.ctx.acesso.autenticar("adm", "adm")
        cad = CadastroController(self.banco)
        sub = self.banco.valor("SELECT id FROM subgrupos")
        un = self.banco.valor("SELECT id FROM unidades WHERE abreviatura = 'UN'")
        self.skol = cad.salvar("produtos", {"codigo": "1", "nome": "SKOL", "subgrupo_id": sub, "unidade_id": un,
                                            "preco_cent": "8,00", "controla_estoque": "S"})
        self.agua = cad.salvar("produtos", {"codigo": "2", "nome": "AGUA", "subgrupo_id": sub, "unidade_id": un, "preco_cent": "3,50"})
        self.banco.executar("UPDATE produtos SET qt_atual = 50, estoque_minimo = 10 WHERE id = ?", (self.skol,))
        self.cliente = cad.salvar("clientes", {"numero_consulta": "7", "nome": "WESLEY", "limite_cent": "100,00"})
        self.root = tk.Tk()
        self.root.withdraw()
        tema.aplicar_tema(self.root)
        self.robo = Robo(self.root)
        self.addCleanup(self._fechar)

    def _fechar(self):
        self.robo.parar()
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self.banco.fechar()

    def sem_travar(self):
        self.assertFalse([l for l in self.robo.log if l.startswith("TRAVADO") or l.startswith("TclError")], self.robo.log)

    def abrir_turno(self):
        return self.ctx.turnos.abrir(self.ctx.operador_id, 1, 10000)


class TesteTelasAbrem(BaseUI):
    def test_todos_os_cadastros_abrem_com_dados(self):
        from src.ui.cadastros_tk import JanelaCadastro
        for chave in ENTIDADES:
            with self.subTest(chave=chave):
                j = JanelaCadastro(self.root, self.ctx, chave)
                j.update()
                esperado = len(self.ctx.cadastros.listar(chave))
                self.assertEqual(j.grade.total(), esperado)
                j.ordenar(); j.update()
                j.destroy()

    def test_gravar_produto_pelo_formulario_e_validacao(self):
        from src.ui.cadastros_tk import JanelaCadastro
        j = JanelaCadastro(self.root, self.ctx, "produtos")
        j.update()
        j.incluir()
        j.campos["nome"].var.set("HEINEKEN")
        j.campos["subgrupo_id"].var.set("DIVERSOS - DIVERSOS")
        j.campos["unidade_id"].var.set("Unidade")
        j.campos["preco_cent"].var.set("12,90")
        j.campos["controla_estoque"].bool.set(True)
        j.gravar(); j.update()
        p = self.banco.um("SELECT * FROM produtos WHERE nome = 'HEINEKEN'")
        self.assertEqual((p["preco_cent"], p["controla_estoque"], p["codigo"]), (1290, 1, "0000000000003"))
        # nome repetido: mostra o erro e não grava
        self.robo.quando("Dialogo", lambda w: w.destroy())
        j.incluir()
        j.campos["nome"].var.set("HEINEKEN")
        j.campos["subgrupo_id"].var.set("DIVERSOS - DIVERSOS"); j.campos["unidade_id"].var.set("Unidade")
        j.gravar(); j.update()
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM produtos WHERE nome = 'HEINEKEN'"), 1)
        self.sem_travar()
        j.destroy()

    def test_pesquisar_e_excluir(self):
        from src.ui.cadastros_tk import JanelaCadastro
        j = JanelaCadastro(self.root, self.ctx, "produtos")
        j.update()
        j.texto_busca = "agua"; j.carregar(); j.update()
        self.assertEqual(j.grade.total(), 1)
        self.robo.quando("Dialogo", lambda w: clicar(w, "Sim"))
        j.excluir(); j.update()
        self.assertIsNone(self.banco.um("SELECT 1 FROM produtos WHERE nome = 'AGUA'"))
        self.sem_travar()
        j.destroy()

    def test_todos_os_relatorios_abrem(self):
        from src.ui.relatorios_ui import SPECS, abrir_relatorio
        self.abrir_turno()
        for chave in [*SPECS, "vendas_periodo", "estoque_atual"]:
            with self.subTest(chave=chave):
                j = abrir_relatorio(self.root, self.ctx, chave)
                j.update()
                j.destroy()
        self.sem_travar()

    def test_lancamentos_e_configuracoes_abrem(self):
        from src.ui import config_ui
        from src.ui.lancamentos_ui import JanelaContas, JanelaEstoque
        for classe in (JanelaContas, JanelaEstoque):
            j = classe(self.root, self.ctx); j.update(); j.destroy()
        for chave in ("acessos", "loja", "configuracoes", "maquinas"):
            with self.subTest(chave=chave):
                j = config_ui.abrir(self.root, self.ctx, chave); j.update()
                if chave != "acessos":
                    self.robo.quando("Dialogo", lambda w: w.destroy())
                    j.gravar(); j.update()
                j.destroy()
        self.sem_travar()

    def test_configuracao_gravada_pela_tela(self):
        from src.ui import config_ui
        j = config_ui.abrir(self.root, self.ctx, "configuracoes")
        j.vars["servico_pct"].set("12,5")
        j.vars["num_mesas"].set("20")
        self.robo.quando("Dialogo", lambda w: w.destroy())
        j.gravar(); j.update(); j.destroy()
        self.assertEqual((float(self.banco.cfg("servico_pct")), self.banco.cfg_int("num_mesas")), (12.5, 20))

    def test_acessos_alteram_nivel_do_modulo(self):
        from src.ui import config_ui
        j = config_ui.abrir(self.root, self.ctx, "acessos"); j.update()
        j.grade.selecionar("cad_produtos"); j.update()
        j.v_nivel.set("4"); j.gravar(); j.update(); j.destroy()
        self.assertEqual(self.ctx.acesso.nivel_modulo("cad_produtos"), 4)


class TesteMenu(BaseUI):
    def test_menu_mostra_somente_o_que_o_nivel_permite(self):
        from src.ui.app import App
        app = App(self.banco)
        self.addCleanup(app.root.destroy)
        app.ctx.operador = app.ctx.acesso.autenticar("adm", "adm")
        app.mostrar_menu(); app.root.update()
        self.assertEqual(set(app.botoes), {"Cadastros", "Caixa", "Lançamentos", "Relatórios", "Utilitários", "Configurações", "Saída"})
        # operador de nível 1: sem Configurações nem Utilitários
        self.ctx.cadastros.salvar("operadores", {"nome": "Ana", "senha": "1", "nivel": "1"})
        app.ctx.operador = app.ctx.acesso.autenticar("ana", "1")
        app.mostrar_menu(); app.root.update()
        self.assertNotIn("Configurações", app.botoes)
        self.assertNotIn("Utilitários", app.botoes)
        self.assertIn("Caixa", app.botoes)
        self.assertEqual(app.valores["estoque_total"].cget("text"), "1")    # painel do dia
        self.assertIn("Não há backup", app.lbl_backup.cget("text"))

    def test_login_valida_senha_e_ignora_caixa_alta(self):
        from src.ui.login import JanelaLogin
        j = JanelaLogin(self.root, self.ctx, "Loja")
        j.var_usuario.set("adm"); j.var_senha.set("errada"); j.entrar()
        self.assertIsNone(j.operador)
        self.assertEqual(j.lbl_msg.cget("text"), "Senha Incorreta")
        j.var_senha.set("AdM"); j.entrar()
        self.assertEqual(j.operador.nome, "ADM")


class TesteFluxosCaixa(BaseUI):
    def setUp(self):
        super().setUp()
        self.abrir_turno()
        from src.ui.caixa_ui import JanelaCaixa
        self.cx = JanelaCaixa(self.root, self.ctx)
        self.cx.update()

    def lancar(self, cod, qtd):
        self.cx.var_cod.set(cod); self.cx._enter_codigo(); self.cx.update()
        self.cx.var_qtd.set(str(qtd)); self.cx.confirmar_item(); self.cx.update()

    def pagar(self, forma, valor=None, desconto_pct=None):
        def acao(j):
            if desconto_pct:
                j.var_pct.set(str(desconto_pct)); j._aplicar_desconto()
            f = [i for i in j.grade_formas.tree.get_children() if j.grade_formas.valores(i)[0] == forma][0]
            j.grade_formas.selecionar(f); j._forma_escolhida()
            if valor:
                j.var_valor.set(valor)
            j._lancar_valor()
            j.after(10, j.fechar_venda)
        self.robo.quando("JanelaPagamento", acao)
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.cx.pagar(); self.cx.update()

    def test_venda_de_balcao_com_troco_baixa_estoque(self):
        self.lancar("1", 2)
        self.assertEqual(self.cx.lbl_total.cget("text"), "16,00")
        self.pagar("Dinheiro", "20,00")
        v = self.banco.um("SELECT * FROM vendas")
        self.assertEqual((v["cupom"], v["status"], v["troco_cent"]), (1, "fechada", 400))
        self.assertEqual(self.banco.valor("SELECT qt_atual FROM produtos WHERE id = ?", (self.skol,)), 48)
        self.assertEqual(self.cx.lbl_troco.cget("text"), "4,00")
        self.sem_travar()

    def test_busca_por_nome_e_produto_inexistente(self):
        self.cx.var_cod.set("zzz"); self.cx._enter_codigo(); self.cx.update()
        self.assertIsNone(self.cx.produto)
        self.assertIn("não encontrado", self.cx.status.cget("text"))
        self.cx.var_cod.set("sko"); self.cx._enter_codigo(); self.cx.update()    # único achado: usa direto
        self.assertEqual(self.cx.produto["nome"], "SKOL")

    def test_leitor_optico_lanca_direto_com_quantidade_1(self):
        self.cx.alternar_leitor()
        self.cx.var_cod.set("1"); self.cx._enter_codigo(); self.cx.update()
        self.cx.var_cod.set("1"); self.cx._enter_codigo(); self.cx.update()
        self.assertEqual(self.cx.grade.total(), 2)
        self.assertEqual(self.cx.lbl_total.cget("text"), "16,00")

    def test_mesa_servico_pre_conta_e_pagamento(self):
        self.cx.var_pos.set("5"); self.cx.chamar_mesa(); self.cx.update()
        self.lancar("1", 5)
        self.assertEqual(self.cx.lbl_total.cget("text"), "44,00")           # 40,00 + 10%
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.cx.pre_conta(); self.cx.update()
        self.assertEqual(self.banco.valor("SELECT status FROM vendas WHERE posicao = 5"), "conta_enviada")
        self.cx.var_pos.set("5"); self.cx.chamar_mesa(); self.cx.update()
        self.pagar("Pix")
        self.assertEqual(self.banco.valor("SELECT status FROM vendas WHERE posicao = 5"), "fechada")
        self.assertEqual(self.banco.valor("SELECT servico_cent FROM vendas WHERE posicao = 5"), 400)
        self.sem_travar()

    def test_mesa_vazia_nao_deixa_fantasma(self):
        self.cx.var_pos.set("9"); self.cx.chamar_mesa(); self.cx.update()
        self.cx.var_pos.set("0"); self.cx.chamar_mesa(); self.cx.update()
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM vendas"), 0)

    def tiles(self):
        return [(t["chave"], t["estado"], t["total"]) for t in self.cx.painel_mesas.tiles()]

    def itens_do_icone(self, chave, marca):
        return self.cx.painel_mesas.canvas.find_withtag(f"t:{chave}&&{marca}")

    def clicar_no_icone(self, chave):
        c = self.cx.painel_mesas.canvas
        self.cx.update()
        x1, y1, x2, y2 = c.bbox(f"t:{chave}&&fundo")
        x, y = (x1 + x2) // 2, (y1 + y2) // 2
        c.event_generate("<Motion>", x=x, y=y)         # o Tk só sabe qual é o item sob o mouse depois de um movimento
        c.event_generate("<Button-1>", x=x, y=y)
        self.cx.update()

    def foco(self):
        return str(self.cx.focus_lastfor())

    def test_skol_na_comanda_2_aparece_como_icone_no_rodape(self):
        self.assertTrue(self.cx.mesas_visiveis)                       # os ícones ficam à vista, sem apertar Esc
        self.assertEqual(self.tiles(), [("0", "balcao", "")])         # só o balcão
        self.cx.var_cod.set("C2"); self.cx._enter_codigo(); self.cx.update()   # "C2" no código abre a comanda 2
        self.assertEqual(self.cx.lbl_situacao.cget("text"), "Comanda 2")
        self.assertEqual(self.cx.var_pos.get(), "C2")
        self.lancar("1", 1)
        self.assertEqual(self.cx.lbl_total.cget("text"), "8,80")      # 8,00 + 10% de serviço, como na mesa
        self.assertEqual(self.tiles(), [("0", "balcao", ""), ("C2", "consumindo", "8,80")])
        self.assertTrue(self.itens_do_icone("C2", "icone:comanda"))
        fundo = self.itens_do_icone("C2", "fundo")[0]
        self.assertEqual(float(self.cx.painel_mesas.canvas.itemcget(fundo, "width")), 3.0)   # a que está na tela: borda grossa
        v = self.banco.um("SELECT modalidade, comanda, posicao FROM vendas")
        self.assertEqual((v["modalidade"], v["comanda"], v["posicao"]), ("mesa", 1, 2))
        self.sem_travar()

    def test_mesa_2_e_comanda_2_sao_icones_diferentes_e_o_clique_troca(self):
        self.cx.var_pos.set("2"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("1", 1)
        self.cx.var_pos.set("c2"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("2", 2)
        self.assertEqual([t[0] for t in self.tiles()], ["0", "2", "C2"])      # balcão, mesas e depois comandas
        self.assertTrue(self.itens_do_icone("2", "icone:mesa"))
        self.assertTrue(self.itens_do_icone("C2", "icone:comanda"))
        self.clicar_no_icone("2")
        self.assertEqual((self.cx.lbl_situacao.cget("text"), self.cx.lbl_total.cget("text")), ("Mesa 2", "8,80"))
        self.clicar_no_icone("0")
        self.assertEqual(self.cx.lbl_situacao.cget("text"), "Balcão")
        self.clicar_no_icone("C2")
        self.assertEqual((self.cx.lbl_situacao.cget("text"), self.cx.lbl_total.cget("text")), ("Comanda 2", "7,70"))
        self.sem_travar()

    def test_esc_volta_ao_marcar_comanda_e_o_segundo_esc_ao_balcao(self):
        self.cx.var_pos.set("C2"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("1", 1)
        self.cx.ent_codigo.focus_set()
        self.cx._esc_codigo(); self.cx.update()                       # Esc no lançamento de itens
        self.assertEqual(self.foco(), str(self.cx.ent_pos))
        self.assertTrue(self.cx.ent_pos.selection_present())          # o número fica selecionado: é só digitar o próximo
        self.assertEqual(self.cx.var_pos.get(), "C2")
        self.assertTrue(self.cx.mesas_visiveis)
        self.cx._esc_posicao(); self.cx.update()                      # segundo Esc: balcão; a comanda continua gravada
        self.assertEqual(self.cx.lbl_situacao.cget("text"), "Balcão")
        self.assertEqual(self.banco.valor("SELECT status FROM vendas WHERE comanda = 1"), "aberta")
        self.assertIn(("C2", "consumindo", "8,80"), self.tiles())
        self.assertEqual(self.foco(), str(self.cx.ent_codigo))
        self.cx._esc_posicao(); self.cx.update()                      # já no balcão: só devolve o foco ao código
        self.assertEqual(self.foco(), str(self.cx.ent_codigo))
        self.sem_travar()

    def test_esc_com_produto_pendente_so_cancela_o_produto(self):
        self.cx.var_pos.set("C2"); self.cx.chamar_mesa(); self.cx.update()
        self.cx.var_cod.set("1"); self.cx._enter_codigo(); self.cx.update()      # produto escolhido, falta a quantidade
        self.assertIsNotNone(self.cx.produto)
        self.cx._esc_codigo(); self.cx.update()
        self.assertIsNone(self.cx.produto)
        self.assertEqual(self.foco(), str(self.cx.ent_codigo))
        self.assertEqual(self.cx.lbl_situacao.cget("text"), "Comanda 2")           # continua na comanda
        self.cx._esc_codigo(); self.cx.update()                                   # o próximo Esc marca a comanda
        self.assertEqual(self.foco(), str(self.cx.ent_pos))

    def test_comanda_vazia_deixada_com_esc_nao_vira_icone_fantasma(self):
        self.cx.var_pos.set("C4"); self.cx.chamar_mesa(); self.cx.update()
        self.assertEqual(self.tiles(), [("0", "balcao", ""), ("C4", "consumindo", "0,00")])   # recém-aberta já aparece
        self.cx._esc_codigo(); self.cx._esc_posicao(); self.cx.update()
        self.assertEqual(self.tiles(), [("0", "balcao", "")])

    def test_icones_mostram_conta_enviada_e_comanda_parada(self):
        from datetime import timedelta
        self.cx.var_pos.set("C2"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("1", 2)
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.cx.pre_conta(); self.cx.update()                                      # conta enviada
        self.cx.var_pos.set("C3"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("2", 1)
        self.assertEqual(self.tiles(), [("0", "balcao", ""), ("C2", "conta", "17,60"), ("C3", "consumindo", "3,85")])
        self.assertTrue(self.itens_do_icone("C2", "icone:conta"))
        self.assertFalse(self.itens_do_icone("C3", "relogio"))
        self.addCleanup(fmt.definir_relogio, None)
        fmt.definir_relogio(lambda: datetime.now() + timedelta(minutes=45))        # passam 45 min sem lançar nada
        self.cx._atualizar_painel(); self.cx.update()
        self.assertEqual(self.tiles()[2], ("C3", "parada", "3,85"))
        self.assertTrue(self.itens_do_icone("C3", "relogio"))
        self.assertFalse(self.itens_do_icone("C2", "relogio"))      # conta enviada não é "parada": o cliente está pagando
        self.sem_travar()

    def test_muitos_icones_quebram_em_linhas_e_rolam(self):
        from src.ui.painel_mesas import ALTURA, MARGEM
        for n in range(1, 61):
            v, _ = self.ctx.caixa.abrir_mesa(n, comanda=True)
            self.ctx.caixa.adicionar_item(v, self.skol, 1)
        self.cx.carregar_mesas(); self.cx.update()
        p = self.cx.painel_mesas
        self.assertEqual(len(p.tiles()), 61)                          # 60 comandas e o balcão
        self.assertEqual(int(p.canvas.cget("height")), 2 * ALTURA + MARGEM)      # só duas linhas à vista
        self.assertEqual(p.barra.winfo_manager(), "place")            # e a barra de rolagem aparece
        p.focar("C1")
        p._tecla(SimpleNamespace(keysym="End", char=""))
        self.assertEqual(p.cursor(), "C60")
        p._tecla(SimpleNamespace(keysym="Home", char=""))
        self.assertEqual(p.cursor(), "0")
        p._tecla(SimpleNamespace(keysym="Up", char=""))               # no alto da faixa: volta ao campo da posição
        self.assertEqual(self.foco(), str(self.cx.ent_pos))
        self.sem_travar()

    def test_teclado_nos_icones_escolhe_digita_e_transfere(self):
        p = self.cx.painel_mesas
        self.cx.var_pos.set("3"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("1", 1)
        self.cx.var_pos.set("C2"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("2", 1)
        self.cx.var_pos.set("C9"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("1", 2)
        p.focar("3")
        p._tecla(SimpleNamespace(keysym="Return", char="\r"))         # Enter chama a escolhida
        self.assertEqual(self.cx.lbl_situacao.cget("text"), "Mesa 3")
        p.focar("0")
        p._tecla(SimpleNamespace(keysym="c", char="c"))               # digitar C já começa a marcar a posição
        self.assertEqual((self.cx.var_pos.get(), self.foco()), ("C", str(self.cx.ent_pos)))
        self.cx.var_pos.set("C9"); self.cx.chamar_mesa(); self.cx.update()

        def digita(w):
            entradas(w)[0].insert(0, "3, C2"); clicar(w, "OK")
        self.robo.quando("Dialogo", digita)
        p.focar("C9")
        p._tecla(SimpleNamespace(keysym="t", char="t")); self.cx.update()      # T: as outras vêm para a escolhida
        self.assertEqual(self.tiles(), [("0", "balcao", ""), ("C9", "consumindo", "30,25")])
        self.assertEqual(self.cx.lbl_total.cget("text"), "30,25")     # 16,00 + 8,00 + 3,50 + 10%
        self.sem_travar()

    def test_comanda_desligada_avisa_e_nao_abre(self):
        self.banco.cfg_set("num_comandas", 0)
        self.robo.quando("Dialogo", lambda w: w.destroy())
        self.cx.var_cod.set("C2"); self.cx._enter_codigo(); self.cx.update()
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM vendas"), 0)
        self.assertIsNone(self.cx.venda_id)
        self.assertIn("Dialogo", self.robo.log)
        self.sem_travar()

    def test_produto_com_atalho_c2_vence_a_comanda(self):
        self.banco.executar("UPDATE produtos SET atalho = 'C2' WHERE id = ?", (self.agua,))
        self.cx.var_cod.set("C2"); self.cx._enter_codigo(); self.cx.update()
        self.assertEqual(self.cx.produto["nome"], "AGUA")
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM vendas"), 0)

    def test_pre_conta_e_pagamento_da_comanda(self):
        self.cx.var_pos.set("C2"); self.cx.chamar_mesa(); self.cx.update()
        self.lancar("1", 2)
        textos = []
        self.robo.quando("Visualizador", lambda w: (textos.append(w.texto), w.destroy()))
        self.cx.pre_conta(); self.cx.update()
        self.assertIn("CONTA DA COMANDA", textos[0])
        self.assertEqual(self.banco.valor("SELECT status FROM vendas"), "conta_enviada")
        self.assertEqual(self.tiles(), [("0", "balcao", ""), ("C2", "conta", "17,60")])
        self.cx.var_pos.set("C2"); self.cx.chamar_mesa(); self.cx.update()
        self.pagar("Pix")
        v = self.banco.um("SELECT status, comanda, servico_cent FROM vendas")
        self.assertEqual((v["status"], v["comanda"], v["servico_cent"]), ("fechada", 1, 160))
        self.assertEqual(self.tiles(), [("0", "balcao", "")])
        self.sem_travar()

    def test_transferir_comanda_para_mesa_com_f10(self):
        self.cx.var_pos.set("C2"); self.cx.chamar_mesa(); self.cx.update(); self.lancar("1", 1)

        def digita(w):
            entradas(w)[0].insert(0, "7"); clicar(w, "OK")
        self.robo.quando("Dialogo", digita)
        self.cx.transferir_mesa(); self.cx.update()
        v = self.banco.um("SELECT comanda, posicao FROM vendas")
        self.assertEqual((v["comanda"], v["posicao"]), (0, 7))
        self.assertEqual((self.cx.lbl_situacao.cget("text"), self.cx.var_pos.get()), ("Mesa 7", "7"))
        self.assertEqual(self.tiles(), [("0", "balcao", ""), ("7", "consumindo", "8,80")])
        self.sem_travar()

    def test_posicao_invalida_e_avisada(self):
        self.robo.quando("Dialogo", lambda w: w.destroy())
        self.cx.var_pos.set("abc"); self.cx.chamar_mesa(); self.cx.update()
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM vendas"), 0)
        self.assertIn("Dialogo", self.robo.log)
        self.sem_travar()

    def test_painel_so_aparece_no_esc_quando_nao_e_fixo(self):
        self.cx.destroy()
        self.banco.cfg_set("painel_mesas_fixo", "N")
        from src.ui.caixa_ui import JanelaCaixa
        self.cx = JanelaCaixa(self.root, self.ctx)
        self.cx.update()
        self.assertFalse(self.cx.mesas_visiveis)
        self.assertEqual(self.cx.painel_mesas.winfo_manager(), "")    # fora da tela até o Esc
        self.cx._esc_codigo(); self.cx.update()
        self.assertTrue(self.cx.mesas_visiveis)
        self.assertEqual(self.cx.painel_mesas.winfo_manager(), "pack")
        self.assertEqual(self.foco(), str(self.cx.ent_pos))
        self.cx.var_pos.set("C5"); self.cx.chamar_mesa(); self.cx.update()    # abriu a comanda: o painel some de novo
        self.assertFalse(self.cx.mesas_visiveis)
        self.assertEqual(self.foco(), str(self.cx.ent_codigo))
        self.sem_travar()

    def test_cancelar_item_e_conta_inteira(self):
        self.lancar("1", 1); self.lancar("2", 1)
        self.cx._foco_grade(ultimo=True); self.cx.modo_cancelar = True
        self.robo.quando("Dialogo", lambda w: clicar(w, "Sim"))
        self.cx.cancelar_item_selecionado(); self.cx.update()
        self.assertEqual((self.cx.grade.total(), self.cx.lbl_total.cget("text")), (1, "8,00"))
        self.robo.quando("Dialogo", lambda w: clicar(w, "Sim"))
        self.cx.cancelar_conta(); self.cx.update()
        self.assertIsNone(self.cx.venda_id)
        self.assertEqual(self.banco.valor("SELECT status FROM vendas"), "cancelada")
        self.sem_travar()

    def test_operador_sem_nivel_precisa_de_senha_de_supervisor(self):
        self.ctx.cadastros.salvar("operadores", {"nome": "Caixa1", "senha": "9", "nivel": "0"})
        self.ctx.operador = self.ctx.acesso.autenticar("caixa1", "9")
        self.lancar("1", 1)
        self.cx._foco_grade(ultimo=True)
        senhas = iter(["errada", "ADM"])

        def digita(w):
            entradas(w)[0].insert(0, next(senhas)); clicar(w, "OK")
        self.robo.quando("Dialogo", digita, vezes=1)
        self.robo.quando("Dialogo", lambda w: w.destroy(), vezes=1)       # aviso de senha inválida
        self.robo.quando("Dialogo", digita, vezes=1)
        self.robo.quando("Dialogo", lambda w: clicar(w, "Sim"), vezes=1)
        self.cx.cancelar_item_selecionado(); self.cx.update()
        self.assertEqual(self.cx.grade.total(), 0)

    def test_caderneta_debita_saldo_do_cliente(self):
        self.cx.venda_id = self.ctx.caixa.abrir_caderneta(self.cliente); self.cx.recarregar(); self.cx.update()
        self.assertIn("CADERNETA", self.cx.faixa.cget("text"))
        self.lancar("1", 3)
        self.robo.quando("Dialogo", lambda w: clicar(w, "Sim"))
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.cx.pagar(); self.cx.update()
        self.assertEqual(self.banco.valor("SELECT saldo_cent FROM clientes WHERE id = ?", (self.cliente,)), -2400)
        self.sem_travar()

    def test_entrega_pedido_e_recebimento(self):
        self.cx.venda_id = self.ctx.entregas.abrir(self.cliente); self.cx.recarregar(); self.cx.update()
        self.assertIn("ENTREGA", self.cx.faixa.cget("text"))
        self.lancar("1", 2)
        self.ctx.entregas.definir_dados(self.cx.venda_id, 5000)
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.cx.pre_conta(); self.cx.update()                      # F8 na entrega: emite o pedido
        self.assertEqual(self.banco.valor("SELECT status FROM vendas WHERE modalidade = 'entrega'"), "conta_enviada")
        self.assertEqual(len(self.ctx.entregas.pendentes()), 1)
        self.cx.venda_id = self.ctx.entregas.pendentes()[0]["id"]
        self.cx.recarregar(); self.pagar("Dinheiro", "50,00")
        v = self.banco.um("SELECT status, troco_cent FROM vendas WHERE modalidade = 'entrega'")
        self.assertEqual((v["status"], v["troco_cent"]), ("fechada", 3400))
        self.sem_travar()

    def test_sangria_repique_e_troca_de_turno(self):
        self.lancar("1", 1)
        self.pagar("Dinheiro", "8,00")
        def sangria(w):
            ents = entradas(w)
            ents[0].insert(0, "20,00"); ents[1].insert(0, "gelo"); clicar(w, "Gravar")
        self.robo.quando("Dialogo", sangria)
        self.robo.quando("Visualizador", lambda w: w.destroy())
        self.cx.sangria(); self.cx.update()
        self.assertEqual(self.banco.valor("SELECT valor_cent FROM movimentos_caixa WHERE tipo = 'saida'"), 2000)
        res = self.ctx.turnos.resumo(self.ctx.turnos.atual()["id"])
        self.assertEqual(res["esperado"], 10000 + 800 - 2000)

        def trocar(w):
            campos = entradas(w)
            if campos:                           # 1º diálogo: valor encontrado na gaveta
                campos[0].delete(0, "end"); campos[0].insert(0, "88,00"); clicar(w, "OK")
            else:                                # 2º diálogo: "Confirma?"
                clicar(w, "Sim")
        self.robo.quando("Dialogo", trocar, vezes=2)
        self.robo.quando("PainelFechamento", lambda w: w.destroy())
        self.cx.fechar_turno(); self.cx.update()
        t = self.banco.um("SELECT status, resultado_cent FROM turnos")
        self.assertEqual((t["status"], t["resultado_cent"]), ("fechado", 0))
        self.sem_travar()


class TesteFluxoDeEntrada(BaseUI):
    """App.run de ponta a ponta: login real -> menu (ou caixa direto para o nível 0) -> saída."""

    def _app(self):
        from src.ui.app import App
        self.root.destroy()
        app = App(self.banco)
        self.root = app.root
        self.robo = Robo(app.root)
        return app

    def test_login_leva_ao_menu_e_saida_volta_ao_login(self):
        app = self._app()
        vistos = []

        def logar(w):
            vistos.append("login")
            w.var_usuario.set("adm"); w.var_senha.set("ADM"); w.entrar()
        self.robo.quando("JanelaLogin", logar, vezes=1)
        # no 2º login (depois da saída) o usuário fecha a janela: o programa encerra
        self.robo.quando("JanelaLogin", lambda w: (vistos.append("login2"), w.destroy()), vezes=1)

        def sair_do_menu():
            vistos.append("menu" if app.menu is not None else "sem-menu")
            self.robo.quando("Dialogo", lambda w: clicar(w, "Sim"))
            app.sair()
        app.root.after(900, sair_do_menu)
        app.root.after(12000, app.root.destroy)        # rede de segurança
        app.root.after(80, app.entrar)
        app.root.mainloop()
        self.assertEqual(vistos, ["login", "menu", "login2"])
        self.sem_travar()

    def test_operador_nivel_zero_vai_direto_ao_caixa_e_pede_o_turno(self):
        self.ctx.cadastros.salvar("operadores", {"nome": "Caixa1", "senha": "9", "nivel": "0"})
        app = self._app()
        vistos = []

        def logar(w):
            w.var_usuario.set("caixa1"); w.var_senha.set("9"); w.entrar()
        self.robo.quando("JanelaLogin", logar, vezes=1)
        self.robo.quando("JanelaLogin", lambda w: w.destroy(), vezes=1)

        def turno(w):                    # diálogos da abertura do turno: nº do turno, fundo, confirmação
            campos = entradas(w)
            if campos:
                campos[0].delete(0, "end"); campos[0].insert(0, "1" if w.title() == "Abertura do turno" and not vistos else "50,00")
                vistos.append(w.title()); clicar(w, "OK")
            else:
                clicar(w, "Sim")
        self.robo.quando("Dialogo", turno, vezes=3)

        def fechar_caixa():
            from src.ui.caixa_ui import JanelaCaixa
            cx = next((w for w in app.root.winfo_children() if isinstance(w, JanelaCaixa)), None)
            vistos.append("caixa" if cx is not None else "sem-caixa")
            if cx is not None:
                cx.destroy()
        app.root.after(1500, fechar_caixa)
        app.root.after(15000, app.root.destroy)
        app.root.after(80, app.entrar)
        app.root.mainloop()
        self.assertIn("caixa", vistos)
        t = self.banco.um("SELECT numero, valor_inicial_cent, status FROM turnos")
        self.assertEqual((t["numero"], t["valor_inicial_cent"], t["status"]), (1, 5000, "aberto"))
        self.sem_travar()


class TesteLancamentosUI(BaseUI):
    def test_compra_de_estoque_pela_tela(self):
        from src.ui.lancamentos_ui import JanelaEstoque
        forn = self.banco.inserir("fornecedores", {"nome": "AMBEV"})
        j = JanelaEstoque(self.root, self.ctx); j.update()
        j.v_tipo.set("compra"); j._tipo_mudou()
        j.v_forn.set("AMBEV"); j.v_valor.set("48,00"); j.v_doc.set("123")
        j.iniciar(); j.update()
        self.assertIsNotNone(j.lanc_id)
        j.v_cod.set("1"); j._achar_codigo()
        j.v_qtd.set("24"); j.v_val_item.set("48,00")
        j.adicionar_item(); j.update()
        p = self.banco.um("SELECT qt_atual, ult_preco_cent FROM produtos WHERE id = ?", (self.skol,))
        self.assertEqual((p["qt_atual"], p["ult_preco_cent"]), (74, 200))
        self.assertEqual(j.grade.total(), 1)
        self.robo.quando("Dialogo", lambda w: clicar(w, "Sim"))
        j.grade.selecionar_indice(0); j.remover_item(); j.update()
        self.assertEqual(self.banco.valor("SELECT qt_atual FROM produtos WHERE id = ?", (self.skol,)), 50)
        self.sem_travar()
        j.destroy()

    def test_conta_mensal_pela_tela(self):
        from src.ui.lancamentos_ui import JanelaContas
        j = JanelaContas(self.root, self.ctx); j.update()
        j.v_sub.set("Aluguel - Imóvel (-)")
        j.v_desc.set("Aluguel"); j.v_valor.set("2.500,00"); j.v_venc.set("10/10/2026"); j.v_meses.set("3")
        j.gravar(); j.update()
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM contas"), 3)
        self.assertEqual(self.banco.valor("SELECT MAX(valor_cent) FROM contas"), 250000)
        j.destroy()

    def test_backup_e_limpeza_pela_tela(self):
        from src.ui import utilitarios_ui
        with tempfile.TemporaryDirectory() as pasta:
            self.banco.cfg_set("pasta_backup", pasta)
            self.robo.quando("Dialogo", lambda w: w.destroy())
            utilitarios_ui.executar(self.root, self.ctx, "backup")
            import os
            self.assertEqual(len([f for f in os.listdir(pasta) if f.endswith(".db")]), 1)
        self.sem_travar()


class TesteAvisosDeCorteNasTelas(BaseUI):
    """Listas que mostram só os mais recentes avisam o operador em vez de cortar em silêncio."""

    def vender(self, n):
        self.abrir_turno()
        for _ in range(n):
            v = self.ctx.caixa.abrir_balcao()
            self.ctx.caixa.adicionar_item(v, self.agua, 1)
            self.ctx.caixa.adicionar_pagamento(v, self.banco.valor("SELECT id FROM tipos_pagamento WHERE tipo = 'Dinheiro'"), 350)
            self.ctx.caixa.fechar(v)

    def test_cupons_do_periodo_avisam_quando_a_grade_corta(self):
        from src.ui import relatorios_ui
        self.vender(3)
        with mock.patch.object(relatorios_ui, "LIMITE_CUPONS", 2):
            j = relatorios_ui.JanelaVendasPeriodo(self.root, self.ctx); j.update()
            texto = j.resumo.cget("text")
            self.assertEqual(j.grade.total(), 2)
            self.assertIn("MOSTRANDO OS 2 ÚLTIMOS DE 3", texto)
            self.assertIn("TC 3", texto)                       # os totais valem para o período inteiro
            j.destroy()
        j = relatorios_ui.JanelaVendasPeriodo(self.root, self.ctx); j.update()
        self.assertEqual(j.grade.total(), 3)
        self.assertNotIn("MOSTRANDO", j.resumo.cget("text"))
        j.destroy()

    def test_lancamentos_anteriores_avisam_quando_a_lista_corta(self):
        from src.ui import lancamentos_ui
        for _ in range(3):
            self.ctx.estoque.criar_lancamento("entrada")
        j = lancamentos_ui.JanelaEstoque(self.root, self.ctx); j.update()
        with mock.patch.object(lancamentos_ui, "LIMITE_LANCAMENTOS", 2), \
                mock.patch.object(tema, "escolher", return_value=None) as escolher:
            j.abrir_anterior()
        itens, rotulo = escolher.call_args.args[2], escolher.call_args.args[3]
        self.assertEqual(len(itens), 2)
        self.assertIn("2 lançamentos mais recentes de 3", rotulo)
        with mock.patch.object(tema, "escolher", return_value=None) as escolher:
            j.abrir_anterior()
        self.assertEqual((len(escolher.call_args.args[2]), escolher.call_args.args[3]), (3, "Filtrar por texto:"))
        j.destroy()

    def test_painel_de_fechamento_mostra_o_total_fora_da_gaveta(self):
        from src.ui.caixa_dialogos import PainelFechamento
        self.abrir_turno()
        v = self.ctx.caixa.abrir_balcao()
        self.ctx.caixa.adicionar_item(v, self.skol, 2)
        self.ctx.caixa.adicionar_pagamento(v, self.banco.valor("SELECT id FROM tipos_pagamento WHERE tipo = 'Pix'"), 1600)
        self.ctx.caixa.fechar(v)
        res = self.ctx.turnos.fechar(self.ctx.turnos.atual()["id"], self.ctx.operador_id, 10000)
        pares = {}

        def ler(janela):                          # rótulo (coluna 0) e valor (coluna 1) da mesma linha da grade
            linhas, pilha = {}, [janela]
            while pilha:
                w = pilha.pop()
                pilha.extend(w.winfo_children())
                if isinstance(w, ttk.Label) and w.grid_info():
                    info = w.grid_info()
                    linhas.setdefault((str(w.master), int(info["row"])), {})[int(info["column"])] = w.cget("text")
            pares.update({c[0]: c[1] for c in linhas.values() if 0 in c and 1 in c})
            janela.destroy()
        self.robo.quando("PainelFechamento", ler)
        PainelFechamento(self.root, self.ctx, res)
        self.assertEqual(pares["Fora da gaveta (cartão/Pix)"], "16,00")
        self.assertEqual(pares["Valor esperado"], "100,00")
        self.assertEqual(pares["Pix"], "16,00")
        self.assertEqual(res["resultado"], 0)
        self.sem_travar()


class TesteLoginComLicenca(BaseUI):
    """Entrada com a licença exigida (o executável): bloqueio, renovação, aviso e turno aberto."""
    SEMENTE = bytes(range(32))

    def setUp(self):
        super().setUp()
        from src.core import ed25519, licenca
        self.licenca = licenca
        patcher = mock.patch.object(licenca, "CHAVE_PUBLICA_HEX", ed25519.chave_publica(self.SEMENTE).hex())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(fmt.definir_relogio, None)
        fmt.definir_relogio(lambda: datetime(2026, 10, 3, 21, 0, 0))
        self.banco.cfg_set("licenca_exigir", "S")

    def codigo(self, dias=30, hoje=date(2026, 10, 3)):
        return self.licenca.gerar_licenca(self.SEMENTE, "LOJA-1", dias, hoje)

    def entrar(self, senha="adm", codigo=None):
        from src.ui.login import JanelaLogin
        j = JanelaLogin(self.root, self.ctx, "Loja")
        j.var_usuario.set("adm"); j.var_senha.set(senha)
        with mock.patch.object(tema, "pedir_texto", return_value=codigo) as pedir, \
                mock.patch.object(tema, "mensagem") as aviso:
            j.entrar()
        return j, pedir, aviso

    def test_sem_licenca_pede_o_codigo_e_entra_ao_ativar(self):
        j, pedir, aviso = self.entrar(codigo=self.codigo())
        pedir.assert_called_once()
        self.assertEqual(j.operador.nome, "ADM")
        self.assertEqual(self.banco.cfg("chave_loja"), "LOJA-1")
        aviso.assert_not_called()
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM log_eventos WHERE evento = 'licenca_bloqueio'"), 1)

    def test_codigo_invalido_ou_cancelado_nao_deixa_entrar(self):
        j, pedir, _ = self.entrar(codigo="lixo")
        self.assertIsNone(j.operador)
        self.assertIn("inválido", j.lbl_msg.cget("text"))
        j.destroy()
        j2, pedir2, _ = self.entrar(codigo=None)
        self.assertIsNone(j2.operador)
        j2.destroy()
        pedir.assert_called_once(); pedir2.assert_called_once()

    def abrir_turno_antes_da_exigencia(self, aberto_em=None):
        """Abre o turno com a licença ainda desligada (como numa loja que já estava operando) e liga a exigência."""
        self.banco.cfg_set("licenca_exigir", "N")
        tid = self.abrir_turno()
        if aberto_em:
            self.banco.executar("UPDATE turnos SET aberto_em = ? WHERE id = ?", (aberto_em, tid))
        self.banco.cfg_set("licenca_exigir", "S")

    def test_com_o_turno_aberto_entra_sem_pedir_codigo_e_avisa(self):
        self.abrir_turno_antes_da_exigencia()
        j, pedir, aviso = self.entrar()
        pedir.assert_not_called()
        self.assertEqual(j.operador.nome, "ADM")
        self.assertIn("turno aberto", aviso.call_args.args[1])

    def test_turno_antigo_ou_esquecido_nao_isenta_da_licenca(self):
        self.abrir_turno_antes_da_exigencia(aberto_em="2026-09-20 08:00:00")
        j, pedir, aviso = self.entrar(codigo=None)
        pedir.assert_called_once()                              # não houve isenção: pediu o código
        self.assertIsNone(j.operador)
        j.destroy()

    def test_sem_licenca_nao_abre_turno_novo_nem_pelo_menu(self):
        from src.core.erros import ErroNegocio
        with self.assertRaisesRegex(ErroNegocio, "Renove a licença"):
            self.ctx.turnos.abrir(self.ctx.operador_id, 1, 0)

    def test_perto_do_vencimento_avisa_e_registra_o_uso(self):
        self.licenca.ativar(self.banco, self.codigo(dias=3))
        j, pedir, aviso = self.entrar()
        pedir.assert_not_called()
        self.assertEqual(j.operador.nome, "ADM")
        self.assertIn("vence em 3 dias", aviso.call_args.args[1])
        self.assertEqual(self.banco.cfg("licenca_ultimo_uso"), "2026-10-03")

    def test_licenca_em_dia_entra_sem_aviso_e_senha_errada_continua_barrando(self):
        self.licenca.ativar(self.banco, self.codigo(dias=30))
        j, _, aviso = self.entrar(senha="errada")
        self.assertIsNone(j.operador)
        self.assertEqual(j.lbl_msg.cget("text"), "Senha Incorreta")
        j.destroy()
        j, _, aviso = self.entrar()
        self.assertEqual(j.operador.nome, "ADM")
        aviso.assert_not_called()

    def test_sem_exigencia_o_login_nao_mexe_na_licenca(self):
        self.banco.cfg_set("licenca_exigir", "N")
        j, pedir, aviso = self.entrar()
        self.assertEqual(j.operador.nome, "ADM")
        pedir.assert_not_called(); aviso.assert_not_called()
        self.assertEqual(self.banco.cfg("licenca_ultimo_uso"), "")
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM log_eventos WHERE evento LIKE 'licenca%'"), 0)
