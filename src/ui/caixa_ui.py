"""Tela do Caixa (manual do Caixa). Operação por teclado:

  código + Enter -> quantidade + Enter     Enter com código vazio -> barra de tarefas (setas + Enter)
  Esc -> painel de mesas                    Delete na grade -> cancela item        O -> observação do item
  F2 balança  F3 leitor  F4 mesa  F5 caderneta  F6 entrega  F7 sangria  F8 pré-conta  F9 repique
  F10 transferir  F11 gaveta  F12 pagar
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.core import formatacao as fmt
from src.core.erros import ErroNegocio
from src.hardware.dispositivos import DispositivoIndisponivel
from src.ui import caixa_dialogos, tema
from src.ui.caixa_pagamento import JanelaPagamento
from src.ui.clientes_ui import JanelaClientes, JanelaEntregas
from src.ui.visualizador import Visualizador


class JanelaCaixa(tk.Toplevel):
    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx
        self.venda_id: int | None = None
        self.produto: dict | None = None
        self.modo_cancelar = False
        self.mesas_visiveis = False
        self.indice_barra: int | None = None
        self.leitor = bool(ctx.config.maquina()["leitor_optico"])
        self.title(f"Caixa - {ctx.config.nome_loja()}")
        self.configure(bg=tema.COR["fundo"])
        self.geometry("1180x740")
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self.sair)
        self.withdraw()
        if ctx.turnos.atual() is None and not caixa_dialogos.abrir_turno(self, ctx):
            self.destroy()
            return
        self._montar()
        self.venda_id = ctx.banco.valor(   # retoma a venda de balcão interrompida (queda de energia, saída do caixa)
            "SELECT id FROM vendas WHERE modalidade = 'balcao' AND status = 'aberta' ORDER BY id DESC LIMIT 1")
        self.deiconify()
        self.lift()
        self.focus_force()
        self.recarregar()
        self.ent_codigo.focus_set()
        self._relogio()

    # ================================================================ layout
    def _montar(self) -> None:
        topo = tk.Frame(self, bg=tema.COR["marinho"], padx=12, pady=6)
        topo.pack(fill="x")
        self.lbl_loja = tk.Label(topo, text=self.ctx.config.nome_loja().upper(), bg=tema.COR["marinho"], fg="white", font=tema.FONTE_G)
        self.lbl_loja.pack(side="left")
        self.lbl_turno = tk.Label(topo, bg=tema.COR["marinho"], fg="#c9d6ff", font=tema.FONTE)
        self.lbl_turno.pack(side="right")
        self.lbl_hora = tk.Label(topo, bg=tema.COR["marinho"], fg="white", font=tema.FONTE_B)
        self.lbl_hora.pack(side="right", padx=20)

        meio = ttk.Frame(self, padding=(12, 8, 12, 0))
        meio.pack(fill="x")
        esq = ttk.Frame(meio)
        esq.pack(side="left", fill="y")
        ttk.Label(esq, text="Posição (mesa)", style="Rotulo.TLabel").pack(anchor="w")
        self.var_pos = tk.StringVar(value="0")
        self.ent_pos = ttk.Entry(esq, textvariable=self.var_pos, width=8, font=("Segoe UI", 16, "bold"), justify="center")
        self.ent_pos.pack(anchor="w")
        self.lbl_situacao = ttk.Label(esq, text="Balcão", font=tema.FONTE_B, foreground=tema.COR["marinho2"])
        self.lbl_situacao.pack(anchor="w", pady=(4, 0))
        self.lbl_leitor = ttk.Label(esq, text="", foreground=tema.COR["aviso"], font=tema.FONTE_B)
        self.lbl_leitor.pack(anchor="w")

        dir_ = tk.Frame(meio, bg="white", bd=1, relief="solid", padx=16, pady=4)
        dir_.pack(side="right")
        tk.Label(dir_, text="Total:", bg="white", fg=tema.COR["marinho"], font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        self.lbl_total = tk.Label(dir_, text="0,00", bg="white", fg=tema.COR["total"], font=("Georgia", 44, "bold"), width=9, anchor="e")
        self.lbl_total.grid(row=0, column=1, sticky="e")
        tk.Label(dir_, text="Troco:", bg="white", fg=tema.COR["marinho"], font=("Segoe UI", 13, "bold")).grid(row=1, column=0, sticky="w")
        self.lbl_troco = tk.Label(dir_, text="0,00", bg="white", fg=tema.COR["troco"], font=("Georgia", 20, "bold"), anchor="e")
        self.lbl_troco.grid(row=1, column=1, sticky="e")

        self.faixa = tk.Label(self, text="", font=tema.FONTE_B, fg="white", anchor="w", padx=14, pady=4)
        self.barra = ttk.Frame(self, padding=(12, 8, 12, 0))
        self.barra.pack(fill="x")
        self._barra_tarefas()

        ent = ttk.Frame(self, padding=(12, 8, 12, 0))
        ent.pack(fill="x")
        ttk.Label(ent, text="Código", style="Rotulo.TLabel").grid(row=0, column=0, sticky="w")
        self.var_cod = tk.StringVar()
        self.ent_codigo = ttk.Entry(ent, textvariable=self.var_cod, width=18, font=("Segoe UI", 14))
        self.ent_codigo.grid(row=1, column=0, sticky="w")
        ttk.Button(ent, text="Consultar", command=self.consultar).grid(row=1, column=1, padx=8)
        ttk.Label(ent, text="Descrição", style="Rotulo.TLabel").grid(row=0, column=2, sticky="w")
        self.lbl_desc = ttk.Label(ent, text="", font=("Segoe UI", 14, "bold"), foreground=tema.COR["marinho"], width=36)
        self.lbl_desc.grid(row=1, column=2, sticky="w", padx=(0, 10))
        ttk.Label(ent, text="Unidade", style="Rotulo.TLabel").grid(row=0, column=3, sticky="w")
        self.lbl_un = ttk.Label(ent, text="", font=("Segoe UI", 12), width=6)
        self.lbl_un.grid(row=1, column=3, sticky="w")
        ttk.Label(ent, text="Quantidade", style="Rotulo.TLabel").grid(row=0, column=4, sticky="w")
        self.var_qtd = tk.StringVar()
        self.ent_qtd = ttk.Entry(ent, textvariable=self.var_qtd, width=10, font=("Segoe UI", 14), state="disabled")
        self.ent_qtd.grid(row=1, column=4, sticky="w", padx=(0, 10))
        ttk.Label(ent, text="Preço", style="Rotulo.TLabel").grid(row=0, column=5, sticky="w")
        self.lbl_preco = ttk.Label(ent, text="", font=("Segoe UI", 14, "bold"), width=10)
        self.lbl_preco.grid(row=1, column=5, sticky="w")

        corpo = ttk.Frame(self, padding=12)
        corpo.pack(fill="both", expand=True)
        self.painel_mesas = ttk.LabelFrame(corpo, text="Mesas abertas", padding=8)
        self.grade_mesas = tema.Grade(self.painel_mesas, [("pos", "Mesa", 60, "center"), ("sit", "Situação", 130, "w"),
                                                           ("tot", "Total", 90, "e")], altura=14)
        self.grade_mesas.pack(fill="both", expand=True)
        ttk.Label(self.painel_mesas, text="Enter chama a mesa; T transfere outras para ela", wraplength=210, foreground=tema.COR["suave"]).pack(anchor="w", pady=(6, 0))
        self.grade_mesas.tag("enviada", foreground=tema.COR["aviso"])
        self.grade_mesas.tag("parada", foreground=tema.COR["perigo"])
        self.grade = tema.Grade(corpo, [("cod", "Código", 120, "w"), ("prod", "Produto", 330, "w"), ("un", "Un", 50, "w"),
                                        ("preco", "Preço", 90, "e"), ("qtd", "Quantidade", 90, "e"), ("tot", "Total", 100, "e"),
                                        ("obs", "Observação", 200, "w")], altura=14)
        self.grade.pack(side="left", fill="both", expand=True)
        self.status = ttk.Label(self, text="", foreground=tema.COR["suave"], padding=(12, 3))
        self.status.pack(fill="x", side="bottom")

        e = self.ent_codigo
        e.bind("<Return>", self._enter_codigo)
        e.bind("<Escape>", self._esc_codigo)
        e.bind("<Down>", lambda ev: self._foco_grade())
        self.ent_qtd.bind("<Return>", lambda ev: self.confirmar_item())
        self.ent_qtd.bind("<Escape>", lambda ev: self.cancelar_item_pendente())
        self.ent_pos.bind("<Return>", lambda ev: self.chamar_mesa())
        self.ent_pos.bind("<Escape>", lambda ev: self.ent_codigo.focus_set())
        t = self.grade.tree
        t.bind("<Delete>", lambda ev: self.cancelar_item_selecionado())
        t.bind("<Return>", self._enter_grade)
        t.bind("<Escape>", lambda ev: self._sair_modo_cancelar())
        t.bind("o", lambda ev: self.observacao_item()); t.bind("O", lambda ev: self.observacao_item())
        t.bind("t", lambda ev: self.transferir_item()); t.bind("T", lambda ev: self.transferir_item())
        gm = self.grade_mesas.tree
        gm.bind("<Return>", self._mesa_escolhida)
        gm.bind("<Double-1>", self._mesa_escolhida)
        gm.bind("t", lambda ev: self.transferir_varias()); gm.bind("T", lambda ev: self.transferir_varias())
        gm.bind("<Escape>", lambda ev: self.alternar_mesas(False))
        for tecla, fn in (("F1", self.f1), ("F2", self.balanca), ("F3", self.alternar_leitor), ("F4", self.foco_mesa), ("F5", self.caderneta),
                          ("F6", self.entrega), ("F7", self.sangria), ("F8", self.pre_conta), ("F9", self.repique),
                          ("F10", self.transferir_mesa), ("F11", self.gaveta), ("F12", self.pagar)):
            self.bind(f"<{tecla}>", lambda ev, f=fn: (f(), "break")[1])
        self.bind("<Left>", lambda ev: self._barra_mover(-1))
        self.bind("<Right>", lambda ev: self._barra_mover(1))

    def _barra_tarefas(self) -> None:
        self.tarefas = [("Pagar (F12)", self.pagar), ("Cancelar", self.menu_cancelar), ("Consultar", self.consultar),
                        ("Mesa (F4)", self.foco_mesa), ("Pré-Conta (F8)", self.pre_conta), ("Transfere (F10)", self.transferir_mesa),
                        ("Repique (F9)", self.repique), ("Sangria (F7)", self.sangria), ("Delivery (F6)", self.entrega),
                        ("Caderneta (F5)", self.caderneta), ("Impressora", self.impressora), ("Gaveta (F11)", self.gaveta),
                        ("Balança (F2)", self.balanca), ("Fecha Turno", self.fechar_turno), ("Leitor (F3)", self.alternar_leitor),
                        ("Sair", self.sair)]
        self.botoes_tarefa = []
        for i, (rotulo, fn) in enumerate(self.tarefas):
            b = ttk.Button(self.barra, text=rotulo, style="Barra.TButton", takefocus=False, command=lambda f=fn: self._exec_barra(f))
            b.grid(row=i // 8, column=i % 8, padx=2, pady=2, sticky="ew")
            self.botoes_tarefa.append(b)
        for c in range(8):
            self.barra.columnconfigure(c, weight=1)

    # ============================================================== estado
    def _relogio(self) -> None:
        try:
            self.lbl_hora.configure(text=fmt.agora_dt().strftime("%d/%m/%Y  %H:%M:%S"))
            self._id_relogio = self.after(1000, self._relogio)
        except tk.TclError:      # janela já destruída
            pass

    def destroy(self) -> None:
        try:
            self.after_cancel(self._id_relogio)
        except (AttributeError, tk.TclError, ValueError):
            pass
        super().destroy()

    def avisar(self, texto: str, cor: str | None = None) -> None:
        self.status.configure(text=texto, foreground=cor or tema.COR["suave"])

    def venda(self) -> dict | None:
        return self.ctx.caixa.obter(self.venda_id) if self.venda_id else None

    def recarregar(self) -> None:
        t = self.ctx.turnos.atual()
        self.lbl_turno.configure(text=f"Operador: {self.ctx.operador.nome}    Turno: {t['numero'] if t else '-'}")
        v = self.venda()
        self.grade.limpar()
        total = 0
        if v:
            for it in self.ctx.caixa.itens(v["id"]):
                nome = it["nome"] + (f"  [{' / '.join(it['partes_nomes'])}]" if it["partes_nomes"] else "")
                self.grade.adicionar([it["codigo"], nome, it["unidade"], fmt.fmt_num(it["preco_unit_cent"]),
                                      fmt.fmt_qtd(it["quantidade"]), fmt.fmt_num(it["total_cent"]), it["observacao"] or ""], iid=it["id"])
            total = v["total_cent"]
            self.grade.tree.yview_moveto(1.0)
        self.lbl_total.configure(text=fmt.fmt_num(total))
        self.lbl_troco.configure(text="0,00")
        self._situacao(v)
        self.lbl_leitor.configure(text="LEITOR ÓPTICO ATIVO" if self.leitor else "")
        if self.mesas_visiveis:
            self.carregar_mesas()

    def _situacao(self, v: dict | None) -> None:
        if v is None:
            self.lbl_situacao.configure(text="Balcão")
            self.var_pos.set("0")
            self.faixa.pack_forget()
            return
        mod = v["modalidade"]
        if mod == "mesa":
            self.lbl_situacao.configure(text=f"Mesa {v['posicao']}" + (" - CONTA ENVIADA" if v["status"] == "conta_enviada" else ""))
            self.var_pos.set(str(v["posicao"]))
        else:
            self.lbl_situacao.configure(text={"balcao": "Balcão", "caderneta": "Caderneta", "entrega": f"Entrega {v['posicao']}"}[mod])
            self.var_pos.set("0")
        if mod in ("caderneta", "entrega") and v["cliente_id"]:
            c = self.ctx.caderneta.obter(v["cliente_id"])
            if mod == "caderneta":
                txt = (f"CADERNETA   {c['numero_consulta']}  {c['nome']}      Limite {fmt.fmt_num(c['limite_cent'])}"
                       f"      Saldo {fmt.fmt_num(c['saldo_cent'])}")
                cor = "#b32020"
            else:
                txt = (f"ENTREGA #{v['posicao']}   {c['numero_consulta']}  {c['nome']}   {c['endereco'] or ''}   "
                       f"Taxa {fmt.fmt_num(v['taxa_cent'])}")
                cor = "#1f5fb3"
            self.faixa.configure(text=txt, bg=cor)
            self.faixa.pack(fill="x", before=self.barra)
        else:
            self.faixa.pack_forget()

    # =============================================================== itens
    def _enter_codigo(self, _=None) -> str:
        if self.indice_barra is not None:
            return self._barra_enter()
        texto = self.var_cod.get().strip()
        if not texto:
            self._entrar_barra()
            return "break"
        self.resolver_codigo(texto)
        return "break"

    def _esc_codigo(self, _=None) -> str:
        if self.indice_barra is not None:
            return self._barra_esc()
        if self.produto is not None:
            self.cancelar_item_pendente()
        else:
            self.alternar_mesas()
        return "break"

    def resolver_codigo(self, texto: str) -> None:
        p = self.ctx.produtos.buscar_codigo(texto)
        if p is None and not texto.isdigit():
            achados = self.ctx.produtos.pesquisar(texto)
            if len(achados) == 1:
                p = achados[0]
            elif achados:
                p = self._escolher_produto(achados, texto)
                if p is None:
                    return
        if p is None:
            self.bell()
            self.avisar(f"Produto '{texto}' não encontrado.", tema.COR["perigo"])
            self.var_cod.set("")
            return
        self.selecionar_produto(p)

    def consultar(self) -> None:
        achados = self.ctx.produtos.pesquisar(self.var_cod.get().strip(), limite=500)
        p = self._escolher_produto(achados, self.var_cod.get().strip())
        if p is not None:
            self.selecionar_produto(p)
        else:
            self.ent_codigo.focus_set()

    def _escolher_produto(self, produtos: list[dict], texto: str = "") -> dict | None:
        itens = [(p["id"], (p["codigo"], p["nome"], fmt.fmt_num(self.ctx.produtos.preco_vigente(p)),
                            fmt.fmt_qtd(p["qt_atual"]) if p["controla_estoque"] else "")) for p in produtos]
        cols = [("cod", "Código", 110, "w"), ("nome", "Produto", 280, "w"), ("preco", "Preço", 80, "e"), ("qt", "Estoque", 80, "e")]
        pid = tema.escolher(self, "Consulta de produtos", itens, "Digite parte do nome para filtrar:", colunas=cols, altura=14)
        return self.ctx.produtos.por_id(pid) if pid else None

    def selecionar_produto(self, p: dict) -> None:
        if self.venda_id and self.venda() and self.venda()["modalidade"] == "caderneta" and not self.venda()["cliente_id"]:
            tema.aviso(self, "Escolha o cliente da caderneta (F5).")
            return
        self.produto = p
        preco = self.ctx.produtos.preco_vigente(p)
        un = self.ctx.banco.valor("SELECT abreviatura FROM unidades WHERE id = ?", (p["unidade_id"],), "")
        self.lbl_desc.configure(text=p["nome"])
        self.lbl_un.configure(text=un)
        self.lbl_preco.configure(text=fmt.fmt_num(preco))
        self.var_cod.set(p["codigo"])
        if self.leitor and not p["aceita_decimal"] and p["partes"] <= 1:
            self.var_qtd.set("1")
            self.confirmar_item()
            return
        self.ent_qtd.configure(state="normal")
        self.var_qtd.set("1")
        self.ent_qtd.focus_set()
        self.ent_qtd.selection_range(0, "end")

    def f1(self) -> None:
        """Na entrega libera o troco (manual do Caixa); nas demais telas abre a consulta de produtos."""
        v = self.venda()
        if v and v["modalidade"] == "entrega":
            self.liberar_troco()
        else:
            self.consultar()

    def cancelar_item_pendente(self) -> None:
        self._limpar_entrada()
        self.ent_codigo.focus_set()

    def _limpar_entrada(self) -> None:
        self.produto = None
        self.var_cod.set("")
        self.var_qtd.set("")
        self.ent_qtd.configure(state="disabled")
        for lbl in (self.lbl_desc, self.lbl_un, self.lbl_preco):
            lbl.configure(text="")

    def confirmar_item(self) -> None:
        p = self.produto
        if p is None:
            return
        try:
            qtd = fmt.para_qtd(self.var_qtd.get())
        except ValueError:
            self.avisar("Quantidade inválida.", tema.COR["perigo"])
            return
        partes = None
        if p["partes"] > 1 and (p["composto"] or self.ctx.banco.valor("SELECT COUNT(*) FROM produtos WHERE montagem = 1 AND ativo = 1")):
            partes = caixa_dialogos.dialogo_partes(self, self.ctx, p)
            if partes is None:
                return
        ok, item_id = tema.tratar(self, self._lancar, p["id"], qtd, partes or None)
        if not ok:
            self.ent_qtd.focus_set()
            return
        self.avisar(f"{fmt.fmt_qtd(qtd)} x {p['nome']} lançado.", tema.COR["ok"])
        self._limpar_entrada()
        self.recarregar()
        self.ent_codigo.focus_set()

    def _lancar(self, produto_id: int, qtd: float, partes: list[int] | None) -> int:
        caixa = self.ctx.caixa
        if self.venda_id is None:
            self.venda_id = caixa.abrir_balcao()
        item_id = caixa.adicionar_item(self.venda_id, produto_id, qtd, partes=partes)
        for sub, texto in self.ctx.impressao.pedido_remoto(self.venda_id, [item_id]).items():
            self.ctx.impressao.enviar_remoto(texto, f"pedido_{sub}")
            self.avisar(f"Pedido enviado à impressora remota: {sub}", tema.COR["ok"])
        return item_id

    def observacao_item(self) -> None:
        s = self.grade.selecionado()
        if s is None:
            return
        if not self.ctx.banco.valor("SELECT usa_observacao FROM produtos WHERE id = (SELECT produto_id FROM itens_venda WHERE id = ?)", (int(s),)):
            tema.aviso(self, "Este produto não permite observações (marque 'Permite observações' no cadastro).")
            return
        texto = caixa_dialogos.escolher_observacao(self, self.ctx)
        if texto:
            self.ctx.caixa.definir_observacao(int(s), texto)
            for sub, tk_ in self.ctx.impressao.pedido_remoto(self.venda_id, [int(s)]).items():
                self.ctx.impressao.enviar_remoto(tk_, f"obs_{sub}")
            self.recarregar()
            self.grade.selecionar(s)

    # ============================================================ cancelar
    def _autorizar(self, modulo: str, cfg: str, motivo: str) -> bool:
        if not self.ctx.acesso.precisa_senha(self.ctx.operador, modulo, cfg):
            return True
        return tema.pedir_senha_supervisor(self, self.ctx, modulo, motivo) is not None

    def menu_cancelar(self) -> None:
        if self.venda_id is None:
            tema.aviso(self, "Não há venda em andamento.")
            return
        op = tema.escolher(self, "Cancela...", [("item", "Cancela Item"), ("conta", "Cancela Conta (venda inteira)")],
                           "Escolha e tecle Enter:", altura=3)
        if op == "item":
            if self._autorizar("caixa_cancelamento", "exigir_senha_cancelamento", "Cancelar item exige autorização:"):
                self.modo_cancelar = True
                self._foco_grade(ultimo=True)
                self.avisar("Selecione o item com as setas e tecle Enter para cancelar. Esc retorna.", tema.COR["aviso"])
        elif op == "conta":
            self.cancelar_conta()

    def cancelar_conta(self) -> None:
        if not self._autorizar("caixa_cancelamento", "exigir_senha_cancelamento", "Cancelar a venda exige autorização:"):
            return
        if not tema.confirmar(self, "Cancelar a venda inteira?\nTodos os itens lançados serão eliminados.", "Cancela Venda", padrao_sim=False):
            return
        ok, _ = tema.tratar(self, self.ctx.caixa.cancelar_venda, self.venda_id, "cancelada no caixa")
        if ok:
            self.venda_id = None
            self._limpar_entrada()
            self.recarregar()
            self.avisar("Venda cancelada.", tema.COR["aviso"])
            self.ent_codigo.focus_set()

    def _enter_grade(self, _=None) -> str:
        if self.modo_cancelar:
            self.cancelar_item_selecionado()
        return "break"

    def cancelar_item_selecionado(self) -> None:
        s = self.grade.selecionado()
        if s is None:
            return
        if not self.modo_cancelar and not self._autorizar("caixa_cancelamento", "exigir_senha_cancelamento", "Cancelar item exige autorização:"):
            return
        nome = self.grade.valores(s)[1]
        if tema.confirmar(self, f"Cancelar o item '{nome}'?", "Cancela Item", padrao_sim=False):
            ok, _ = tema.tratar(self, self.ctx.caixa.cancelar_item, int(s))
            if ok:
                self.modo_cancelar = False
                self.recarregar()
                self.avisar("Item cancelado.", tema.COR["aviso"])
                self.ent_codigo.focus_set()

    def _sair_modo_cancelar(self) -> None:
        self.modo_cancelar = False
        self.avisar("")
        self.ent_codigo.focus_set()

    def _foco_grade(self, ultimo: bool = False) -> None:
        if self.grade.total():
            self.grade.tree.focus_set()
            self.grade.selecionar_indice(10 ** 9 if ultimo else max(self.grade.indice(), 0))

    # ============================================================== mesas
    def alternar_mesas(self, mostrar: bool | None = None) -> None:
        self.mesas_visiveis = (not self.mesas_visiveis) if mostrar is None else mostrar
        if self.mesas_visiveis:
            self.painel_mesas.pack(side="right", fill="y", padx=(10, 0), before=self.grade)
            self.carregar_mesas()
            self.grade_mesas.tree.focus_set()
            self.grade_mesas.selecionar_indice(0)
        else:
            self.painel_mesas.pack_forget()
            self.ent_codigo.focus_set()

    def carregar_mesas(self) -> None:
        ms = self.ctx.caixa.mesas()
        linhas, tags = [], []
        for m in ms:
            if m["status"] == "conta_enviada":
                sit, tag = "Conta enviada", ("enviada",)
            elif m["inativa"]:
                sit, tag = f"Parada {m['minutos_parada']} min", ("parada",)
            else:
                sit, tag = "Consumindo", ()
            linhas.append([m["posicao"], sit, fmt.fmt_num(m["total_cent"])])
            tags.append(tag)
        self.grade_mesas.preencher(linhas, [m["posicao"] for m in ms], tags)

    def _mesa_escolhida(self, _=None) -> str:
        s = self.grade_mesas.selecionado()
        if s is not None:
            self.var_pos.set(s)
            self.chamar_mesa()
        return "break"

    def foco_mesa(self) -> None:
        self.alternar_mesas(True)
        self.ent_pos.focus_set()
        self.ent_pos.selection_range(0, "end")

    def _descartar_se_vazia(self) -> None:
        """Ao sair de uma venda sem itens (mesa recém-aberta) ela é eliminada para não deixar mesa fantasma."""
        v = self.venda()
        if v and not self.ctx.caixa.itens(v["id"]) and v["modalidade"] in ("mesa", "caderneta") and not self.ctx.caixa.pagamentos(v["id"]):
            self.ctx.caixa.cancelar_venda(v["id"])

    def chamar_mesa(self) -> None:
        try:
            n = int(self.var_pos.get().strip() or 0)
        except ValueError:
            tema.aviso(self, "Digite o número da mesa.")
            return
        atual = self.venda()
        if atual and atual["modalidade"] == "mesa" and atual["posicao"] == n:
            self.ent_codigo.focus_set()
            return
        if atual and self.ctx.caixa.itens(atual["id"]) and atual["modalidade"] in ("balcao", "caderneta", "entrega"):
            tema.aviso(self, "Conclua, pague ou cancele a venda em andamento antes de chamar uma mesa.")
            self.var_pos.set("0")
            return
        self._descartar_se_vazia()
        if n == 0:
            self.venda_id = self.ctx.banco.valor(
                "SELECT id FROM vendas WHERE modalidade = 'balcao' AND status = 'aberta' ORDER BY id DESC LIMIT 1")
            self.recarregar()
            self.ent_codigo.focus_set()
            return
        pessoas = 0
        existente = self.ctx.banco.valor("SELECT id FROM vendas WHERE modalidade='mesa' AND posicao=? AND status IN ('aberta','conta_enviada')", (n,))
        if not existente and self.ctx.banco.cfg_bool("pergunta_pessoas"):
            pessoas = tema.pedir_numero(self, f"Mesa {n}", "Número de pessoas na mesa:", 1, 1, 999) or 0
        ok, res = tema.tratar(self, self.ctx.caixa.abrir_mesa, n, pessoas)
        if ok:
            self.venda_id = res[0]
            self.alternar_mesas(False)
            self.recarregar()
            self.ent_codigo.focus_set()

    def pre_conta(self) -> None:
        v = self.venda()
        if v is None:
            tema.aviso(self, "Não há conta em andamento.")
            return
        if v["modalidade"] == "entrega":
            return self.emitir_pedido_entrega()
        if v["modalidade"] != "mesa":
            tema.aviso(self, "A pré-conta é enviada às mesas. Escolha uma mesa (F4).")
            return
        ok, _ = tema.tratar(self, self.ctx.caixa.enviar_conta, v["id"])
        if ok:
            Visualizador(self, self.ctx, "Pré-conta", self.ctx.impressao.pre_conta(v["id"]), f"pre_conta_mesa_{v['posicao']}")
            self.venda_id = None
            self.recarregar()
            self.ent_codigo.focus_set()

    def transferir_mesa(self) -> None:
        v = self.venda()
        if v is None or v["modalidade"] != "mesa":
            tema.aviso(self, "Chame a mesa que será transferida (F4) e tecle F10.")
            return
        destino = tema.pedir_numero(self, "Transfere mesa", f"Transferir a mesa {v['posicao']} para a mesa:", "", 1, self.ctx.banco.cfg_int("num_mesas", 50))
        if destino is None:
            return
        ok, vid = tema.tratar(self, self.ctx.caixa.transferir_mesa, v["posicao"], destino)
        if ok:
            self.venda_id = vid
            self.recarregar()
            self.avisar(f"Mesa {v['posicao']} transferida para {destino}.", tema.COR["ok"])

    def transferir_varias(self) -> None:
        s = self.grade_mesas.selecionado()
        if s is None:
            return
        txt = tema.pedir_texto(self, "Transfere várias mesas", f"Mesas de origem (separe por vírgula) que irão para a mesa {s}:")
        if not txt:
            return
        try:
            origens = [int(x) for x in txt.replace(" ", "").split(",") if x]
        except ValueError:
            tema.aviso(self, "Use apenas números separados por vírgula.")
            return
        ok, vid = tema.tratar(self, self.ctx.caixa.transferir_varias, origens, int(s))
        if ok:
            self.carregar_mesas()
            if self.venda_id and not self.ctx.banco.valor("SELECT 1 FROM vendas WHERE id = ?", (self.venda_id,)):
                self.venda_id = None
                self.recarregar()

    def transferir_item(self) -> None:
        s = self.grade.selecionado()
        v = self.venda()
        if s is None or v is None or v["modalidade"] != "mesa":
            return
        qtd_atual = self.ctx.banco.valor("SELECT quantidade FROM itens_venda WHERE id = ?", (int(s),))
        destino = tema.pedir_numero(self, "Transfere item", "Mesa de destino:", "", 1, self.ctx.banco.cfg_int("num_mesas", 50))
        if destino is None:
            return
        qtd = tema.pedir_texto(self, "Transfere item", "Quantidade a transferir:", fmt.fmt_qtd(qtd_atual, 0) if qtd_atual == int(qtd_atual) else fmt.fmt_qtd(qtd_atual))
        if not qtd:
            return
        try:
            quantidade = fmt.para_qtd(qtd)
        except ValueError:
            tema.aviso(self, "Quantidade inválida.")
            return
        ok, _ = tema.tratar(self, self.ctx.caixa.transferir_item, int(s), destino, quantidade)
        if ok:
            self.recarregar()
            self.avisar(f"Item transferido para a mesa {destino}.", tema.COR["ok"])

    # ============================================================== pagar
    def pagar(self) -> None:
        v = self.venda()
        if v is None or (not self.ctx.caixa.itens(v["id"]) and v["modalidade"] != "caderneta"):
            tema.aviso(self, "Lance ao menos um item antes de pagar.")
            return
        itens = self.ctx.caixa.itens(v["id"])
        if v["modalidade"] == "caderneta" and itens:
            c = self.ctx.caderneta.obter(v["cliente_id"])
            if not tema.confirmar(self, f"Lançar {fmt.fmt_brl(v['total_cent'])} na caderneta de {c['nome']}?", "Caderneta"):
                return
            ok, venda = tema.tratar(self, self.ctx.caixa.fechar, v["id"])
            if ok:
                self._pos_fechamento(venda)
            return
        j = JanelaPagamento(self, self.ctx, v["id"])
        if j.fechou:
            self._pos_fechamento(self.ctx.caixa.obter(v["id"]))
        else:
            self.recarregar()
            self.ent_codigo.focus_set()

    def _pos_fechamento(self, venda: dict) -> None:
        if venda["modalidade"] == "caderneta" and self.ctx.banco.cfg_bool("imprimir_cupom", True):
            Visualizador(self, self.ctx, f"Cupom {venda['cupom']}", self.ctx.impressao.cupom(venda["id"]), f"cupom_{venda['cupom']}")
        self.lbl_troco.configure(text=fmt.fmt_num(venda["troco_cent"]))
        self.venda_id = None
        self._limpar_entrada()
        self.recarregar()
        self.lbl_troco.configure(text=fmt.fmt_num(venda["troco_cent"]))
        self.avisar(f"Venda {venda['cupom']} fechada. Troco {fmt.fmt_brl(venda['troco_cent'])}.", tema.COR["ok"])
        self.ent_codigo.focus_set()

    # ========================================= caderneta / entrega / outros
    def _exigir_venda_vazia(self) -> bool:
        v = self.venda()
        if v and self.ctx.caixa.itens(v["id"]):
            tema.aviso(self, "Conclua, pague ou cancele a venda atual antes de trocar de modalidade.")
            return False
        self._descartar_se_vazia()
        self.venda_id = None
        return True

    def caderneta(self) -> None:
        if not self._exigir_venda_vazia():
            return
        j = JanelaClientes(self, self.ctx, "caderneta")
        if j.cliente_id:
            ok, vid = tema.tratar(self, self.ctx.caixa.abrir_caderneta, j.cliente_id)
            if ok:
                self.venda_id = vid
        self.recarregar()
        self.ent_codigo.focus_set()

    def entrega(self) -> None:
        escolha = tema.escolher(self, "Delivery", [("novo", "Novo pedido de entrega"), ("lista", "Entregas pendentes (receber / entregador)")],
                                "Escolha:", altura=3)
        if escolha == "novo":
            if not self._exigir_venda_vazia():
                return
            j = JanelaClientes(self, self.ctx, "entrega")
            if j.cliente_id:
                ok, vid = tema.tratar(self, self.ctx.entregas.abrir, j.cliente_id)
                if ok:
                    self.venda_id = vid
        elif escolha == "lista":
            if not self._exigir_venda_vazia():
                return
            j = JanelaEntregas(self, self.ctx)
            if j.venda_id:
                self.venda_id = j.venda_id
        self.recarregar()
        self.ent_codigo.focus_set()

    def liberar_troco(self) -> None:
        v = self.venda()
        if v is None or v["modalidade"] != "entrega":
            return
        dlg = tema.Dialogo(self, "Entrega - liberar troco")
        ttk.Label(dlg.corpo, text=f"Total do pedido (com taxa): {fmt.fmt_brl(v['total_cent'])}", font=tema.FONTE_B).pack(anchor="w")
        ttk.Label(dlg.corpo, text="Cliente vai pagar com (R$):", style="Rotulo.TLabel").pack(anchor="w", pady=(8, 0))
        var = tk.StringVar(value=fmt.fmt_num(v["troco_para_cent"]) if v["troco_para_cent"] else "")
        e1 = ttk.Entry(dlg.corpo, textvariable=var, width=16)
        e1.pack(anchor="w")
        lbl = ttk.Label(dlg.corpo, text="", font=tema.FONTE_B, foreground=tema.COR["troco"])
        lbl.pack(anchor="w", pady=4)
        ents = [(r["id"], r["nome"]) for r in self.ctx.cadastros.listar("operadores", apenas_ativos=True) if r["entregador"]]
        ttk.Label(dlg.corpo, text="Entregador (opcional)", style="Rotulo.TLabel").pack(anchor="w")
        var_ent = tk.StringVar(value=next((n for i, n in ents if i == v["entregador_id"]), ""))
        ttk.Combobox(dlg.corpo, textvariable=var_ent, values=[""] + [n for _, n in ents], state="readonly", width=30).pack(anchor="w")
        ttk.Label(dlg.corpo, text="Mensagem para o pedido", style="Rotulo.TLabel").pack(anchor="w", pady=(8, 0))
        var_msg = tk.StringVar(value=v["mensagem"] or "")
        ttk.Entry(dlg.corpo, textvariable=var_msg, width=44).pack(fill="x")

        def calc(*_):
            try:
                c = fmt.para_centavos(var.get())
                lbl.configure(text=f"Troco a levar: {fmt.fmt_brl(max(c - v['total_cent'], 0))}" if c else "")
            except ValueError:
                lbl.configure(text="")
        var.trace_add("write", calc)
        calc()

        def gravar(_=None):
            try:
                troco_para = fmt.para_centavos(var.get()) if var.get().strip() else 0
                eid = next((i for i, n in ents if n == var_ent.get()), None)
                self.ctx.entregas.definir_dados(v["id"], troco_para, eid, var_msg.get())
            except (ValueError, ErroNegocio) as ex:
                tema.erro(dlg, str(ex))
                return
            dlg.ok()
        tema._botoes(dlg, "Gravar", comando_ok=gravar)
        dlg.bind("<Return>", gravar)
        dlg.mostrar(e1)
        self.recarregar()

    def emitir_pedido_entrega(self) -> None:
        v = self.venda()
        ok, _ = tema.tratar(self, self.ctx.entregas.emitir_pedido, v["id"])
        if ok:
            Visualizador(self, self.ctx, "Pedido de entrega", self.ctx.impressao.pedido_entrega(v["id"]), f"entrega_{v['posicao']}")
            self.venda_id = None
            self.recarregar()
            self.ent_codigo.focus_set()

    def repique(self) -> None:
        v = self.venda()
        pos = v["posicao"] if v and v["modalidade"] == "mesa" else tema.pedir_numero(self, "Repique", "Posição (mesa) que deixou o repique:", "", 0, 9999)
        if pos is None:
            return
        valor = tema.pedir_dinheiro(self, "Repique", "Valor deixado pelo cliente (R$):")
        if valor is None:
            return
        t = self.ctx.turnos.atual()
        ok, _ = tema.tratar(self, self.ctx.turnos.repique, t["id"], self.ctx.operador_id, pos, valor)
        if ok:
            self.avisar(f"Repique de {fmt.fmt_brl(valor)} registrado.", tema.COR["ok"])

    def sangria(self) -> None:
        if not self._autorizar("caixa_sangria", "exigir_senha_sangria", "Sangria exige autorização:"):
            return
        t = self.ctx.turnos.atual()
        if caixa_dialogos.sangria(self, self.ctx, t["id"]):
            self.avisar("Movimento financeiro registrado.", tema.COR["ok"])

    def gaveta(self) -> None:
        if not self._autorizar("caixa_gaveta", "exigir_senha_gaveta", "Abrir a gaveta exige autorização:"):
            return
        self.ctx.banco.log("gaveta", "abertura manual", self.ctx.operador_id)
        try:
            self.ctx.gaveta().abrir()
            self.avisar("Gaveta aberta.", tema.COR["ok"])
        except DispositivoIndisponivel as e:
            tema.aviso(self, f"{e}\nA abertura foi registrada.", "Gaveta")

    def balanca(self) -> None:
        if self.produto is None:
            tema.aviso(self, "Lance o código do produto antes de capturar o peso.")
            return
        try:
            peso = self.ctx.balanca().ler_peso()
        except DispositivoIndisponivel as e:
            txt = tema.pedir_texto(self, "Balança", f"{e}\nPeso (kg):", self.var_qtd.get())
            if not txt:
                return
            try:
                peso = fmt.para_qtd(txt)
            except ValueError:
                tema.aviso(self, "Peso inválido.")
                return
        self.ent_qtd.configure(state="normal")
        self.var_qtd.set(fmt.fmt_qtd(peso, 3).replace(".", ""))
        self.ent_qtd.focus_set()

    def alternar_leitor(self) -> None:
        self.leitor = not self.leitor
        self.lbl_leitor.configure(text="LEITOR ÓPTICO ATIVO" if self.leitor else "")
        self.avisar("Leitor óptico " + ("ativado: cada item entra com quantidade 1." if self.leitor else "desativado."))

    def impressora(self) -> None:
        op = tema.escolher(self, "Impressora", [("x", "Leitura X (parcial do turno - gerencial)"), ("z", "Redução Z (fechamento do dia - gerencial)")],
                           "Funções gerenciais (não emitem documento fiscal):", altura=3)
        if op == "x":
            t = self.ctx.turnos.atual()
            Visualizador(self, self.ctx, "Leitura X", self.ctx.impressao.leitura_x(t["id"]), "leitura_x")
        elif op == "z":
            Visualizador(self, self.ctx, "Redução Z", self.ctx.impressao.reducao_z(), "reducao_z")

    def fechar_turno(self) -> None:
        v = self.venda()
        if v and self.ctx.caixa.itens(v["id"]) and v["modalidade"] in ("balcao", "caderneta"):
            tema.aviso(self, "Há uma venda em andamento. Conclua ou cancele antes de trocar o turno.")
            return
        self._descartar_se_vazia()
        self.venda_id = None
        if caixa_dialogos.trocar_turno(self, self.ctx):
            self.destroy()

    def sair(self) -> None:
        v = self.venda()
        if v and v["modalidade"] == "balcao" and self.ctx.caixa.itens(v["id"]):
            if not tema.confirmar(self, "Há uma venda em andamento no balcão.\nSair mantém a venda aberta para continuar depois. Sair mesmo?", "Sair do caixa"):
                return
        else:
            try:
                self._descartar_se_vazia()
            except ErroNegocio:
                pass
        self.destroy()

    # ============================================================== barra
    def _entrar_barra(self) -> None:
        self.indice_barra = 0
        self._pintar_barra()
        self.avisar("Barra de tarefas: use as setas e Enter. Esc volta. (Pagar já está selecionado)")

    def _sair_barra(self) -> None:
        self.indice_barra = None
        self._pintar_barra()
        self.avisar("")
        self.ent_codigo.focus_set()

    def _barra_mover(self, d: int) -> None:
        if self.indice_barra is not None:
            self.indice_barra = (self.indice_barra + d) % len(self.tarefas)
            self._pintar_barra()

    def _barra_enter(self, _=None) -> str:
        i = self.indice_barra
        self._sair_barra()
        if i is not None:
            self.tarefas[i][1]()
        return "break"

    def _barra_esc(self, _=None) -> str:
        self._sair_barra()
        return "break"

    def _exec_barra(self, fn) -> None:
        if self.indice_barra is not None:
            self._sair_barra()
        fn()

    def _pintar_barra(self) -> None:
        for i, b in enumerate(self.botoes_tarefa):
            b.configure(style="Sel.TButton" if i == self.indice_barra else "Barra.TButton")
        if self.indice_barra is not None:
            self.status.configure(text=self.tarefas[self.indice_barra][0])
