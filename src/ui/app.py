"""Janela principal: login, os sete botões do menu (manual ADM seção 1) e o painel de resumo."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

from src.controllers.acesso_controller import GRUPOS_MENU
from src.controllers.fila_impressao_controller import ServicoFilaImpressao
from src.core import formatacao as fmt
from src.core.erros import ErroNegocio
from src.database.conexao import BancoDados
from src.ui import tema
from src.ui.contexto import Contexto
from src.ui.login import JanelaLogin
from src.versao import VERSAO

CADASTROS = [("unidades", "Unidades"), ("grupos", "Grupos"), ("subgrupos", "Subgrupos"), ("produtos", "Produtos"),
             ("observacoes", "Observações"), ("composicao", "Composição"), ("cargos", "Cargos"),
             ("operadores", "Operadores"), ("fornecedores", "Fornecedores"), ("clientes", "Clientes"), ("garotas", "Garotas"),
             ("bairros", "Bairros e taxas de entrega"), ("tipos_pagamento", "Tipos de Pagamento"),
             ("planos_contas", "Plano de Contas"), ("subplanos", "Sub Planos"), ("aliquotas", "Alíquotas")]
MODULO_CADASTRO = {"planos_contas": "cad_plano_contas"}   # os demais seguem o padrão cad_<chave>

LANCAMENTOS = [("contas", "Contas", "lanc_contas"), ("estoque", "Estoque", "lanc_estoque")]

RELATORIOS = [
    ("Vendas", [("vendas_periodo", "Venda no período", "rel_vendas"), ("vendas_grupo", "Venda por grupo", "rel_vendas_grupo"),
                ("informativo", "Informativo por dia", "rel_informativos"), ("horas", "Vendas por hora", "rel_informativos"),
                ("cancelados", "Cancelamentos", "rel_informativos")]),
    ("Caixa", [("caixa_mov", "Entradas e saídas financeiras", "rel_caixa"), ("fechamentos", "Fechamentos do caixa", "rel_caixa"),
               ("comandas", "Comandas", "rel_comandas"), ("garcons", "Garçons", "rel_garcons"),
               ("comissao_garotas", "Comissão das garotas", "rel_comissao_garotas")]),
    ("Gestão", [("cmv", "C.M.V. (custo da mercadoria vendida)", "rel_cmv"),
                ("comissao_produto", "Comissão por produto", "rel_comissoes"), ("comissao_venda", "Comissão por venda", "rel_comissoes"),
                ("comissao_cliente", "Vendas por cliente", "rel_comissoes")]),
    ("Clientes", [("clientes_inativos", "Clientes inativos", "rel_clientes"), ("clientes_resumo", "Entrega e caderneta por cliente", "rel_clientes")]),
    ("Financeiro", [("resultado_financeiro", "Resultado financeiro", "rel_financeiro"), ("extrato_contas", "Extrato de contas", "rel_financeiro")]),
    ("Estoque", [("estoque_atual", "Estoque atual", "rel_estoque"), ("mov_estoque", "Movimento de estoque", "rel_estoque"),
                 ("posicao_estoque", "Posição por período", "rel_estoque"), ("custo_medio", "Preço médio de compra", "rel_informativos"),
                 ("form_contagem", "Formulário de contagem", "rel_estoque"), ("form_pedidos", "Formulário de pedidos", "rel_estoque")]),
]

UTILITARIOS = [("limpeza", "Limpeza do movimento", "util_limpeza"), ("comunicacao", "Programa de comunicação", "util_comunicacao"),
               ("backup", "Backup de dados", "util_backup"), ("fila_impressao", "Fila de impressão", "util_fila_impressao")]
CONFIGURACOES = [("acessos", "Acessos", "cfg_acessos"), ("loja", "Loja", "cfg_loja"),
                 ("configuracoes", "Configurações", "cfg_configuracoes"), ("maquinas", "Máquinas", "cfg_maquinas")]

BOTOES = [("Manutenção de Cadastros", "Cadastros", "m"), ("Caixa", "Caixa", "c"), ("Lançamentos", "Lançamentos", "l"),
          ("Relatórios", "Relatórios", "r"), ("Utilitários", "Utilitários", "u"), ("Configurações", "Configurações", "o"),
          ("Saída", "Saída", "s")]


class App:
    def __init__(self, banco: BancoDados | None = None):
        self.banco = banco or BancoDados()
        self.root = tk.Tk()
        self.root.withdraw()
        tema.aplicar_tema(self.root)
        self.ctx = Contexto(self.banco)
        self.janelas: dict[str, tk.Toplevel] = {}
        self.servico_impressao: ServicoFilaImpressao | None = None
        self.menu: tk.Frame | None = None
        self.root.protocol("WM_DELETE_WINDOW", self.sair)
        self._relogio_id = None
        self._consulta_versao: dict | None = None      # {"pronta": bool, "dados": ...}: a thread da rede escreve aqui

    # ---------------------------------------------------------------- fluxo
    def run(self) -> None:
        self._iniciar_fila_impressao()
        self.root.after(80, self.entrar)
        self.root.mainloop()
        if self.servico_impressao is not None:
            self.servico_impressao.parar()
        self.banco.fechar()

    def _iniciar_fila_impressao(self) -> None:
        """Thread que esvazia a fila da impressora térmica/cozinha. Precisa de banco em arquivo (conexão própria)."""
        try:
            self.servico_impressao = ServicoFilaImpressao(self.banco.caminho)
            self.servico_impressao.iniciar()
        except ErroNegocio:
            self.servico_impressao = None

    def entrar(self) -> None:
        self._destruir_menu()
        self.root.withdraw()
        dlg = JanelaLogin(self.root, self.ctx, self.ctx.config.nome_loja())
        self.root.wait_window(dlg)
        if dlg.operador is None:
            self.root.destroy()
            return
        self.ctx.operador = dlg.operador
        self.banco.log("login", dlg.operador.nome, dlg.operador.id)
        if dlg.operador.so_caixa:
            self.abrir_caixa()
            self.root.after(50, self.entrar)
        else:
            self.mostrar_menu()

    def sair(self) -> None:
        if self.ctx.operador is None:
            self.root.destroy()
            return
        if tema.confirmar(self.root, "Encerrar a sessão e voltar à tela de entrada?", "Saída"):
            for j in list(self.janelas.values()):
                try:
                    j.destroy()
                except tk.TclError:
                    pass
            self.janelas.clear()
            self.banco.log("logout", self.ctx.operador.nome, self.ctx.operador.id)
            self.ctx.operador = None
            self.root.after(50, self.entrar)

    # ----------------------------------------------------------------- menu
    def _destruir_menu(self) -> None:
        if self._relogio_id:
            self.root.after_cancel(self._relogio_id)
            self._relogio_id = None
        if self.menu is not None:
            self.menu.destroy()
            self.menu = None

    def mostrar_menu(self) -> None:
        self._destruir_menu()
        r, ctx = self.root, self.ctx
        r.title(f"PDV - {ctx.config.nome_loja()}")
        r.geometry("1040x640")
        r.minsize(900, 560)
        self.menu = tk.Frame(r, bg=tema.COR["marinho"])
        self.menu.pack(fill="both", expand=True)
        cab = tk.Frame(self.menu, bg="white", padx=16, pady=10)
        cab.pack(fill="x")
        tk.Label(cab, text="Produto licenciado e de uso exclusivo para:", bg="white", fg=tema.COR["suave"]).pack(anchor="w")
        tk.Label(cab, text=ctx.config.nome_loja().upper(), bg="white", fg=tema.COR["marinho"], font=("Segoe UI", 20, "bold")).pack(anchor="w")
        self.lbl_operador = tk.Label(cab, bg="white", fg=tema.COR["suave"], justify="right")
        self.lbl_operador.place(relx=1.0, x=-4, y=6, anchor="ne")
        tk.Label(cab, text=f"Versão {VERSAO}", bg="white", fg=tema.COR["suave"]).place(relx=1.0, x=-4, rely=1.0, anchor="se")

        corpo = tk.Frame(self.menu, bg=tema.COR["marinho"], padx=22, pady=18)
        corpo.pack(fill="both", expand=True)
        esq = tk.Frame(corpo, bg=tema.COR["marinho"])
        esq.pack(side="left", fill="y")
        visiveis = ctx.acesso.grupos_visiveis(ctx.operador) + ["Saída"]
        self.botoes: dict[str, tk.Button] = {}
        for rotulo, grupo, letra in BOTOES:
            if grupo not in visiveis:
                continue
            i = rotulo.lower().find(letra)
            b = tk.Button(esq, text=rotulo, font=("Georgia", 16), fg="white", bg=tema.COR["marinho2"], activebackground="#2c52c4",
                          activeforeground="white", relief="raised", bd=2, anchor="w", padx=14, pady=6, width=24, underline=i,
                          command=lambda g=grupo: self.acionar(g))
            b.pack(pady=5, fill="x")
            self.botoes[grupo] = b
            r.bind(f"<KeyPress-{letra}>", lambda e, g=grupo: self.acionar(g))
            r.bind(f"<KeyPress-{letra.upper()}>", lambda e, g=grupo: self.acionar(g))
        self._montar_painel(corpo)
        r.deiconify()
        r.lift()
        r.focus_force()
        self.atualizar_painel()
        self.consultar_atualizacoes()

    def _montar_painel(self, pai) -> None:
        dir_ = tk.Frame(pai, bg=tema.COR["marinho"])
        dir_.pack(side="right", fill="both", expand=True, padx=(30, 0))
        self.painel = tk.Frame(dir_, bg="#0e1a3a", bd=1, relief="solid", padx=14, pady=12)
        self.painel.pack(side="bottom", fill="x")
        self.valores: dict[str, tk.Label] = {}

        def titulo(txt, cor="#9fb3e8"):
            tk.Label(self.painel, text=txt, bg="#0e1a3a", fg=cor, font=tema.FONTE_B).pack(anchor="w", pady=(6, 0))

        def linha(chave, txt, cor="white"):
            f = tk.Frame(self.painel, bg="#0e1a3a")
            f.pack(fill="x")
            tk.Label(f, text=f" - {txt}", bg="#0e1a3a", fg="#d4dcf5").pack(side="left")
            lbl = tk.Label(f, text="0", bg="#0e1a3a", fg=cor, font=tema.FONTE_B, width=12, anchor="e")
            lbl.pack(side="right")
            self.valores[chave] = lbl

        self.lbl_versao = tk.Label(self.painel, text="", bg="#0e1a3a", fg="#ffd24d", font=tema.FONTE_B, cursor="hand2",
                                   wraplength=360, justify="left")
        self.lbl_versao.bind("<Button-1>", lambda e: self.abrir_aviso_versao())
        self.lbl_backup = tk.Label(self.painel, text="", bg="#0e1a3a", fg="#ffd24d", font=tema.FONTE_B)
        self.lbl_backup.pack(anchor="w")
        self.lbl_atualiz = tk.Label(self.painel, text="", bg="#0e1a3a", fg="white", font=tema.FONTE_B)
        self.lbl_atualiz.pack(anchor="w")
        titulo("Estoque:")
        linha("estoque_total", "Produtos em estoque")
        linha("estoque_sem", "Produtos sem estoque", "#ff6b6b")
        linha("estoque_ponto", "Produtos em ponto de pedido", "#ffd24d")
        linha("estoque_normal", "Produtos com estoque normal", "#5be39a")
        titulo("Contas:")
        linha("contas_anteriores", "Contas anteriores não quitadas")
        linha("contas_hoje", "Contas de hoje não quitadas")
        titulo("Vendas:")
        linha("vendas_dia", "Número de vendas no dia")
        linha("venda_media", "Venda média por cupom do dia")
        titulo("Nuvem:")
        linha("pendentes", "Vendas aguardando envio", "#ffd24d")
        linha("rejeitadas", "Vendas recusadas pela nuvem", "#ff6b6b")
        tk.Label(dir_, text=self.ctx.config.loja().get("telefone") or "", bg=tema.COR["marinho"], fg="#9fb3e8").pack(side="top", pady=20)

    def atualizar_painel(self) -> None:
        if self.menu is None:
            return
        from src.controllers.sync_controller import SyncController
        p = self.ctx.relatorios.painel()
        for chave, lbl in self.valores.items():
            if chave == "pendentes":
                valor = SyncController(self.banco).contagem_pendentes()
            elif chave == "rejeitadas":
                valor = SyncController(self.banco).contagem_rejeitadas()
            elif chave == "venda_media":
                valor = fmt.fmt_num(p["venda_media"])
            else:
                valor = p[chave]
            lbl.configure(text=str(valor))
        self.lbl_atualiz.configure(text=f"Última atualização:  {fmt.fmt_datahora(p['atualizado_em'])}")
        self.lbl_backup.configure(text=f"Último backup: {fmt.fmt_datahora(p['ultimo_backup'])}" if p["ultimo_backup"]
                                  else "Não há backup nesta máquina")
        self.mostrar_aviso_versao()
        op = self.ctx.operador
        self.lbl_operador.configure(text=f"Operador: {op.nome}\nNível de acesso: {op.nivel}")
        self._relogio_id = self.root.after(30_000, self.atualizar_painel)

    # --------------------------------------------------------- atualizações
    def mostrar_aviso_versao(self) -> None:
        """Faixa no topo do painel quando há versão nova (vermelha se for crítica). Clicar abre as notas."""
        from src.sync import atualizacoes
        from src.ui import atualizacao_ui
        aviso = atualizacoes.pendente(self.banco)
        if aviso is None:
            self.lbl_versao.pack_forget()
            return
        self.lbl_versao.configure(text=atualizacao_ui.texto_faixa(aviso), fg="#ff6b6b" if aviso["critica"] else "#ffd24d")
        if not self.lbl_versao.winfo_ismapped():
            self.lbl_versao.pack(anchor="w", before=self.lbl_backup, pady=(0, 6))

    def abrir_aviso_versao(self) -> None:
        from src.sync import atualizacoes
        from src.ui import atualizacao_ui
        aviso = atualizacoes.pendente(self.banco)
        if aviso is not None:
            atualizacao_ui.mostrar(self.root, self.banco, aviso)
            self.mostrar_aviso_versao()

    def consultar_atualizacoes(self) -> None:
        """Pergunta à nuvem se há versão nova, numa thread (a rede não pode travar a tela). O banco só é usado aqui, na
        thread da tela: a thread recebe o endereço e o token prontos e devolve a resposta em self._consulta_versao."""
        from src.sync import atualizacoes
        url, token = self.banco.cfg("api_url"), self.banco.cfg("api_token")
        if not url.strip() or not token.strip() or not atualizacoes.precisa_consultar(self.banco) or self._consulta_versao:
            return
        estado = self._consulta_versao = {"pronta": False, "dados": None}

        def rede():
            estado["dados"] = atualizacoes.consultar(url, token)
            estado["pronta"] = True
        threading.Thread(target=rede, name="consulta-atualizacoes", daemon=True).start()
        self.root.after(500, self._receber_consulta)

    def _receber_consulta(self) -> None:
        from src.sync import atualizacoes
        estado = self._consulta_versao
        if estado is None:
            return
        if not estado["pronta"]:
            self.root.after(500, self._receber_consulta)
            return
        self._consulta_versao = None
        atualizacoes.gravar(self.banco, estado["dados"])
        if self.menu is not None:
            self.mostrar_aviso_versao()

    # --------------------------------------------------------------- ações
    def acionar(self, grupo: str) -> None:
        try:
            if isinstance(self.root.focus_get(), (tk.Entry, ttk.Entry)):
                return
        except KeyError:   # foco em lista suspensa de combobox
            return
        if grupo == "Saída":
            return self.sair()
        if grupo == "Caixa":
            return self.abrir_caixa()
        ctx = self.ctx
        m = tk.Menu(self.root, tearoff=0, font=tema.FONTE)
        permitidos = {x["modulo"] for x in ctx.acesso.modulos_permitidos(ctx.operador, grupo)}
        if grupo == "Cadastros":
            for chave, rotulo in CADASTROS:
                mod = MODULO_CADASTRO.get(chave, f"cad_{chave}")
                if mod in permitidos:
                    m.add_command(label=rotulo, command=lambda c=chave: self.abrir_cadastro(c))
        elif grupo == "Lançamentos":
            for chave, rotulo, mod in LANCAMENTOS:
                if mod in permitidos:
                    m.add_command(label=rotulo, command=lambda c=chave: self.abrir_lancamento(c))
        elif grupo == "Relatórios":
            for sub, itens in RELATORIOS:
                visiveis = [i for i in itens if i[2] in permitidos]
                if visiveis:
                    sm = tk.Menu(m, tearoff=0, font=tema.FONTE)
                    for chave, rotulo, _ in visiveis:
                        sm.add_command(label=rotulo, command=lambda c=chave: self.abrir_relatorio(c))
                    m.add_cascade(label=sub, menu=sm)
        elif grupo == "Utilitários":
            for chave, rotulo, mod in UTILITARIOS:
                if mod in permitidos:
                    m.add_command(label=rotulo, command=lambda c=chave: self.utilitario(c))
        elif grupo == "Configurações":
            for chave, rotulo, mod in CONFIGURACOES:
                if mod in permitidos:
                    m.add_command(label=rotulo, command=lambda c=chave: self.abrir_config(c))
        b = self.botoes[grupo]
        try:
            m.tk_popup(b.winfo_rootx() + b.winfo_width() - 10, b.winfo_rooty() + 8)
        finally:
            m.grab_release()

    def _unica(self, chave: str, criar):
        j = self.janelas.get(chave)
        if j is not None and j.winfo_exists():
            j.deiconify()
            j.lift()
            j.focus_force()
            return j
        j = criar()
        self.janelas[chave] = j
        return j

    def abrir_caixa(self) -> None:
        from src.ui.caixa_ui import JanelaCaixa
        j = JanelaCaixa(self.root, self.ctx)
        self.root.wait_window(j)
        if self.menu is not None:
            self.atualizar_painel()

    def abrir_cadastro(self, chave: str) -> None:
        if chave == "composicao":
            from src.ui.composicao_ui import JanelaComposicao
            self._unica("composicao", lambda: JanelaComposicao(self.root, self.ctx))
            return
        from src.ui.cadastros_tk import JanelaCadastro
        self._unica("cad_" + chave, lambda: JanelaCadastro(self.root, self.ctx, chave))

    def abrir_lancamento(self, chave: str) -> None:
        from src.ui.lancamentos_ui import JanelaContas, JanelaEstoque
        classe = JanelaContas if chave == "contas" else JanelaEstoque
        self._unica("lanc_" + chave, lambda: classe(self.root, self.ctx))

    def abrir_relatorio(self, chave: str) -> None:
        from src.ui.relatorios_ui import abrir_relatorio
        abrir_relatorio(self.root, self.ctx, chave)

    def abrir_config(self, chave: str) -> None:
        from src.ui import config_ui
        self._unica("cfg_" + chave, lambda: config_ui.abrir(self.root, self.ctx, chave))

    def utilitario(self, chave: str) -> None:
        from src.ui import utilitarios_ui
        utilitarios_ui.executar(self.root, self.ctx, chave)
        self.atualizar_painel()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
