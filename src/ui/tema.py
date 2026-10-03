"""Tema visual, componentes (Grade) e diálogos reutilizáveis da interface Tkinter."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.core import formatacao as fmt
from src.core.erros import ErroNegocio

COR = {
    "fundo": "#eef1f8", "painel": "#ffffff", "texto": "#1c2438", "suave": "#5b6785",
    "marinho": "#14234d", "marinho2": "#1f3a8a", "borda": "#c9d1e6",
    "ok": "#1f9d63", "perigo": "#c93a3a", "aviso": "#d9981e", "total": "#9b1c1c", "troco": "#1f3a8a",
    "linha_par": "#f6f8fd", "selecao": "#cfe0ff",
}
FONTE = ("Segoe UI", 10)
FONTE_B = ("Segoe UI", 10, "bold")
FONTE_G = ("Segoe UI", 14, "bold")
FONTE_MONO = ("Consolas", 10)


def aplicar_tema(root: tk.Misc) -> None:
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except tk.TclError:
        pass
    root.configure(bg=COR["fundo"])
    s.configure(".", font=FONTE, background=COR["fundo"], foreground=COR["texto"])
    s.configure("TFrame", background=COR["fundo"])
    s.configure("Painel.TFrame", background=COR["painel"], relief="solid", borderwidth=1)
    s.configure("TLabel", background=COR["fundo"], foreground=COR["texto"])
    s.configure("Painel.TLabel", background=COR["painel"])
    s.configure("Rotulo.TLabel", font=("Segoe UI", 9, "bold"), foreground=COR["marinho2"])
    s.configure("Titulo.TLabel", font=FONTE_G, foreground=COR["marinho"])
    s.configure("TButton", padding=(10, 5), background=COR["marinho2"], foreground="white", borderwidth=0)
    s.map("TButton", background=[("active", "#2c52c4"), ("disabled", "#9aa6c6")],
          foreground=[("disabled", "#e5e9f5")])
    s.configure("Perigo.TButton", background=COR["perigo"])
    s.map("Perigo.TButton", background=[("active", "#a82d2d")])
    s.configure("Ok.TButton", background=COR["ok"])
    s.map("Ok.TButton", background=[("active", "#17784b")])
    s.configure("Barra.TButton", padding=(8, 6), background=COR["marinho"], foreground="white", font=("Segoe UI", 9))
    s.map("Barra.TButton", background=[("active", COR["marinho2"])])
    s.configure("Sel.TButton", background=COR["aviso"], foreground="black")
    s.configure("TEntry", padding=4, fieldbackground="white")
    s.configure("TCombobox", padding=4, fieldbackground="white")
    s.configure("Treeview", rowheight=24, font=FONTE, background="white", fieldbackground="white", bordercolor=COR["borda"])
    s.configure("Treeview.Heading", font=FONTE_B, background=COR["marinho"], foreground="white", padding=5)
    s.map("Treeview.Heading", background=[("active", COR["marinho2"])])
    s.map("Treeview", background=[("selected", COR["selecao"])], foreground=[("selected", COR["texto"])])
    s.configure("TNotebook", background=COR["fundo"])
    s.configure("TNotebook.Tab", padding=(12, 5), font=FONTE_B)
    s.configure("TLabelframe", background=COR["fundo"], bordercolor=COR["borda"])
    s.configure("TLabelframe.Label", background=COR["fundo"], font=FONTE_B, foreground=COR["marinho2"])
    s.configure("TCheckbutton", background=COR["fundo"])


def centralizar(janela: tk.Toplevel, pai: tk.Misc | None = None) -> None:
    janela.update_idletasks()
    w, h = janela.winfo_reqwidth(), janela.winfo_reqheight()
    if pai is not None and pai.winfo_ismapped():
        x = pai.winfo_rootx() + (pai.winfo_width() - w) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - h) // 3
    else:
        x = (janela.winfo_screenwidth() - w) // 2
        y = (janela.winfo_screenheight() - h) // 3
    janela.geometry(f"+{max(x, 0)}+{max(y, 0)}")


# ---------------------------------------------------------------- Grade
class Grade(ttk.Frame):
    """Treeview com barra de rolagem e linhas alternadas.

    `colunas`: lista de (id, título, largura_px, alinhamento['w'|'e'|'center'])."""

    def __init__(self, master, colunas, altura: int = 10, selectmode: str = "browse"):
        super().__init__(master)
        self.colunas = colunas
        self.tree = ttk.Treeview(self, columns=[c[0] for c in colunas], show="headings", height=altura,
                                 selectmode=selectmode)
        for cid, titulo, largura, anchor in colunas:
            self.tree.heading(cid, text=titulo)
            self.tree.column(cid, width=largura, anchor=anchor, stretch=anchor == "w")
        barra = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.tree.tag_configure("par", background=COR["linha_par"])
        self._n = 0

    def limpar(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._n = 0

    def adicionar(self, valores, iid: str | int | None = None, tags=()) -> str:
        tags = tuple(tags) + (("par",) if self._n % 2 else ())
        self._n += 1
        kw = {"iid": str(iid)} if iid is not None else {}
        return self.tree.insert("", "end", values=list(valores), tags=tags, **kw)

    def preencher(self, linhas, ids=None, tags=None) -> None:
        self.limpar()
        for i, ln in enumerate(linhas):
            self.adicionar(ln, ids[i] if ids else None, tags[i] if tags else ())

    def selecionado(self) -> str | None:
        s = self.tree.selection()
        return s[0] if s else None

    def selecionar(self, iid: str | int | None) -> None:
        if iid is None:
            return
        iid = str(iid)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            self.tree.see(iid)

    def selecionar_indice(self, i: int) -> None:
        filhos = self.tree.get_children()
        if filhos:
            self.selecionar(filhos[max(0, min(i, len(filhos) - 1))])

    def indice(self) -> int:
        s = self.selecionado()
        return self.tree.get_children().index(s) if s else -1

    def valores(self, iid) -> list:
        return list(self.tree.item(str(iid), "values"))

    def tag(self, nome: str, **kw) -> None:
        self.tree.tag_configure(nome, **kw)

    def total(self) -> int:
        return len(self.tree.get_children())


# --------------------------------------------------------------- diálogos
class Dialogo(tk.Toplevel):
    def __init__(self, master, titulo: str):
        super().__init__(master)
        self.withdraw()
        self.title(titulo)
        self.configure(bg=COR["fundo"])
        self.resizable(False, False)
        self.resultado = None
        self._pai = master
        self.corpo = ttk.Frame(self, padding=14)
        self.corpo.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda e: self.cancelar())
        self.protocol("WM_DELETE_WINDOW", self.cancelar)

    def ok(self, valor=True) -> None:
        self.resultado = valor
        self.destroy()

    def cancelar(self) -> None:
        self.resultado = None
        self.destroy()

    def mostrar(self, foco: tk.Misc | None = None):
        try:
            self.transient(self._pai.winfo_toplevel())
        except tk.TclError:
            pass
        centralizar(self, self._pai.winfo_toplevel())
        self.deiconify()
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        (foco or self).focus_set()
        self.wait_window(self)
        return self.resultado


def _botoes(dlg: Dialogo, ok_texto="OK", cancelar_texto="Cancelar", estilo_ok="TButton", comando_ok=None):
    barra = ttk.Frame(dlg.corpo)
    barra.pack(fill="x", pady=(12, 0))
    b_ok = ttk.Button(barra, text=ok_texto, style=estilo_ok, command=comando_ok or dlg.ok)
    b_ok.pack(side="right")
    if cancelar_texto:
        ttk.Button(barra, text=cancelar_texto, command=dlg.cancelar).pack(side="right", padx=(0, 8))
    return b_ok


def mensagem(master, texto: str, titulo: str = "Aviso", tipo: str = "info") -> None:
    dlg = Dialogo(master, titulo)
    cor = {"info": COR["marinho2"], "erro": COR["perigo"], "aviso": COR["aviso"]}[tipo]
    ttk.Label(dlg.corpo, text=texto, wraplength=420, justify="left", foreground=cor if tipo == "erro" else COR["texto"],
              font=FONTE_B if tipo == "erro" else FONTE).pack(anchor="w")
    b = _botoes(dlg, "OK", None)
    dlg.bind("<Return>", lambda e: dlg.ok())
    dlg.mostrar(b)


def erro(master, texto: str, titulo: str = "Atenção") -> None:
    mensagem(master, texto, titulo, "erro")


def aviso(master, texto: str, titulo: str = "Aviso") -> None:
    mensagem(master, texto, titulo, "aviso")


def confirmar(master, texto: str, titulo: str = "Confirma", sim="Sim", nao="Não", padrao_sim: bool = True) -> bool:
    dlg = Dialogo(master, titulo)
    ttk.Label(dlg.corpo, text=texto, wraplength=420, justify="left").pack(anchor="w")
    barra = ttk.Frame(dlg.corpo)
    barra.pack(fill="x", pady=(14, 0))
    b_sim = ttk.Button(barra, text=f"{sim} (S)", command=lambda: dlg.ok(True))
    b_nao = ttk.Button(barra, text=f"{nao} (N)", command=lambda: dlg.ok(False))
    b_nao.pack(side="right")
    b_sim.pack(side="right", padx=(0, 8))
    dlg.bind("<s>", lambda e: dlg.ok(True)); dlg.bind("<S>", lambda e: dlg.ok(True))
    dlg.bind("<n>", lambda e: dlg.ok(False)); dlg.bind("<N>", lambda e: dlg.ok(False))
    foco = b_sim if padrao_sim else b_nao
    for b, v in ((b_sim, True), (b_nao, False)):
        b.bind("<Return>", lambda e, v=v: (dlg.ok(v), "break")[1])   # Enter no botão = a escolha do botão
    dlg.bind("<Return>", lambda e: dlg.ok(padrao_sim))
    dlg.cancelar = lambda: dlg.ok(False)   # Esc e fechar a janela = Não
    dlg.bind("<Escape>", lambda e: dlg.ok(False))
    dlg.protocol("WM_DELETE_WINDOW", lambda: dlg.ok(False))
    return bool(dlg.mostrar(foco))


def pedir_texto(master, titulo: str, rotulo: str, inicial: str = "", senha: bool = False, largura: int = 34,
                validar=None) -> str | None:
    dlg = Dialogo(master, titulo)
    ttk.Label(dlg.corpo, text=rotulo, style="Rotulo.TLabel").pack(anchor="w")
    var = tk.StringVar(value=inicial)
    ent = ttk.Entry(dlg.corpo, textvariable=var, width=largura, show="*" if senha else "")
    ent.pack(fill="x", pady=(4, 0))
    msg = ttk.Label(dlg.corpo, text="", foreground=COR["perigo"])
    msg.pack(anchor="w")

    def aceitar(_=None):
        v = var.get().strip()
        if validar:
            try:
                v = validar(v)
            except (ValueError, ErroNegocio) as e:
                msg.configure(text=str(e))
                return
        dlg.ok(v)
    _botoes(dlg, comando_ok=aceitar)
    dlg.bind("<Return>", aceitar)
    ent.selection_range(0, "end")
    return dlg.mostrar(ent)


def pedir_dinheiro(master, titulo: str, rotulo: str, inicial_cent: int | None = None, permitir_zero: bool = False) -> int | None:
    def validar(v):
        c = fmt.para_centavos(v)
        if c < 0 or (c == 0 and not permitir_zero):
            raise ValueError("Informe um valor maior que zero." if not permitir_zero else "Valor inválido.")
        return c
    r = pedir_texto(master, titulo, rotulo, fmt.fmt_num(inicial_cent) if inicial_cent is not None else "",
                    largura=18, validar=validar)
    return r


def pedir_numero(master, titulo: str, rotulo: str, inicial: int | str = "", minimo: int = 0, maximo: int | None = None) -> int | None:
    def validar(v):
        try:
            n = int(v)
        except ValueError:
            raise ValueError("Digite um número inteiro.") from None
        if n < minimo or (maximo is not None and n > maximo):
            raise ValueError(f"Use um número de {minimo}" + (f" a {maximo}." if maximo is not None else " em diante."))
        return n
    return pedir_texto(master, titulo, rotulo, str(inicial), largura=14, validar=validar)


def escolher(master, titulo: str, itens: list[tuple], rotulo: str = "Digite para filtrar", largura: int = 460,
             altura: int = 12, colunas: list[tuple] | None = None):
    """Lista com filtro por digitação. `itens` = [(valor, texto)] ou [(valor, (col1, col2...))] com `colunas`.
    Enter ou duplo clique escolhem; Esc cancela. Devolve o valor ou None."""
    dlg = Dialogo(master, titulo)
    ttk.Label(dlg.corpo, text=rotulo, style="Rotulo.TLabel").pack(anchor="w")
    var = tk.StringVar()
    ent = ttk.Entry(dlg.corpo, textvariable=var)
    ent.pack(fill="x", pady=(2, 8))
    cols = colunas or [("t", "", largura, "w")]
    grade = Grade(dlg.corpo, cols, altura=altura)
    grade.pack(fill="both", expand=True)

    def textos(texto):
        return texto if isinstance(texto, (tuple, list)) else (texto,)

    def montar(*_):
        filtro = var.get().strip().lower()
        grade.limpar()
        for i, (valor, texto) in enumerate(itens):
            if not filtro or filtro in " ".join(str(x) for x in textos(texto)).lower():
                grade.adicionar(textos(texto), iid=i)
        grade.selecionar_indice(0)

    def escolher_atual(_=None):
        s = grade.selecionado()
        if s is not None:
            dlg.ok(itens[int(s)][0])

    var.trace_add("write", montar)
    montar()
    ent.bind("<Down>", lambda e: (grade.selecionar_indice(grade.indice() + 1), "break")[1])
    ent.bind("<Up>", lambda e: (grade.selecionar_indice(grade.indice() - 1), "break")[1])
    grade.tree.bind("<Double-1>", escolher_atual)
    grade.tree.bind("<Return>", escolher_atual)
    dlg.bind("<Return>", escolher_atual)
    _botoes(dlg, "Escolher", comando_ok=escolher_atual)
    return dlg.mostrar(ent)


def pedir_senha_supervisor(master, ctx, modulo: str, motivo: str = ""):
    """Janela 'Digite uma Senha Válida'. Devolve o Operador autorizado ou None."""
    for tentativa in range(3):
        senha = pedir_texto(master, "Autorização", (motivo + "\n" if motivo else "") + "Digite uma senha válida:", senha=True,
                            largura=22)
        if senha is None:
            return None
        sup = ctx.acesso.validar_supervisor(senha, modulo)
        if sup is not None:
            return sup
        erro(master, "Senha inválida ou sem permissão para esta operação.")
    return None


def tratar(master, funcao, *args, **kwargs):
    """Executa `funcao` e mostra erros de negócio ao operador. Devolve (ok, resultado)."""
    try:
        return True, funcao(*args, **kwargs)
    except ErroNegocio as e:
        erro(master, str(e))
    except Exception as e:  # noqa: BLE001 - nunca deixar a tela morrer no caixa
        import traceback
        traceback.print_exc()
        erro(master, f"Erro inesperado: {e}\nO movimento já gravado foi preservado.", "Erro")
    return False, None
