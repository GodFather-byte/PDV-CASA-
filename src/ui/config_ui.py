"""Configurações (manual ADM seção 8): acessos, loja, configurações operacionais e máquinas."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.controllers.config_controller import CAMPOS_CONFIG, CAMPOS_LOJA, CAMPOS_MAQUINA
from src.core.erros import ErroNegocio
from src.ui import tema
from src.ui.visualizador import Visualizador


def abrir(master, ctx, chave: str):
    if chave == "acessos":
        return JanelaAcessos(master, ctx)
    if chave == "loja":
        return JanelaFormulario(master, ctx, "Dados da Loja", [(c[0], c[1], c[2], "Dados", None) for c in CAMPOS_LOJA],
                                ctx.config.loja, ctx.config.salvar_loja, imprimivel=True)
    if chave == "maquinas":
        campos = [(c[0], c[1], c[2], "Máquina", c[3] if len(c) > 3 else None) for c in CAMPOS_MAQUINA]

        def _testar(janela):
            ok, _ = tema.tratar(janela, ctx.config.salvar_maquina, janela._coletar())
            if ok:
                sucesso, _ = tema.tratar(janela, ctx.impressao.imprimir_teste)
                if sucesso:
                    tema.mensagem(janela, "Página de teste enviada à impressora térmica.", "Teste de impressão")

        def _gaveta(janela):
            ok, _ = tema.tratar(janela, ctx.config.salvar_maquina, janela._coletar())
            if ok:
                sucesso, _ = tema.tratar(janela, ctx.impressao.abrir_gaveta)
                if sucesso:
                    tema.mensagem(janela, "Pulso de abertura enviado à gaveta.", "Gaveta")

        return JanelaFormulario(master, ctx, "Máquinas", campos, ctx.config.maquina, ctx.config.salvar_maquina,
                                aviso="Atenção: as mudanças nas configurações do equipamento só valem depois de sair do programa e entrar novamente.",
                                somente_leitura=("terminal",),
                                acoes=[("Imprimir página de teste", _testar), ("Abrir gaveta", _gaveta)])
    return JanelaFormulario(master, ctx, "Configurações", [(c[0], c[1], c[2], c[3], None) for c in CAMPOS_CONFIG],
                            ctx.config.todas, ctx.config.salvar_config)


class JanelaFormulario(tk.Toplevel):
    """Formulário simples dirigido por lista de campos (chave, rótulo, tipo, seção, opções)."""

    def __init__(self, master, ctx, titulo, campos, carregar, salvar, aviso: str | None = None,
                 imprimivel: bool = False, somente_leitura: tuple = (), acoes=None):
        super().__init__(master)
        self.ctx, self.campos, self.carregar, self.salvar = ctx, campos, carregar, salvar
        self.somente_leitura = somente_leitura
        self.title(titulo)
        self.configure(bg=tema.COR["fundo"])
        self.geometry("900x660" if len({c[3] for c in campos}) > 1 else "760x560")
        barra = tk.Frame(self, bg=tema.COR["marinho"], padx=6, pady=5)
        barra.pack(fill="x")
        ttk.Button(barra, text="Gravar", style="Barra.TButton", command=self.gravar).pack(side="left", padx=2)
        ttk.Button(barra, text="Cancelar", style="Barra.TButton", command=self.recarregar).pack(side="left", padx=2)
        if imprimivel:
            ttk.Button(barra, text="Imprimir", style="Barra.TButton", command=self.imprimir).pack(side="left", padx=2)
        for rotulo, fn in (acoes or []):
            ttk.Button(barra, text=rotulo, style="Barra.TButton", command=lambda f=fn: f(self)).pack(side="left", padx=2)
        ttk.Button(barra, text="Sair", style="Barra.TButton", command=self.destroy).pack(side="right")
        if aviso:
            ttk.Label(self, text=aviso, foreground=tema.COR["aviso"], wraplength=800, padding=(12, 8, 12, 0)).pack(anchor="w")
        secoes: dict[str, list] = {}
        for c in campos:
            secoes.setdefault(c[3], []).append(c)
        corpo = ttk.Frame(self, padding=12)
        corpo.pack(fill="both", expand=True)
        nb = ttk.Notebook(corpo) if len(secoes) > 1 else None
        if nb:
            nb.pack(fill="both", expand=True)
        self.vars: dict[str, tk.Variable] = {}
        self.opcoes: dict[str, dict] = {}
        for nome, lista in secoes.items():
            pagina = ttk.Frame(nb, padding=12) if nb else corpo
            if nb:
                nb.add(pagina, text=nome)
            for i, (chave, rotulo, tipo, _, opc) in enumerate(lista):
                if tipo == "sn":
                    v = tk.BooleanVar()
                    ttk.Checkbutton(pagina, text=rotulo, variable=v).grid(row=i, column=0, columnspan=2, sticky="w", pady=4)
                else:
                    v = tk.StringVar()
                    ttk.Label(pagina, text=rotulo, style="Rotulo.TLabel").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 12))
                    if tipo == "escolha":
                        self.opcoes[chave] = {r: val for val, r in opc}
                        w = ttk.Combobox(pagina, textvariable=v, values=[r for _, r in opc], state="readonly", width=34)
                    else:
                        w = ttk.Entry(pagina, textvariable=v, width=46 if tipo == "texto" else 14,
                                      state="readonly" if chave in somente_leitura else "normal")
                    w.grid(row=i, column=1, sticky="w", pady=4)
                self.vars[chave] = v
        self.recarregar()
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-s>", lambda e: self.gravar())
        tema.centralizar(self, master.winfo_toplevel())
        self.transient(master.winfo_toplevel())

    def recarregar(self) -> None:
        dados = self.carregar()
        for chave, rotulo, tipo, _, opc in self.campos:
            v = dados.get(chave)
            if tipo == "sn":
                self.vars[chave].set(str(v).upper() in ("S", "1", "TRUE"))
            elif tipo == "escolha":
                self.vars[chave].set(next((r for val, r in opc if str(val) == str(v)), ""))
            else:
                self.vars[chave].set("" if v is None else str(v))

    def _coletar(self) -> dict:
        valores = {}
        for chave, _, tipo, _, opc in self.campos:
            if chave in self.somente_leitura:
                continue
            v = self.vars[chave].get()
            if tipo == "sn":
                v = "S" if v else "N"
            elif tipo == "escolha":
                v = self.opcoes[chave].get(v, v)
            valores[chave] = v
        return valores

    def gravar(self) -> None:
        ok, _ = tema.tratar(self, self.salvar, self._coletar())
        if ok:
            tema.mensagem(self, "Configurações gravadas.", "Gravar")

    def imprimir(self) -> None:
        l = self.ctx.config.loja()
        texto = "\n".join(f"{c[1]:<40} {l.get(c[0]) or ''}" for c in CAMPOS_LOJA)
        Visualizador(self, self.ctx, "Dados da loja", "DADOS DA LOJA\n" + "=" * 60 + "\n" + texto, "dados_loja")


class JanelaAcessos(tk.Toplevel):
    """Nível mínimo de cada módulo (1 a 4). O nível 0 já é o do caixa e não aparece."""

    def __init__(self, master, ctx):
        super().__init__(master)
        self.ctx = ctx
        self.title("Acessos ao sistema")
        self.configure(bg=tema.COR["fundo"])
        self.geometry("880x640")
        corpo = ttk.Frame(self, padding=12)
        corpo.pack(fill="both", expand=True)
        ttk.Label(corpo, text="Cada módulo exige um nível mínimo. Os níveis são hierárquicos: o operador de nível 4 executa tudo o que "
                              "estiver restrito aos demais. O nível 0 é exclusivo da operação de caixa.",
                  wraplength=820, justify="left").pack(anchor="w", pady=(0, 8))
        self.grade = tema.Grade(corpo, [("grupo", "Grupo", 110, "w"), ("desc", "Módulo", 400, "w"), ("nivel", "Nível", 60, "center")], altura=18)
        self.grade.pack(fill="both", expand=True)
        edit = ttk.Frame(corpo)
        edit.pack(fill="x", pady=(10, 0))
        self.lbl = ttk.Label(edit, text="Selecione um módulo", font=tema.FONTE_B)
        self.lbl.pack(side="left")
        self.v_nivel = tk.StringVar(value="2")
        ttk.Button(edit, text="Gravar", style="Ok.TButton", command=self.gravar).pack(side="right")
        ttk.Combobox(edit, textvariable=self.v_nivel, values=["1", "2", "3", "4"], state="readonly", width=4).pack(side="right", padx=8)
        ttk.Label(edit, text="Novo nível:").pack(side="right")
        self.grade.tree.bind("<<TreeviewSelect>>", self._sel)
        self.bind("<Escape>", lambda e: self.destroy())
        self.carregar()
        tema.centralizar(self, master.winfo_toplevel())
        self.transient(master.winfo_toplevel())

    def carregar(self, manter: str | None = None) -> None:
        mods = self.ctx.acesso.modulos()
        self.grade.preencher([[m["grupo"], m["descricao"], m["nivel"]] for m in mods], [m["modulo"] for m in mods])
        self.grade.selecionar(manter) if manter else self.grade.selecionar_indice(0)

    def _sel(self, _=None) -> None:
        s = self.grade.selecionado()
        if s:
            v = self.grade.valores(s)
            self.lbl.configure(text=v[1])
            self.v_nivel.set(str(v[2]))

    def gravar(self) -> None:
        s = self.grade.selecionado()
        if s is None:
            return
        ok, _ = tema.tratar(self, self.ctx.acesso.alterar_nivel_modulo, s, int(self.v_nivel.get()))
        if ok:
            self.carregar(s)
