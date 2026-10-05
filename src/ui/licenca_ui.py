"""Telas e agendamento do licenciamento: chave na primeira execução, verificação a cada 4 horas, faixa de aviso, tela de
bloqueio e a tela "Licença". A regra de quando bloquear vive em src/core/servico_licenca.py; aqui só se mostra.

A rede só roda na thread do serviço; a tela consulta o resultado com `after` e nunca espera por ela.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.core.servico_licenca import INTERVALO_SEGUNDOS, ServicoLicenca
from src.ui import tema

SONDAGEM_MS = 300
REAVALIAR_MS = 15_000     # bloqueio adiado por causa de uma venda em andamento: olha de novo a cada 15 s


def pedir_chave(master, servico: ServicoLicenca, motivo: str = "") -> bool:
    """Pede e grava a chave de licença. False se o operador desistir."""
    texto = (f"{motivo}\n\n" if motivo else "") + "Digite a chave de licença fornecida:"

    def validar(v: str) -> str:
        if not "".join(v.split()):
            raise ValueError("Informe a chave de licença.")
        return v
    chave = tema.pedir_texto(master, "Chave de licença", texto, largura=46, validar=validar)
    if chave is None:
        return False
    servico.salvar_chave(chave)
    return True


class GuardaLicenca:
    """Liga o serviço à janela principal: primeira execução, checagem ao abrir e a cada 4 h, faixa e bloqueio."""

    def __init__(self, app):
        self.app = app
        self.servico = ServicoLicenca(app.banco, extra_em_andamento=self._caixa_aberto)
        self._bloqueio_aberto = False
        self._reavaliacao = None

    def _caixa_aberto(self) -> bool:
        """Tela do caixa aberta conta como venda em andamento (o operador pode estar digitando o primeiro item)."""
        try:
            return any(type(w).__name__ == "JanelaCaixa" for w in self.app.root.winfo_children())
        except tk.TclError:
            return False

    # ------------------------------------------------------------ ciclo
    def iniciar(self) -> None:
        """Ao abrir o PDV: chave (se faltar) e a primeira verificação. Volta na hora; o resultado chega depois."""
        if not self.servico.ativo:
            return
        if not self.servico.chave():
            pedir_chave(self.app.root, self.servico, "Primeira execução: este caixa ainda não tem chave de licença.")
        self.verificar()
        self._agendar()

    def _agendar(self) -> None:
        self.app.root.after(INTERVALO_SEGUNDOS * 1000, self._periodica)

    def _periodica(self) -> None:
        self.verificar()
        self._agendar()

    def verificar(self) -> None:
        if self.servico.iniciar_verificacao() or self.servico.verificando:
            self._sondar()

    def _sondar(self) -> None:
        try:
            if self.servico.coletar() or not self.servico.verificando:
                self.concluir()
            else:
                self.app.root.after(SONDAGEM_MS, self._sondar)
        except tk.TclError:
            pass                                      # janela principal já fechou

    def concluir(self) -> None:
        self.atualizar_faixa()
        self.avaliar()

    def avaliar(self) -> None:
        """Mostra o bloqueio se for permitido agora; com venda em andamento, adia e olha de novo depois."""
        s = self.servico
        if not s.bloqueado or self._bloqueio_aberto:
            return
        try:
            if s.bloqueio_pendente:
                self._mostrar_bloqueio()
            elif self._reavaliacao is None:
                self._reavaliacao = self.app.root.after(REAVALIAR_MS, self._reavaliar)
        except tk.TclError:
            pass

    def _reavaliar(self) -> None:
        self._reavaliacao = None
        self.avaliar()

    # ------------------------------------------------------------ telas
    def atualizar_faixa(self) -> None:
        """Faixa discreta e não bloqueante no painel do menu (mensalidade em atraso)."""
        lbl = getattr(self.app, "lbl_licenca", None)
        if lbl is None:
            return
        try:
            aviso = self.servico.aviso
            if not aviso:
                lbl.pack_forget()
            else:
                lbl.configure(text=aviso)
                if not lbl.winfo_ismapped():
                    lbl.pack(anchor="w", before=self.app.lbl_backup, pady=(0, 6))
        except tk.TclError:
            pass

    def _mostrar_bloqueio(self) -> None:
        root = self.app.root
        anterior = root.grab_current()
        self._bloqueio_aberto = True
        try:
            janela = JanelaBloqueio(root, self.servico)
            root.wait_window(janela)
        finally:
            self._bloqueio_aberto = False
        if janela.saiu:
            try:
                root.destroy()
            except tk.TclError:
                pass
            return
        try:
            if anterior is not None and anterior.winfo_exists():
                anterior.grab_set()                    # devolve o foco modal à tela de login, se ela estava aberta
        except tk.TclError:
            pass
        self.atualizar_faixa()

    def abrir_status(self) -> None:
        abrir_status(self.app.root, self)


class JanelaBloqueio(tk.Toplevel):
    """Tela cheia de bloqueio. Só fecha com a licença liberada (ou saindo do programa)."""

    def __init__(self, master, servico: ServicoLicenca):
        super().__init__(master)
        self.servico, self.saiu = servico, False
        self.title("Licença")
        self.configure(bg=tema.COR["marinho"])
        self.resizable(False, False)
        quadro = tk.Frame(self, bg=tema.COR["marinho"], padx=40, pady=30)
        quadro.pack()
        tk.Label(quadro, text="Licença não liberada", bg=tema.COR["marinho"], fg="white", font=("Segoe UI", 20, "bold")).pack()
        self.lbl_motivo = tk.Label(quadro, bg=tema.COR["marinho"], fg="#ffd24d", font=tema.FONTE_G, wraplength=520, justify="center")
        self.lbl_motivo.pack(pady=(14, 10))
        tk.Label(quadro, text=f"Suporte: {servico.contato_suporte()}", bg=tema.COR["marinho"], fg="#d4dcf5",
                 font=tema.FONTE, wraplength=520, justify="center").pack()
        tk.Label(quadro, text=f"ID deste computador: {servico.machine_id()}", bg=tema.COR["marinho"], fg="#9fb3e8",
                 font=tema.FONTE_MONO).pack(pady=(10, 14))
        self.lbl_estado = tk.Label(quadro, text="", bg=tema.COR["marinho"], fg="white", font=tema.FONTE_B)
        self.lbl_estado.pack(pady=(0, 8))
        barra = tk.Frame(quadro, bg=tema.COR["marinho"])
        barra.pack()
        self.btn_tentar = ttk.Button(barra, text="Tentar novamente", command=self.tentar)
        self.btn_tentar.pack(side="left", padx=4)
        self.btn_chave = ttk.Button(barra, text="Informar outra chave", command=self.outra_chave)
        self.btn_chave.pack(side="left", padx=4)
        ttk.Button(barra, text="Sair do programa", command=self.sair).pack(side="left", padx=4)
        self.protocol("WM_DELETE_WINDOW", self.sair)
        self.atualizar_motivo()
        tema.centralizar(self)
        self.lift()
        tema.modalizar(self)
        self.btn_tentar.focus_set()

    def atualizar_motivo(self) -> None:
        self.lbl_motivo.configure(text=self.servico.mensagem_bloqueio())

    def tentar(self) -> None:
        self.btn_tentar.state(["disabled"])
        self.lbl_estado.configure(text="Verificando a licença...")
        self.servico.iniciar_verificacao()
        self._sondar()

    def _sondar(self) -> None:
        try:
            if not self.winfo_exists():
                return
            if self.servico.coletar() or not self.servico.verificando:
                self.btn_tentar.state(["!disabled"])
                self.lbl_estado.configure(text="")
                if self.servico.bloqueado:
                    self.atualizar_motivo()
                    self.lbl_estado.configure(text="Ainda não foi possível liberar a licença.")
                else:
                    self.destroy()
            else:
                self.after(SONDAGEM_MS, self._sondar)
        except tk.TclError:
            pass

    def outra_chave(self) -> None:
        if pedir_chave(self, self.servico):
            self.tentar()

    def sair(self) -> None:
        self.saiu = True
        self.destroy()


def abrir_status(master, guarda: GuardaLicenca) -> None:
    """Tela "Licença": status, licença mascarada (só os 4 últimos caracteres) e machine_id para conferência."""
    s = guarda.servico
    dlg = tema.Dialogo(master, "Licença")
    corpo = dlg.corpo
    ttk.Label(corpo, text="Status", style="Rotulo.TLabel").pack(anchor="w")
    lbl_status = ttk.Label(corpo, text=s.status_texto(), wraplength=440, justify="left")
    lbl_status.pack(anchor="w", pady=(0, 8))
    ttk.Label(corpo, text="Licença", style="Rotulo.TLabel").pack(anchor="w")
    lbl_chave = ttk.Label(corpo, text=s.chave_mascarada())
    lbl_chave.pack(anchor="w", pady=(0, 8))
    ttk.Label(corpo, text="ID da máquina (machine_id)", style="Rotulo.TLabel").pack(anchor="w")
    var_id = tk.StringVar(value=s.machine_id())
    linha = ttk.Frame(corpo)
    linha.pack(fill="x", pady=(2, 8))
    ttk.Entry(linha, textvariable=var_id, state="readonly", width=40).pack(side="left", fill="x", expand=True)

    def copiar() -> None:
        dlg.clipboard_clear()
        dlg.clipboard_append(var_id.get())
    ttk.Button(linha, text="Copiar", command=copiar).pack(side="left", padx=(6, 0))
    ttk.Label(corpo, text=f"Suporte: {s.contato_suporte()}", wraplength=440, justify="left").pack(anchor="w", pady=(0, 8))
    barra = ttk.Frame(corpo)
    barra.pack(fill="x", pady=(6, 0))

    def atualizar() -> None:
        lbl_status.configure(text=s.status_texto())
        lbl_chave.configure(text=s.chave_mascarada())

    def verificar() -> None:
        if not s.ativo:
            return
        s.iniciar_verificacao()
        lbl_status.configure(text="Verificando...")
        acompanhar()

    def acompanhar() -> None:
        try:
            if not dlg.winfo_exists():
                return
            if s.coletar() or not s.verificando:
                atualizar()
                guarda.concluir()
            else:
                dlg.after(SONDAGEM_MS, acompanhar)
        except tk.TclError:
            pass

    def trocar() -> None:
        if pedir_chave(dlg, s):
            atualizar()
            verificar()
    ttk.Button(barra, text="Fechar", command=dlg.cancelar).pack(side="right")
    ttk.Button(barra, text="Alterar chave...", command=trocar).pack(side="right", padx=(0, 8))
    ttk.Button(barra, text="Verificar agora", command=verificar).pack(side="right", padx=(0, 8))
    dlg.mostrar()
