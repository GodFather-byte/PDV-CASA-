"""Lançamentos (manual ADM seção 5): contas a pagar/receber e movimentos de estoque."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.controllers.estoque_controller import TIPOS
from src.core import formatacao as fmt
from src.core.erros import ErroNegocio
from src.ui import tema
from src.ui.visualizador import Visualizador


def _campo(pai, rotulo, widget_fn, linha, coluna, span=1):
    q = ttk.Frame(pai)
    q.grid(row=linha, column=coluna, columnspan=span, sticky="w", padx=(0, 14), pady=(0, 6))
    ttk.Label(q, text=rotulo, style="Rotulo.TLabel").pack(anchor="w")
    w = widget_fn(q)
    w.pack(anchor="w", fill="x")
    return w


class JanelaContas(tk.Toplevel):
    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx, self.cad = ctx, ctx.cadastros
        self.id_atual: int | None = None
        self.title("Lançamento de Contas")
        self.configure(bg=tema.COR["fundo"])
        self.geometry("1120x720")
        self._barra()
        self._form()
        self._filtros()
        self._grade()
        self.status = ttk.Label(self, text="", foreground=tema.COR["suave"], padding=(10, 3))
        self.status.pack(fill="x", side="bottom")
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-s>", lambda e: self.gravar())
        self.novo()
        self.listar()
        self.transient(master.winfo_toplevel())

    def _barra(self) -> None:
        b = tk.Frame(self, bg=tema.COR["marinho"], padx=6, pady=5)
        b.pack(fill="x")
        for rotulo, cmd in (("Incluir", self.novo), ("Excluir", self.excluir), ("Gravar", self.gravar), ("Cancelar", self.cancelar),
                            ("Quitar", self.quitar), ("Desfazer quitação", self.desquitar)):
            ttk.Button(b, text=rotulo, style="Barra.TButton", command=cmd).pack(side="left", padx=2)
        ttk.Button(b, text="Sair", style="Barra.TButton", command=self.destroy).pack(side="right")

    def _form(self) -> None:
        f = ttk.Frame(self, padding=(10, 8, 10, 0))
        f.pack(fill="x")
        subs = self.cad.opcoes("subplanos")
        self.mapa_sub = {r: i for i, r in subs}
        self.v_sub = tk.StringVar()
        self.cb_sub = _campo(f, "Sub plano de contas *", lambda p: ttk.Combobox(
            p, textvariable=self.v_sub, values=[r for _, r in subs], state="readonly", width=40), 0, 0, 2)
        self.v_desc = tk.StringVar()
        _campo(f, "Descrição *", lambda p: ttk.Entry(p, textvariable=self.v_desc, width=44), 0, 2, 2)
        tipos = self.cad.opcoes("tipos_pagamento")
        self.mapa_tipo = {r: i for i, r in tipos}
        self.v_tipo = tk.StringVar()
        _campo(f, "Tipo financeiro *", lambda p: ttk.Combobox(p, textvariable=self.v_tipo, values=[r for _, r in tipos], state="readonly", width=26), 1, 0)
        self.v_valor = tk.StringVar()
        _campo(f, "Valor *", lambda p: ttk.Entry(p, textvariable=self.v_valor, width=14), 1, 1)
        self.v_doc = tk.StringVar()
        _campo(f, "Documento de pagamento", lambda p: ttk.Entry(p, textvariable=self.v_doc, width=26), 1, 2)
        self.v_nota = tk.StringVar()
        _campo(f, "Nota fiscal / comprovante", lambda p: ttk.Entry(p, textvariable=self.v_nota, width=22), 1, 3)
        forn = self.cad.opcoes("fornecedores")
        self.mapa_forn = {r: i for i, r in forn}
        self.v_forn = tk.StringVar()
        _campo(f, "Fornecedor", lambda p: ttk.Combobox(p, textvariable=self.v_forn, values=[""] + [r for _, r in forn], state="readonly", width=26), 2, 0)
        self.v_entrada, self.v_venc, self.v_quit = tk.StringVar(), tk.StringVar(), tk.StringVar()
        _campo(f, "Dt. entrada", lambda p: ttk.Entry(p, textvariable=self.v_entrada, width=12), 2, 1)
        _campo(f, "Dt. vencimento", lambda p: ttk.Entry(p, textvariable=self.v_venc, width=12), 2, 2)
        _campo(f, "Dt. quitação", lambda p: ttk.Entry(p, textvariable=self.v_quit, width=12), 2, 3)
        self.v_merc, self.v_prev = tk.BooleanVar(), tk.BooleanVar()
        sf = ttk.Frame(f)
        sf.grid(row=3, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(sf, text="Refere-se a mercadorias", variable=self.v_merc).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(sf, text="Previsão (não aparece no resultado até confirmar)", variable=self.v_prev).pack(side="left")
        self.v_meses = tk.StringVar(value="1")
        self.sp_meses = _campo(f, "Conta mensal: repetir por (meses)", lambda p: ttk.Spinbox(p, from_=1, to=120, textvariable=self.v_meses, width=6), 3, 3)

    def _filtros(self) -> None:
        f = ttk.Frame(self, padding=(10, 4, 10, 0))
        f.pack(fill="x")
        hoje = fmt.hoje()
        self.f_de, self.f_ate = tk.StringVar(value=fmt.fmt_data(hoje[:8] + "01")), tk.StringVar(value=fmt.fmt_data(fmt.somar_meses(hoje[:8] + "01", 1)))
        self.f_por, self.f_sit = tk.StringVar(value="Vencimento"), tk.StringVar(value="Todas")
        ttk.Label(f, text="Mostrar de").pack(side="left")
        ttk.Entry(f, textvariable=self.f_de, width=11).pack(side="left", padx=4)
        ttk.Label(f, text="até").pack(side="left")
        ttk.Entry(f, textvariable=self.f_ate, width=11).pack(side="left", padx=4)
        ttk.Combobox(f, textvariable=self.f_por, values=["Vencimento", "Entrada", "Quitação"], state="readonly", width=11).pack(side="left", padx=4)
        ttk.Combobox(f, textvariable=self.f_sit, values=["Todas", "Em aberto", "Quitadas"], state="readonly", width=10).pack(side="left", padx=4)
        ttk.Button(f, text="Atualizar lista", command=self.listar).pack(side="left", padx=8)

    def _grade(self) -> None:
        q = ttk.Frame(self, padding=10)
        q.pack(fill="both", expand=True)
        self.grade = tema.Grade(q, [("venc", "Vencimento", 90, "w"), ("ent", "Entrada", 90, "w"), ("quit", "Quitação", 90, "w"),
                                    ("desc", "Descrição", 230, "w"), ("plano", "Plano - Sub plano", 230, "w"), ("tipo", "Tipo", 110, "w"),
                                    ("valor", "Valor", 90, "e"), ("doc", "Documento", 110, "w"), ("prev", "Prev.", 45, "center"),
                                    ("parc", "Parc.", 50, "center")], altura=10)
        self.grade.pack(fill="both", expand=True)
        self.grade.tag("quitada", foreground=tema.COR["ok"])
        self.grade.tag("vencida", foreground=tema.COR["perigo"])
        self.grade.tree.bind("<<TreeviewSelect>>", self._selecionou)
        self.grade.tree.bind("<Delete>", lambda e: self.excluir())

    # ---------------------------------------------------------------- dados
    def listar(self, selecionar: int | None = None) -> None:
        try:
            de, ate = fmt.para_data_iso(self.f_de.get()), fmt.para_data_iso(self.f_ate.get())
        except ValueError as e:
            tema.aviso(self, str(e))
            return
        por = {"Vencimento": "dt_vencimento", "Entrada": "dt_entrada", "Quitação": "dt_quitacao"}[self.f_por.get()]
        quit_ = {"Todas": None, "Em aberto": False, "Quitadas": True}[self.f_sit.get()]
        self.linhas = self.ctx.contas.listar(de, ate, por, quitada=quit_)
        hoje = fmt.hoje()
        total = 0
        self.grade.limpar()
        for c in self.linhas:
            tag = ("quitada",) if c["dt_quitacao"] else (("vencida",) if c["dt_vencimento"] < hoje else ())
            sinal = -c["valor_cent"] if c["debito"] else c["valor_cent"]
            total += sinal
            self.grade.adicionar([fmt.fmt_data(c["dt_vencimento"]), fmt.fmt_data(c["dt_entrada"]), fmt.fmt_data(c["dt_quitacao"]), c["descricao"],
                                  f"{c['plano']} / {c['subplano']}", c["tipo_financeiro"], fmt.fmt_num(c["valor_cent"]), c["documento"] or "",
                                  "S" if c["previsao"] else "", c["parcela"] or ""], iid=c["id"], tags=tag)
        self.status.configure(text=f"{len(self.linhas)} conta(s)   |   Saldo do período (créditos - débitos): {fmt.fmt_brl(total)}")
        if selecionar:
            self.grade.selecionar(selecionar)

    def novo(self) -> None:
        self.id_atual = None
        for v in (self.v_desc, self.v_valor, self.v_doc, self.v_nota, self.v_quit, self.v_forn, self.v_sub):
            v.set("")
        self.v_tipo.set(next(iter(self.mapa_tipo), ""))
        self.v_entrada.set(fmt.fmt_data(fmt.hoje()))
        self.v_venc.set(fmt.fmt_data(fmt.hoje()))
        self.v_merc.set(False); self.v_prev.set(False); self.v_meses.set("1")
        self.sp_meses.configure(state="normal")
        self.cb_sub.focus_set()

    def _selecionou(self, _=None) -> None:
        s = self.grade.selecionado()
        if s is None:
            return
        c = self.ctx.contas.obter(int(s))
        self.id_atual = c["id"]
        self.v_sub.set(f"{c['subplano']} - {c['plano']}")
        self.v_desc.set(c["descricao"]); self.v_valor.set(fmt.fmt_num(c["valor_cent"])); self.v_doc.set(c["documento"] or "")
        self.v_nota.set(c["nota"] or ""); self.v_tipo.set(c["tipo_financeiro"]); self.v_forn.set(c["fornecedor"] or "")
        self.v_entrada.set(fmt.fmt_data(c["dt_entrada"])); self.v_venc.set(fmt.fmt_data(c["dt_vencimento"]))
        self.v_quit.set(fmt.fmt_data(c["dt_quitacao"]))
        self.v_merc.set(bool(c["mercadoria"])); self.v_prev.set(bool(c["previsao"]))
        self.sp_meses.configure(state="disabled")

    def gravar(self) -> None:
        sub = self.mapa_sub.get(self.v_sub.get())
        tipo = self.mapa_tipo.get(self.v_tipo.get())
        if not sub or not tipo:
            tema.aviso(self, "Escolha o sub plano e o tipo financeiro.")
            return
        try:
            valor = fmt.para_centavos(self.v_valor.get())
            meses = int(self.v_meses.get() or 1)
        except ValueError:
            tema.aviso(self, "Valor ou número de meses inválido.")
            return
        dados = dict(descricao=self.v_desc.get(), tipo_pagamento_id=tipo, valor_cent=valor, documento=self.v_doc.get() or None,
                     nota=self.v_nota.get() or None, mercadoria=int(self.v_merc.get()), previsao=int(self.v_prev.get()),
                     fornecedor_id=self.mapa_forn.get(self.v_forn.get()), dt_entrada=self.v_entrada.get(),
                     dt_vencimento=self.v_venc.get(), dt_quitacao=self.v_quit.get())
        if self.id_atual:
            ok, _ = tema.tratar(self, self.ctx.contas.atualizar, self.id_atual, subplano_id=sub, **dados)
            alvo = self.id_atual
        else:
            ok, ids = tema.tratar(self, self.ctx.contas.incluir, sub, dados["descricao"], tipo, valor, dados["dt_vencimento"],
                                  dados["dt_entrada"], dados["dt_quitacao"] or None, dados["documento"], bool(dados["mercadoria"]),
                                  dados["nota"], bool(dados["previsao"]), dados["fornecedor_id"], meses)
            alvo = ids[0] if ok else None
        if ok:
            era_edicao = bool(self.id_atual)
            self.listar(alvo)
            if not era_edicao:
                self.novo()          # inclusão: limpa o formulário para o próximo lançamento

    def cancelar(self) -> None:
        self._selecionou() if self.id_atual else self.novo()

    def excluir(self) -> None:
        if self.id_atual and tema.confirmar(self, "Excluir esta conta?", "Excluir", padrao_sim=False):
            ok, _ = tema.tratar(self, self.ctx.contas.excluir, self.id_atual)
            if ok:
                self.listar()
                self.novo()

    def quitar(self) -> None:
        if not self.id_atual:
            return
        d = tema.pedir_texto(self, "Quitar", "Data da quitação (dd/mm/aaaa):", fmt.fmt_data(fmt.hoje()))
        if d is not None:
            ok, _ = tema.tratar(self, self.ctx.contas.quitar, self.id_atual, d)
            if ok:
                self.listar(self.id_atual)

    def desquitar(self) -> None:
        if self.id_atual:
            self.ctx.contas.desfazer_quitacao(self.id_atual)
            self.listar(self.id_atual)


class JanelaEstoque(tk.Toplevel):
    ORDEM = ["compra", "entrada", "saida", "descarte", "contagem", "inicial", "pedido", "desc_acabados"]

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx, self.est = ctx, ctx.estoque
        self.lanc_id: int | None = None
        self.produto: dict | None = None
        self.title("Lançamento de Estoques")
        self.configure(bg=tema.COR["fundo"])
        self.geometry("1100x740")
        self.v_tipo = tk.StringVar(value="compra")
        self._montar()
        self.bind("<Escape>", lambda e: self.destroy())
        self.novo()
        self.transient(master.winfo_toplevel())

    def _montar(self) -> None:
        b = tk.Frame(self, bg=tema.COR["marinho"], padx=6, pady=5)
        b.pack(fill="x")
        for rotulo, cmd in (("Novo lançamento", self.novo), ("Abrir anterior...", self.abrir_anterior), ("Excluir lançamento", self.excluir),
                            ("Imprimir", self.imprimir)):
            ttk.Button(b, text=rotulo, style="Barra.TButton", command=cmd).pack(side="left", padx=2)
        ttk.Button(b, text="Sair", style="Barra.TButton", command=self.destroy).pack(side="right")

        tipos = ttk.LabelFrame(self, text="Tipo de movimentação de estoque", padding=8)
        tipos.pack(fill="x", padx=10, pady=(8, 0))
        for t in self.ORDEM:
            ttk.Radiobutton(tipos, text=TIPOS[t], value=t, variable=self.v_tipo, command=self._tipo_mudou).pack(side="left", padx=8)

        cab = ttk.LabelFrame(self, text="Lançamento", padding=8)
        cab.pack(fill="x", padx=10, pady=8)
        forn = self.ctx.cadastros.opcoes("fornecedores")
        self.mapa_forn = {r: i for i, r in forn}
        self.v_forn, self.v_desc, self.v_data, self.v_valor, self.v_doc, self.v_nf = (tk.StringVar() for _ in range(6))
        self.cb_forn = _campo(cab, "Fornecedor", lambda p: ttk.Combobox(p, textvariable=self.v_forn, values=[r for _, r in forn], state="readonly", width=28), 0, 0)
        _campo(cab, "Descrição", lambda p: ttk.Entry(p, textvariable=self.v_desc, width=30), 0, 1)
        _campo(cab, "Data", lambda p: ttk.Entry(p, textvariable=self.v_data, width=12), 0, 2)
        self.e_valor = _campo(cab, "Valor da nota", lambda p: ttk.Entry(p, textvariable=self.v_valor, width=14), 1, 0)
        _campo(cab, "Documento", lambda p: ttk.Entry(p, textvariable=self.v_doc, width=20), 1, 1)
        _campo(cab, "Nota fiscal", lambda p: ttk.Entry(p, textvariable=self.v_nf, width=14), 1, 2)
        self.lbl_total = ttk.Label(cab, text="", font=tema.FONTE_B, foreground=tema.COR["marinho2"])
        self.lbl_total.grid(row=0, column=3, rowspan=2, padx=20)
        self.btn_lancar = ttk.Button(cab, text="Lançar itens (Enter)", style="Ok.TButton", command=self.iniciar)
        self.btn_lancar.grid(row=0, column=4, padx=6)
        self.btn_contas = ttk.Button(cab, text="Contas a pagar", command=self.contas_a_pagar)
        self.btn_contas.grid(row=1, column=4, padx=6)
        self.btn_confirma = ttk.Button(cab, text="Confirmar entrega do pedido", command=self.confirmar_entrega)
        self.btn_confirma.grid(row=1, column=3, padx=6)

        self.painel_item = ttk.LabelFrame(self, text="Lançamento de itens", padding=8)
        self.painel_item.pack(fill="x", padx=10)
        self.v_cod, self.v_prod, self.v_qtd, self.v_desc_item, self.v_val_item, self.v_min = (tk.StringVar() for _ in range(6))
        self.e_cod = _campo(self.painel_item, "Código", lambda p: ttk.Entry(p, textvariable=self.v_cod, width=16), 0, 0)
        nomes = [r["nome"] for r in self.ctx.cadastros.listar("produtos", apenas_ativos=True)]
        self.cb_prod = _campo(self.painel_item, "Produto", lambda p: ttk.Combobox(p, textvariable=self.v_prod, values=nomes, width=36), 0, 1)
        self.e_qtd = _campo(self.painel_item, "Quantidade", lambda p: ttk.Entry(p, textvariable=self.v_qtd, width=12), 0, 2)
        self.e_desc_item = _campo(self.painel_item, "Desconto", lambda p: ttk.Entry(p, textvariable=self.v_desc_item, width=10), 0, 3)
        self.e_val_item = _campo(self.painel_item, "Valor (total do item)", lambda p: ttk.Entry(p, textvariable=self.v_val_item, width=12), 0, 4)
        self.e_min = _campo(self.painel_item, "Est. mínimo", lambda p: ttk.Entry(p, textvariable=self.v_min, width=10), 0, 5)
        self.lbl_atual = ttk.Label(self.painel_item, text="", foreground=tema.COR["suave"])
        self.lbl_atual.grid(row=1, column=0, columnspan=5, sticky="w")
        bb = ttk.Frame(self.painel_item)
        bb.grid(row=1, column=5, sticky="e")
        ttk.Button(bb, text="Confirmar item (Enter)", style="Ok.TButton", command=self.adicionar_item).pack(side="left")
        ttk.Button(bb, text="Limpar", command=self._limpar_item).pack(side="left", padx=6)

        q = ttk.Frame(self, padding=10)
        q.pack(fill="both", expand=True)
        self.grade = tema.Grade(q, [("cod", "Código", 110, "w"), ("prod", "Produto", 280, "w"), ("un", "Unidade", 70, "w"),
                                    ("qtd", "Quantidade", 90, "e"), ("unit", "Pr. unitário", 90, "e"), ("desc", "Desconto", 80, "e"),
                                    ("valor", "Valor", 90, "e"), ("dif", "Diferença", 90, "e")], altura=9)
        self.grade.pack(fill="both", expand=True)
        ttk.Label(q, text="Para excluir um item, selecione-o e tecle Enter ou Delete. Para excluir o lançamento inteiro use 'Excluir lançamento'.",
                  foreground=tema.COR["suave"]).pack(anchor="w", pady=(4, 0))
        self.grade.tree.bind("<Return>", lambda e: (self.remover_item(), "break")[1])
        self.grade.tree.bind("<Delete>", lambda e: self.remover_item())
        self.e_cod.bind("<Return>", lambda e: self._achar_codigo())
        self.cb_prod.bind("<<ComboboxSelected>>", lambda e: self._achar_nome())
        for w in (self.e_qtd, self.e_desc_item, self.e_val_item, self.e_min):
            w.bind("<Return>", lambda e: self.adicionar_item())

    # -------------------------------------------------------------- estado
    def _tipo_mudou(self) -> None:
        t = self.v_tipo.get()
        usa_forn = t in ("compra", "pedido")
        self.cb_forn.configure(state="readonly" if usa_forn else "disabled")
        self.e_valor.configure(state="normal" if t == "compra" else "disabled")
        self.btn_contas.configure(state="normal" if t in ("compra", "pedido") else "disabled")
        self.btn_confirma.configure(state="normal" if t == "pedido" and self.lanc_id else "disabled")
        self.e_val_item.configure(state="normal" if t == "compra" else "disabled")
        self.e_desc_item.configure(state="normal" if t == "compra" else "disabled")
        self.e_min.configure(state="normal" if t == "inicial" else "disabled")
        if not self.lanc_id:
            self.v_desc.set(TIPOS[t])

    def novo(self) -> None:
        self.lanc_id = None
        self.v_tipo.set(self.v_tipo.get() or "compra")
        for v in (self.v_forn, self.v_valor, self.v_doc, self.v_nf):
            v.set("")
        self.v_data.set(fmt.fmt_data(fmt.hoje()))
        self._tipo_mudou()
        self._estado_header(editavel=True)
        self.grade.limpar()
        self.lbl_total.configure(text="")
        self._limpar_item()
        self.cb_forn.focus_set()

    def _estado_header(self, editavel: bool) -> None:
        self.btn_lancar.configure(state="normal" if editavel else "disabled")
        for w in self.painel_item.winfo_children():
            self._set_estado(w, "disabled" if editavel else "normal")
        if not editavel:
            self._tipo_mudou()
            self.e_cod.focus_set()

    def _set_estado(self, w, estado) -> None:
        for f in w.winfo_children() if isinstance(w, ttk.Frame) else [w]:
            if isinstance(f, (ttk.Entry, ttk.Combobox, ttk.Button)):
                try:
                    f.configure(state=estado)
                except tk.TclError:
                    pass
            elif isinstance(f, ttk.Frame):
                self._set_estado(f, estado)

    def iniciar(self) -> None:
        t = self.v_tipo.get()
        try:
            valor = fmt.para_centavos(self.v_valor.get()) if t == "compra" else 0
        except ValueError:
            tema.aviso(self, "Valor da nota inválido.")
            return
        ok, lid = tema.tratar(self, self.est.criar_lancamento, t, self.v_data.get(), self.v_desc.get(), self.v_doc.get() or None,
                              self.v_nf.get() or None, self.mapa_forn.get(self.v_forn.get()), valor)
        if ok:
            self.lanc_id = lid
            self._estado_header(editavel=False)
            self.atualizar()

    def abrir_anterior(self) -> None:
        lancs = self.est.lancamentos()[:300]
        itens = [(l["id"], (fmt.fmt_data(l["data"]), TIPOS[l["tipo"]], l["fornecedor"] or "", l["documento"] or "", fmt.fmt_num(l["total_itens"])))
                 for l in lancs]
        cols = [("d", "Data", 90, "w"), ("t", "Tipo", 190, "w"), ("f", "Fornecedor", 150, "w"), ("doc", "Documento", 100, "w"), ("v", "Total", 90, "e")]
        lid = tema.escolher(self, "Lançamentos de estoque", itens, "Filtrar por texto:", colunas=cols, altura=14)
        if lid:
            l = self.est.lancamento(lid)
            self.lanc_id = lid
            self.v_tipo.set(l["tipo"]); self.v_forn.set(l["fornecedor"] or ""); self.v_desc.set(l["descricao"] or "")
            self.v_data.set(fmt.fmt_data(l["data"])); self.v_valor.set(fmt.fmt_num(l["valor_cent"])); self.v_doc.set(l["documento"] or "")
            self.v_nf.set(l["nota_fiscal"] or "")
            self._estado_header(editavel=False)
            self.atualizar()

    def atualizar(self) -> None:
        itens = self.est.itens(self.lanc_id)
        self.grade.preencher([[i["codigo"], i["nome"], i["unidade"], fmt.fmt_qtd(i["quantidade"]), fmt.fmt_num(i["preco_unit_cent"]),
                               fmt.fmt_num(i["desconto_cent"]), fmt.fmt_num(i["valor_cent"]), fmt.fmt_qtd(i["diferenca"])] for i in itens],
                             [i["id"] for i in itens])
        total = self.est.total_itens(self.lanc_id)
        self.lbl_total.configure(text=f"Total dos itens lançados\n{fmt.fmt_brl(total)}")
        self.grade.tree.yview_moveto(1.0)

    # ---------------------------------------------------------------- itens
    def _limpar_item(self) -> None:
        self.produto = None
        for v in (self.v_cod, self.v_prod, self.v_qtd, self.v_desc_item, self.v_val_item, self.v_min):
            v.set("")
        self.lbl_atual.configure(text="")

    def _carregar_produto(self, p: dict | None) -> None:
        if p is None:
            tema.aviso(self, "Produto não encontrado.")
            return
        self.produto = p
        self.v_cod.set(p["codigo"]); self.v_prod.set(p["nome"])
        self.lbl_atual.configure(text=f"Qt. atual: {fmt.fmt_qtd(p['qt_atual'])}    Último preço: {fmt.fmt_brl(p['ult_preco_cent'])}")
        if self.v_tipo.get() == "inicial":
            self.v_min.set(fmt.fmt_qtd(p["estoque_minimo"]))
        self.e_qtd.focus_set()

    def _achar_codigo(self) -> None:
        self._carregar_produto(self.ctx.produtos.buscar_codigo(self.v_cod.get(), apenas_venda=False))

    def _achar_nome(self) -> None:
        nome = self.v_prod.get()
        p = next((r for r in self.ctx.cadastros.listar("produtos", texto=nome) if r["nome"] == nome), None)
        self._carregar_produto(p)

    def adicionar_item(self) -> None:
        if self.lanc_id is None:
            return
        if self.produto is None:
            self._achar_codigo() if self.v_cod.get() else self._achar_nome()
            if self.produto is None:
                return
        try:
            qtd = fmt.para_qtd(self.v_qtd.get())
            valor = fmt.para_centavos(self.v_val_item.get()) if self.v_val_item.get() else 0
            desc = fmt.para_centavos(self.v_desc_item.get()) if self.v_desc_item.get() else 0
            minimo = fmt.para_qtd(self.v_min.get()) if self.v_min.get().strip() else None
        except ValueError:
            tema.aviso(self, "Quantidade ou valor inválido.")
            return
        ok, _ = tema.tratar(self, self.est.adicionar_item, self.lanc_id, self.produto["id"], qtd, valor, desc, minimo)
        if ok:
            self._limpar_item()
            self.atualizar()
            self.e_cod.focus_set()

    def remover_item(self) -> None:
        s = self.grade.selecionado()
        if s is not None and tema.confirmar(self, "Excluir o item selecionado (o estoque volta ao que era)?", "Excluir item", padrao_sim=False):
            ok, _ = tema.tratar(self, self.est.remover_item, int(s))
            if ok:
                self.atualizar()

    def excluir(self) -> None:
        if self.lanc_id and tema.confirmar(self, "Excluir o lançamento inteiro? O efeito no estoque será desfeito.", "Excluir", padrao_sim=False):
            ok, _ = tema.tratar(self, self.est.excluir_lancamento, self.lanc_id)
            if ok:
                self.novo()

    def contas_a_pagar(self) -> None:
        if not self.lanc_id:
            tema.aviso(self, "Lance os itens antes de gerar a conta a pagar.")
            return
        d = tema.pedir_texto(self, "Contas a pagar", "Vencimento (dd/mm/aaaa):", fmt.fmt_data(fmt.hoje()))
        if d is None:
            return
        tipos = self.ctx.cadastros.opcoes("tipos_pagamento")
        tipo = tema.escolher(self, "Tipo financeiro", tipos, "Como será paga a conta?")
        if tipo is None:
            return
        ok, ids = tema.tratar(self, self.ctx.contas.criar_da_compra, self.lanc_id, d, tipo)
        if ok:
            tema.mensagem(self, "Conta a pagar lançada (Lançamentos > Contas).", "Contas a pagar")

    def confirmar_entrega(self) -> None:
        itens = self.est.itens(self.lanc_id)
        valores = {}
        for it in itens:
            v = tema.pedir_dinheiro(self, "Confirmar entrega", f"Valor total de '{it['nome']}' ({fmt.fmt_qtd(it['quantidade'])}):",
                                    it["valor_cent"], permitir_zero=True)
            if v is None:
                return
            valores[it["id"]] = v
        if tema.confirmar(self, "Confirmar a entrega? Depois disso o pedido vira COMPRA e não pode ser alterado.", "Confirmar entrega"):
            ok, _ = tema.tratar(self, self.est.confirmar_pedido, self.lanc_id, valores)
            if ok:
                self.v_tipo.set("compra")
                self._tipo_mudou()
                self.atualizar()

    def imprimir(self) -> None:
        if not self.lanc_id:
            return
        l = self.est.lancamento(self.lanc_id)
        linhas = [f"{TIPOS[l['tipo']].upper()} - {fmt.fmt_data(l['data'])}", f"Fornecedor: {l['fornecedor'] or '-'}   Doc: {l['documento'] or '-'}", "-" * 70]
        for i in self.est.itens(self.lanc_id):
            linhas.append(f"{i['codigo']} {i['nome'][:30]:<30} {fmt.fmt_qtd(i['quantidade']):>10} {fmt.fmt_num(i['valor_cent']):>12}")
        linhas += ["-" * 70, f"Total dos itens: {fmt.fmt_num(self.est.total_itens(self.lanc_id))}"]
        Visualizador(self, self.ctx, "Lançamento de estoque", "\n".join(linhas), f"estoque_{self.lanc_id}")
