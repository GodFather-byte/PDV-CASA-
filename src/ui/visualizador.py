"""Janela de pré-visualização de cupons e relatórios em texto (botões Tela/Impressora do manual)."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

from src.core.relatorio import Relatorio, para_csv, para_texto
from src.ui import tema


class Visualizador(tk.Toplevel):
    def __init__(self, master, ctx, titulo: str, texto: str, nome: str = "documento", csv: str | None = None,
                 modal: bool = True, largura_chars: int | None = None):
        super().__init__(master)
        self.ctx, self.texto, self.nome, self.csv = ctx, texto, nome, csv
        self.title(titulo)
        self.configure(bg=tema.COR["fundo"])
        colunas = largura_chars or max((len(l) for l in texto.splitlines()), default=40)
        linhas = min(max(texto.count("\n") + 2, 10), 32)
        barra = ttk.Frame(self, padding=(10, 8))
        barra.pack(fill="x")
        ttk.Button(barra, text="Imprimir (Ctrl+P)", command=self.imprimir).pack(side="left")
        ttk.Button(barra, text="Salvar texto...", command=self.salvar).pack(side="left", padx=6)
        if csv is not None:
            ttk.Button(barra, text="Exportar CSV (Excel)...", command=self.salvar_csv).pack(side="left")
        ttk.Button(barra, text="Fechar (Esc)", command=self.destroy).pack(side="right")
        corpo = ttk.Frame(self, padding=(10, 0, 10, 10))
        corpo.pack(fill="both", expand=True)
        self.caixa = tk.Text(corpo, font=tema.FONTE_MONO, width=min(colunas + 1, 130), height=linhas, wrap="none",
                             bg="white", relief="solid", borderwidth=1, padx=8, pady=6)
        sy = ttk.Scrollbar(corpo, orient="vertical", command=self.caixa.yview)
        sx = ttk.Scrollbar(corpo, orient="horizontal", command=self.caixa.xview)
        self.caixa.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.caixa.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        corpo.rowconfigure(0, weight=1)
        corpo.columnconfigure(0, weight=1)
        self.caixa.insert("1.0", texto)
        self.caixa.configure(state="disabled")
        for seq in ("<Escape>", "<Return>"):
            self.bind(seq, lambda e: self.destroy())
        self.bind("<Control-p>", lambda e: self.imprimir())
        tema.centralizar(self, master.winfo_toplevel())
        self.transient(master.winfo_toplevel())
        self.caixa.focus_set()
        if modal:
            self.grab_set()
            self.wait_window(self)

    def imprimir(self) -> None:
        caminho = self.ctx.impressao.enviar(self.texto, self.nome)
        try:
            if hasattr(os, "startfile"):
                os.startfile(caminho, "print")  # type: ignore[attr-defined]
            else:
                tema.mensagem(self, f"Arquivo salvo em:\n{caminho}", "Impressão")
        except OSError as e:
            tema.erro(self, f"Não foi possível imprimir: {e}\nO texto foi salvo em:\n{caminho}")

    def salvar(self) -> None:
        caminho = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", initialfile=f"{self.nome}.txt",
                                               filetypes=[("Texto", "*.txt")])
        if caminho:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(self.texto)

    def salvar_csv(self) -> None:
        caminho = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile=f"{self.nome}.csv",
                                               filetypes=[("CSV (Excel)", "*.csv")])
        if caminho:
            with open(caminho, "w", encoding="utf-8-sig", newline="") as f:   # BOM para o Excel abrir acentos
                f.write(self.csv)


def mostrar_texto(master, ctx, titulo: str, texto: str, nome: str = "documento", modal: bool = True) -> Visualizador:
    return Visualizador(master, ctx, titulo, texto, nome, modal=modal)


def mostrar_relatorio(master, ctx, rel: Relatorio, largura: int = 80, nome: str | None = None) -> Visualizador:
    nome = nome or rel.titulo.lower().replace(" ", "_")
    return Visualizador(master, ctx, rel.titulo, para_texto(rel, largura), nome, csv=para_csv(rel), largura_chars=largura)
