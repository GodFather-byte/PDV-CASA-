"""Visual escuro do caixa (o mesmo azul-noite do menu principal): cores e estilos ttk próprios, prefixo "Cx".

Os estilos só valem para quem os pede pelo nome (`style="Cx.TButton"`...); as outras telas continuam com o tema claro."""
from __future__ import annotations

from tkinter import ttk

from src.ui.menu_widgets import PAL, FONTE, misturar

CX = {      # o azul-noite do caixa: mais saturado que o do menu, para os cartões de comanda se destacarem
    "fundo": "#0a1029", "cabecalho": "#0c1432", "cartao": "#111a40", "cartao2": "#1a2656",
    "borda": "#25336e", "texto": PAL["texto"], "suave": PAL["suave"], "mudo": PAL["mudo"],
    "azul": PAL["azul"], "verde": PAL["verde"], "ambar": PAL["ambar"], "vermelho": PAL["vermelho"],
    "turquesa": PAL["turquesa"], "campo": "#0a1030", "linha_par": "#141e4a", "selecao": "#2a4fb0",
    "botao": "#17224f", "botao_hover": "#26367c",
}


def aplicar(root) -> None:
    """Cria (ou refaz) os estilos escuros. Idempotente."""
    s = ttk.Style(root)
    c = CX
    s.configure("Cx.TFrame", background=c["fundo"])
    s.configure("Cx.Cartao.TFrame", background=c["cartao"])
    s.configure("Cx.TLabel", background=c["fundo"], foreground=c["texto"], font=(FONTE, 10))
    s.configure("Cx.Cartao.TLabel", background=c["cartao"], foreground=c["texto"], font=(FONTE, 10))
    s.configure("Cx.Rotulo.TLabel", background=c["fundo"], foreground=c["suave"], font=(FONTE, 8, "bold"))
    s.configure("Cx.CartaoRotulo.TLabel", background=c["cartao"], foreground=c["suave"], font=(FONTE, 8, "bold"))
    s.configure("Cx.Status.TLabel", background=c["cabecalho"], foreground=c["suave"], font=(FONTE, 10))

    s.configure("Cx.TEntry", padding=6, fieldbackground=c["campo"], foreground=c["texto"], insertcolor=c["texto"],
                bordercolor=c["borda"], lightcolor=c["borda"], darkcolor=c["borda"])
    s.map("Cx.TEntry", bordercolor=[("focus", c["azul"])], lightcolor=[("focus", c["azul"])],
          darkcolor=[("focus", c["azul"])], fieldbackground=[("disabled", c["fundo"])],
          foreground=[("disabled", c["mudo"])])
    s.configure("Cx.TCombobox", padding=5, fieldbackground=c["campo"], foreground=c["texto"],
                background=c["botao"], arrowcolor=c["texto"], bordercolor=c["borda"])
    s.map("Cx.TCombobox", fieldbackground=[("readonly", c["campo"])], foreground=[("readonly", c["texto"])])

    base = dict(padding=(8, 5), borderwidth=0, focusthickness=0, font=(FONTE, 9, "bold"))
    s.configure("Cx.TButton", background=c["botao"], foreground=c["texto"], **base)
    s.map("Cx.TButton", background=[("active", c["botao_hover"]), ("disabled", c["cartao"])],
          foreground=[("disabled", c["mudo"])])
    s.configure("Cx.Sel.TButton", background=c["ambar"], foreground="#10131f", **base)       # escolhido pelo teclado (setas)
    s.map("Cx.Sel.TButton", background=[("active", misturar(c["ambar"], "#ffffff", 0.2))])
    s.configure("Cx.Perigo.TButton", background=misturar(c["fundo"], c["vermelho"], 0.2), foreground="#ffb3bb", **base)
    s.map("Cx.Perigo.TButton", background=[("active", misturar(c["fundo"], c["vermelho"], 0.4))])
    s.configure("Cx.Mini.TButton", background=c["botao"], foreground=c["texto"], **dict(base, padding=(4, 1), font=(FONTE, 8, "bold")))
    s.map("Cx.Mini.TButton", background=[("active", c["botao_hover"]), ("disabled", c["cartao"])])
    forte = dict(base, padding=(12, 10), font=(FONTE, 15, "bold"))
    s.configure("Cx.Pagar.TButton", background=c["verde"], foreground="#04241a", **forte)
    s.map("Cx.Pagar.TButton", background=[("active", misturar(c["verde"], "#ffffff", 0.25)), ("disabled", c["cartao"])])
    acao = dict(base, padding=(6, 11), font=(FONTE, 10, "bold"))              # as ações do dia a dia, na coluna da direita
    s.configure("Cx.Acao.TButton", background=c["botao"], foreground=c["texto"], **acao)
    s.map("Cx.Acao.TButton", background=[("active", c["botao_hover"]), ("disabled", c["cartao"])],
          foreground=[("disabled", c["mudo"])])
    s.configure("Cx.AcaoPerigo.TButton", background=misturar(c["fundo"], c["vermelho"], 0.2), foreground="#ffb3bb", **acao)
    s.map("Cx.AcaoPerigo.TButton", background=[("active", misturar(c["fundo"], c["vermelho"], 0.4))])
    medio = dict(base, padding=(12, 9), font=(FONTE, 11, "bold"))
    s.configure("Cx.Principal.TButton", background=c["botao"], foreground=c["texto"], **medio)
    s.map("Cx.Principal.TButton", background=[("active", c["botao_hover"])])
    s.configure("Cx.Ok.TButton", background=c["verde"], foreground="#04241a", **medio)
    s.map("Cx.Ok.TButton", background=[("active", misturar(c["verde"], "#ffffff", 0.25)), ("disabled", c["cartao"])],
          foreground=[("disabled", c["mudo"])])

    for nome, altura, fonte in (("Cx", 30, 12), ("CxForma", 46, 15)):        # CxForma: linhas altas, fáceis de tocar
        s.configure(f"{nome}.Treeview", rowheight=altura, font=(FONTE, fonte), background=c["cartao"],
                    fieldbackground=c["cartao"], foreground=c["texto"], bordercolor=c["borda"], lightcolor=c["borda"],
                    darkcolor=c["borda"], borderwidth=1)
        s.configure(f"{nome}.Treeview.Heading", font=(FONTE, 9, "bold"), background=c["cabecalho"], foreground=c["suave"],
                    padding=7, relief="flat", borderwidth=0)
        s.map(f"{nome}.Treeview.Heading", background=[("active", c["cabecalho"])])
        s.map(f"{nome}.Treeview", background=[("selected", c["selecao"])], foreground=[("selected", "#ffffff")])
        for eixo in ("Vertical", "Horizontal"):
            s.configure(f"{nome}.{eixo}.TScrollbar", background=c["botao"], troughcolor=c["fundo"], bordercolor=c["fundo"],
                        arrowcolor=c["suave"], lightcolor=c["botao"], darkcolor=c["botao"], relief="flat")
            s.map(f"{nome}.{eixo}.TScrollbar", background=[("active", c["botao_hover"])])
