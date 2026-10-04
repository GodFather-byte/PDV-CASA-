"""Tela de entrada: usuário e senha (manual ADM seção 1)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.controllers.turno_controller import TurnoController
from src.core import formatacao as fmt
from src.core import licenca
from src.core.erros import ErroNegocio
from src.ui import tema


class JanelaLogin(tk.Toplevel):
    """Devolve o Operador em `self.operador` (None se o usuário fechar a janela)."""

    def __init__(self, master, ctx, titulo_loja: str = "PDV"):
        super().__init__(master)
        self.ctx, self.operador = ctx, None
        self.title("Entrada no sistema")
        self.configure(bg=tema.COR["marinho"])
        self.resizable(False, False)
        quadro = tk.Frame(self, bg=tema.COR["marinho"], padx=30, pady=24)
        quadro.pack()
        tk.Label(quadro, text=titulo_loja.upper(), bg=tema.COR["marinho"], fg="white", font=("Segoe UI", 18, "bold")).pack()
        tk.Label(quadro, text="PDV - Ponto de Venda", bg=tema.COR["marinho"], fg="#9fb3e8").pack(pady=(0, 16))
        for rotulo in ("Usuário", "Senha"):
            tk.Label(quadro, text=rotulo, bg=tema.COR["marinho"], fg="white", font=tema.FONTE_B, anchor="w").pack(fill="x")
            if rotulo == "Usuário":
                self.var_usuario = tk.StringVar()
                nomes = ctx.acesso.nomes_login()
                self.ent_usuario = ttk.Combobox(quadro, textvariable=self.var_usuario, values=nomes, width=30)
                self.ent_usuario.pack(pady=(2, 10))
                if len(nomes) == 1:
                    self.var_usuario.set(nomes[0])
            else:
                self.var_senha = tk.StringVar()
                self.ent_senha = ttk.Entry(quadro, textvariable=self.var_senha, show="*", width=33)
                self.ent_senha.pack(pady=(2, 6))
        self.lbl_msg = tk.Label(quadro, text="", bg=tema.COR["marinho"], fg="#ffb4b4", font=tema.FONTE_B)
        self.lbl_msg.pack(pady=(4, 6))
        ttk.Button(quadro, text="Entrar", command=self.entrar).pack(fill="x")
        if licenca.exigida(ctx.banco):
            ttk.Button(quadro, text="Código de licença...", command=self.pedir_licenca).pack(fill="x", pady=(6, 0))
        self.ent_usuario.bind("<Return>", lambda e: self.ent_senha.focus_set())
        self.ent_senha.bind("<Return>", lambda e: self.entrar())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda e: self.destroy())
        tema.centralizar(self)
        self.lift()
        tema.modalizar(self)
        (self.ent_senha if self.var_usuario.get() else self.ent_usuario).focus_set()

    def entrar(self) -> None:
        estado = licenca.estado(self.ctx.banco)
        turno = TurnoController(self.ctx.banco).atual()
        if estado.bloqueia and not licenca.turno_vale_como_isencao(self.ctx.banco, turno):
            # Com um turno recente aberto a loja continua operando (só avisa); sem ele, exige a renovação.
            self.ctx.banco.log("licenca_bloqueio", estado.mensagem)
            self.lbl_msg.configure(text=estado.mensagem)
            if not self.pedir_licenca(estado.mensagem):
                return
            estado = licenca.estado(self.ctx.banco)
        senha = self.var_senha.get()
        try:
            operador = self.ctx.acesso.autenticar(self.var_usuario.get(), senha)
        except ErroNegocio as e:
            self.lbl_msg.configure(text=str(e), fg="#ffb4b4")
            self.var_senha.set("")
            self.ent_senha.focus_set()
            return
        if self.ctx.acesso.precisa_trocar_senha(operador, senha) and not self.trocar_senha(operador):
            self.lbl_msg.configure(text="Troque a senha para entrar no sistema.", fg="#ffb4b4")
            self.var_senha.set("")
            self.ent_senha.focus_set()
            return
        self.operador = operador
        if licenca.exigida(self.ctx.banco):
            licenca.registrar_uso(self.ctx.banco)
        if estado.bloqueia:
            tema.mensagem(self, f"{estado.mensagem}\nO turno aberto pode ser trabalhado e fechado normalmente; "
                                "a próxima entrada exigirá o código de renovação.", "Licença", "aviso")
        elif estado.avisa:
            tema.mensagem(self, estado.mensagem, "Licença", "aviso")
        self.destroy()

    def trocar_senha(self, operador) -> bool:
        """Senha igual ao nome (a de fábrica é ADM/ADM): pede uma nova, duas vezes. Devolve False se o usuário desistir."""
        nova = tema.pedir_texto(
            self, "Troque a senha", f"A senha de {operador.nome} é igual ao nome e qualquer um pode adivinhá-la.\n"
            "Digite uma senha nova (até 10 letras ou números):", senha=True, largura=22,
            validar=lambda v: self.ctx.acesso.validar_nova_senha(operador, v))
        if nova is None:
            return False

        def conferir(v: str) -> str:
            if v.upper() != nova.upper():
                raise ErroNegocio("As senhas não conferem.")
            return v
        if tema.pedir_texto(self, "Troque a senha", "Digite a senha nova de novo:", senha=True, largura=22,
                            validar=conferir) is None:
            return False
        self.ctx.acesso.trocar_senha(operador, nova)
        tema.mensagem(self, "Senha trocada. Use a senha nova nas próximas entradas.", "Senha")
        return True

    def pedir_licenca(self, motivo: str = "") -> bool:
        """Pede o código de licença e o ativa. Devolve True se a licença ficou liberada para entrar."""
        texto = (f"{motivo}\n\n" if motivo else "") + "Cole o código de licença fornecido:"
        codigo = tema.pedir_texto(self, "Código de licença", texto, largura=64)
        if not codigo:
            return False
        try:
            lic = licenca.ativar(self.ctx.banco, codigo)
        except ErroNegocio as e:
            self.lbl_msg.configure(text=str(e), fg="#ffb4b4")
            return False
        self.lbl_msg.configure(text=f"Licença ativada até {fmt.fmt_data(lic['expira_em'].isoformat())}.", fg="#5be39a")
        return not licenca.estado(self.ctx.banco).bloqueia
