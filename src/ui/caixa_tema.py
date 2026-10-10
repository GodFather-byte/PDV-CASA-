"""Visual escuro do caixa (o mesmo azul-noite do menu principal): cores e estilos ttk próprios, prefixo "Cx".

Os estilos só valem para quem os pede pelo nome (`style="Cx.TButton"`...); as outras telas continuam com o tema claro."""
from __future__ import annotations

from tkinter import ttk

from src.ui.menu_widgets import PAL, misturar

CX = {
    "fundo": PAL["fundo"], "cabecalho": PAL["cabecalho"], "cartao": PAL["cartao"], "cartao2": PAL["cartao_hover"],
    "borda": PAL["borda"], "texto": PAL["texto"], "suave": PAL["suave"], "mudo": PAL["mudo"],
    "azul": PAL["azul"], "verde": PAL["verde"], "ambar": PAL["ambar"], "vermelho": PAL["vermelho"],
    "turquesa": PAL["turquesa"], "campo": "#0b1330", "linha_par": "#16204a", "selecao": "#2a4fb0",
    "botao": "#1b2756", "botao_hover": "#2a3c80",
}
FONTE = "Segoe UI"


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

    base = dict(padding=(8, 5), borderwidth=0, focusthickness=0, font=(FONTE, 9, "bold"))
    s.configure("Cx.TButton", background=c["botao"], foreground=c["texto"], **base)
    s.map("Cx.TButton", background=[("active", c["botao_hover"]), ("disabled", c["cartao"])],
          foreground=[("disabled", c["mudo"])])
    s.configure("Cx.Sel.TButton", background=c["ambar"], foreground="#10131f", **base)       # escolhido pelo teclado (setas)
    s.map("Cx.Sel.TButton", background=[("active", misturar(c["ambar"], "#ffffff", 0.2))])
    s.configure("Cx.Perigo.TButton", background=misturar(c["botao"], c["vermelho"], 0.18), foreground="#ffb3bb", **base)
    s.map("Cx.Perigo.TButton", background=[("active", misturar(c["botao"], c["vermelho"], 0.38))])
    forte = dict(base, padding=(12, 10), font=(FONTE, 15, "bold"))
    s.configure("Cx.Pagar.TButton", background=c["verde"], foreground="#04241a", **forte)
    s.map("Cx.Pagar.TButton", background=[("active", misturar(c["verde"], "#ffffff", 0.25)), ("disabled", c["cartao"])])
    medio = dict(base, padding=(12, 9), font=(FONTE, 11, "bold"))
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
