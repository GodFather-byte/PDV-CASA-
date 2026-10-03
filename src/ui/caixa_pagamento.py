"""Painel de pagamento do caixa (manual do Caixa: 'Fechar uma venda escolhendo a forma de pagamento').

Fluxo por teclado: forma de pagamento (letras ou setas) -> Enter -> valor -> Enter.
Seta para cima chega a Desconto/Serviço; Esc volta ao lançamento de itens sem fechar a venda."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.core import formatacao as fmt
from src.core.erros import ErroNegocio
from src.ui import caixa_dialogos, tema
from src.ui.visualizador import Visualizador


class JanelaPagamento(tk.Toplevel):
    def __init__(self, master, ctx, venda_id: int):
        super().__init__(master)
        self.ctx, self.venda_id = ctx, venda_id
        self.caixa = ctx.caixa
        self.fechou = False
        self.desconto_autorizado = not ctx.acesso.precisa_senha(ctx.operador, "caixa_desconto", "exigir_senha_desconto")
        self.title("Pagamento")
        self.configure(bg=tema.COR["fundo"])
        self.formas = self.caixa.formas_pagamento()
        v = self.caixa.obter(venda_id)
        self.eh_credito = v["modalidade"] == "caderneta" and not self.caixa.itens(venda_id)
        self._montar(v)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<F10>", lambda e: self.fechar_venda())
        self.atualizar()
        tema.centralizar(self, master.winfo_toplevel())
        self.transient(master.winfo_toplevel())
        tema.modalizar(self)
        self.grade_formas.tree.focus_set()
        self.grade_formas.selecionar_indice(0)
        self.wait_window(self)

    # --------------------------------------------------------------- layout
    def _montar(self, v: dict) -> None:
        corpo = ttk.Frame(self, padding=14)
        corpo.pack(fill="both", expand=True)
        esq = ttk.Frame(corpo)
        esq.grid(row=0, column=0, sticky="n", padx=(0, 16))
        topo = tk.Frame(esq, bg="white", bd=1, relief="solid", padx=14, pady=6)
        topo.pack(fill="x")
        tk.Label(topo, text="Total:", bg="white", fg=tema.COR["marinho"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.lbl_total = tk.Label(topo, text="0,00", bg="white", fg=tema.COR["total"], font=("Georgia", 40, "bold"))
        self.lbl_total.pack(anchor="e")
        trc = tk.Frame(esq, bg="white", bd=1, relief="solid", padx=14, pady=4)
        trc.pack(fill="x", pady=(6, 10))
        self.lbl_troco_rotulo = tk.Label(trc, text="Troco:", bg="white", fg=tema.COR["marinho"], font=("Segoe UI", 14, "bold"))
        self.lbl_troco_rotulo.pack(side="left")
        self.lbl_troco = tk.Label(trc, text="0,00", bg="white", fg=tema.COR["troco"], font=("Georgia", 24, "bold"))
        self.lbl_troco.pack(side="right")
        grade = ttk.Frame(esq)
        grade.pack(fill="x")
        self.var_pct, self.var_desc, self.var_serv = tk.StringVar(), tk.StringVar(), tk.StringVar()
        ttk.Label(grade, text="Desc. %", style="Rotulo.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(grade, text="Desc. R$", style="Rotulo.TLabel").grid(row=0, column=1, sticky="w")
        self.e_pct = ttk.Entry(grade, textvariable=self.var_pct, width=8)
        self.e_desc = ttk.Entry(grade, textvariable=self.var_desc, width=14)
        self.e_pct.grid(row=1, column=0, padx=(0, 8))
        self.e_desc.grid(row=1, column=1)
        ttk.Label(grade, text="Serviço R$", style="Rotulo.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.e_serv = ttk.Entry(grade, textvariable=self.var_serv, width=14)
        self.e_serv.grid(row=3, column=0, columnspan=2, sticky="w")
        self.lbl_resumo = ttk.Label(esq, text="", justify="left", font=tema.FONTE_MONO)
        self.lbl_resumo.pack(anchor="w", pady=(12, 0))
        self.lbl_msg = ttk.Label(esq, text="", foreground=tema.COR["perigo"], wraplength=300, justify="left")
        self.lbl_msg.pack(anchor="w", pady=(6, 0))

        dir_ = ttk.Frame(corpo)
        dir_.grid(row=0, column=1, sticky="nsew")
        ttk.Label(dir_, text="Forma de pagamento (digite a inicial ou use as setas)", style="Rotulo.TLabel").pack(anchor="w")
        self.grade_formas = tema.Grade(dir_, [("tipo", "Forma", 260, "w")], altura=6)
        self.grade_formas.pack(fill="x")
        for f in self.formas:
            self.grade_formas.adicionar([f["tipo"]], iid=f["id"])
        ttk.Label(dir_, text="Valor R$", style="Rotulo.TLabel").pack(anchor="w", pady=(10, 0))
        self.var_valor = tk.StringVar()
        self.e_valor = ttk.Entry(dir_, textvariable=self.var_valor, width=18)
        self.e_valor.pack(anchor="w")
        ttk.Label(dir_, text="Pagamentos lançados (Delete exclui o selecionado)", style="Rotulo.TLabel").pack(anchor="w", pady=(10, 0))
        self.grade_pag = tema.Grade(dir_, [("tipo", "Pagamento", 200, "w"), ("valor", "Valor", 90, "e")], altura=5)
        self.grade_pag.pack(fill="x")
        texto_botao = "Lançar crédito (F10)" if self.eh_credito else "Gravar conta / imprimir (F10)"
        self.btn_fechar = ttk.Button(dir_, text=texto_botao, style="Ok.TButton", command=self.fechar_venda)
        self.btn_fechar.pack(fill="x", pady=(14, 0))
        ttk.Button(dir_, text="Voltar para os itens (Esc)", command=self.destroy).pack(fill="x", pady=(6, 0))

        t = self.grade_formas.tree
        t.bind("<Return>", self._forma_escolhida)
        t.bind("<Up>", self._acima_da_lista)
        t.bind("<Key>", self._tecla_forma)
        self.e_valor.bind("<Return>", self._lancar_valor)
        self.e_valor.bind("<Escape>", lambda e: (self.grade_formas.tree.focus_set(), "break")[1])
        self.grade_pag.tree.bind("<Delete>", self._remover_pagamento)
        for e in (self.e_pct, self.e_desc):
            e.bind("<Return>", self._aplicar_desconto)
        self.e_pct.bind("<Down>", lambda e: self.e_desc.focus_set())
        self.e_desc.bind("<Down>", lambda e: self.e_serv.focus_set())
        self.e_serv.bind("<Return>", self._aplicar_servico)
        self.e_serv.bind("<Down>", lambda e: self.grade_formas.tree.focus_set())
        for e in (self.e_pct, self.e_desc, self.e_serv):
            e.bind("<Escape>", lambda ev: (self.grade_formas.tree.focus_set(), "break")[1])
        if v["modalidade"] != "mesa":
            self.e_serv.configure(state="disabled")
        if self.eh_credito:
            for e in (self.e_pct, self.e_desc):
                e.configure(state="disabled")

    # ----------------------------------------------------------- atualização
    def atualizar(self) -> None:
        self.caixa.recalcular(self.venda_id)
        v = self.caixa.obter(self.venda_id)
        pags = self.caixa.pagamentos(self.venda_id)
        self.grade_pag.preencher([[p["tipo"], fmt.fmt_num(p["valor_cent"])] for p in pags], [p["id"] for p in pags])
        pago = sum(p["valor_cent"] for p in pags)
        total = v["total_cent"]
        self.lbl_total.configure(text=fmt.fmt_num(total if not self.eh_credito else max(pago, 0)))
        linhas = [f"Desc.    : {fmt.fmt_num(v['desconto_cent']):>10}", f"Serviço  : {fmt.fmt_num(v['servico_cent']):>10}",
                  f"Taxa     : {fmt.fmt_num(v['taxa_cent']):>10}", f"Produtos : {fmt.fmt_num(v['subtotal_cent']):>10}",
                  f"Pago     : {fmt.fmt_num(pago):>10}"]
        self.lbl_resumo.configure(text="\n".join(linhas))
        self.lbl_msg.configure(text="")
        if self.eh_credito:
            info = self.caixa.info_credito(self.venda_id)
            self.lbl_troco_rotulo.configure(text="Dívida:")
            self.lbl_troco.configure(text=fmt.fmt_num(info["divida"]), fg=tema.COR["perigo"])
            return
        try:
            liq = self.caixa.liquidar(self.venda_id, total)
        except ErroNegocio as e:
            self.lbl_msg.configure(text=str(e))
            self.lbl_troco_rotulo.configure(text="Troco:")
            self.lbl_troco.configure(text="--", fg=tema.COR["perigo"])
            return
        if liq["falta"] > 0:
            self.lbl_troco_rotulo.configure(text="Falta:")
            self.lbl_troco.configure(text=fmt.fmt_num(liq["falta"]), fg=tema.COR["perigo"])
        else:
            self.lbl_troco_rotulo.configure(text="Troco:")
            self.lbl_troco.configure(text=fmt.fmt_num(liq["troco"]), fg=tema.COR["troco"])
            if liq["vale"]:
                self.lbl_msg.configure(text=f"Será emitido contra-vale de {fmt.fmt_brl(liq['vale'])}.",
                                       foreground=tema.COR["aviso"])
        self._sugerir_valor(liq["falta"])

    def _sugerir_valor(self, falta: int) -> None:
        self.var_valor.set(fmt.fmt_num(falta) if falta > 0 else "")

    # --------------------------------------------------------------- teclado
    def _tecla_forma(self, e) -> str | None:
        if len(e.char) == 1 and e.char.isalnum():
            letra = e.char.lower()
            filhos = self.grade_formas.tree.get_children()
            atual = self.grade_formas.indice()
            ordem = list(range(atual + 1, len(filhos))) + list(range(0, atual + 1))
            for i in ordem:
                if self.grade_formas.valores(filhos[i])[0].lower().startswith(letra):
                    self.grade_formas.selecionar_indice(i)
                    break
            return "break"
        return None

    def _acima_da_lista(self, e) -> str | None:
        if self.grade_formas.indice() <= 0:
            (self.e_pct if str(self.e_pct.cget("state")) != "disabled" else self.e_serv).focus_set()
            return "break"
        return None

    def _forma_escolhida(self, e=None) -> str:
        if self.grade_formas.selecionado() is None:
            return "break"
        self.e_valor.focus_set()
        self.e_valor.selection_range(0, "end")
        return "break"

    def _lancar_valor(self, e=None) -> str:
        forma = self.grade_formas.selecionado()
        if forma is None:
            return "break"
        try:
            cent = fmt.para_centavos(self.var_valor.get())
        except ValueError:
            self.lbl_msg.configure(text="Valor inválido.", foreground=tema.COR["perigo"])
            return "break"
        ok, _ = tema.tratar(self, self.caixa.adicionar_pagamento, self.venda_id, int(forma), cent)
        if not ok:
            return "break"
        self.atualizar()
        pago = sum(p["valor_cent"] for p in self.caixa.pagamentos(self.venda_id))
        if self.eh_credito or pago >= self.caixa.obter(self.venda_id)["total_cent"]:
            self.btn_fechar.focus_set()
            self.btn_fechar.bind("<Return>", lambda ev: (self.fechar_venda(), "break")[1])
        else:
            self.grade_formas.tree.focus_set()
        return "break"

    def _remover_pagamento(self, e=None) -> None:
        s = self.grade_pag.selecionado()
        if s is not None:
            self.caixa.remover_pagamento(int(s))
            self.atualizar()

    def _autorizar_desconto(self) -> bool:
        if self.desconto_autorizado:
            return True
        sup = tema.pedir_senha_supervisor(self, self.ctx, "caixa_desconto", "Desconto exige autorização:")
        self.desconto_autorizado = sup is not None
        return self.desconto_autorizado

    def _aplicar_desconto(self, e=None) -> str:
        if not self._autorizar_desconto():
            return "break"
        pct, valor = self.var_pct.get().strip(), self.var_desc.get().strip()
        try:
            if pct:
                self.caixa.definir_desconto(self.venda_id, pct=float(pct.replace(",", ".")))
            else:
                self.caixa.definir_desconto(self.venda_id, valor_cent=fmt.para_centavos(valor) if valor else 0)
        except (ErroNegocio, ValueError) as ex:
            tema.erro(self, str(ex) if isinstance(ex, ErroNegocio) else "Valor de desconto inválido.")
            return "break"
        self.var_pct.set("")
        self.var_desc.set("")
        self.atualizar()
        self.grade_formas.tree.focus_set()
        return "break"

    def _aplicar_servico(self, e=None) -> str:
        texto = self.var_serv.get().strip()
        try:
            self.caixa.definir_servico(self.venda_id, fmt.para_centavos(texto) if texto else None)
        except (ErroNegocio, ValueError) as ex:
            tema.erro(self, str(ex) if isinstance(ex, ErroNegocio) else "Valor de serviço inválido.")
            return "break"
        self.var_serv.set("")
        self.atualizar()
        self.grade_formas.tree.focus_set()
        return "break"

    # -------------------------------------------------------------- fechamento
    def fechar_venda(self) -> None:
        v = self.caixa.obter(self.venda_id)
        garcom = pessoas = None
        if v["modalidade"] == "mesa":
            if self.ctx.banco.cfg_bool("controle_garcom") and not v["garcom_id"]:
                garcom = caixa_dialogos.escolher_garcom(self, self.ctx)
                if garcom is None:
                    return
            if self.ctx.banco.cfg_bool("pergunta_pessoas") and not v["pessoas"]:
                pessoas = tema.pedir_numero(self, "Mesa", "Número de pessoas na mesa:", 1, 1, 999)
                if pessoas is None:
                    return
        credito = None
        if self.eh_credito:
            info = self.caixa.info_credito(self.venda_id)
            if info["excedente"] > 0:
                credito = tema.confirmar(
                    self, f"O valor excede a dívida do cliente em {fmt.fmt_brl(info['excedente'])}.\n"
                          "Acrescentar o excedente ao crédito do cliente?\n(Não = devolver como troco)", "Caderneta")
        ok, venda = tema.tratar(self, self.caixa.fechar, self.venda_id, garcom, pessoas, credito)
        if not ok:
            self.atualizar()
            return
        self.fechou = True
        if self.ctx.banco.cfg_bool("imprimir_cupom", True):
            texto = self.ctx.impressao.cupom(self.venda_id)
            if self.ctx.impressao.deve_mostrar_na_tela():
                self.destroy()
                Visualizador(self.master, self.ctx, f"Cupom {venda['cupom']}", texto, f"cupom_{venda['cupom']}")
                return
            self.ctx.impressao.enviar(texto, f"cupom_{venda['cupom']}")
        self.destroy()
