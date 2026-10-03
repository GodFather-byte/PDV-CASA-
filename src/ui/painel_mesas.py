"""Faixa de ícones com as mesas e comandas abertas, no rodapé do caixa.

Esc (ou F4) leva ao "marcar comanda": o painel aparece e o foco vai para o campo da posição. Cada posição aberta é um
ícone com o número e o total embaixo: mesinha com garrafa e copo (mesa consumindo), cartão (comanda consumindo), conta
sobre a bandeja (conta já enviada ao cliente) e um relógio quando está parada além do tempo de inatividade.
O primeiro ícone é o balcão. Tudo é desenhado com formas do Tk, sem arquivos de imagem.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from src.core import formatacao as fmt
from src.ui import tema

LARGURA, ALTURA, MARGEM = 74, 72, 6
LINHAS_VISIVEIS = 2           # acima disso a faixa rola, para não tomar a tela do caixa
RESERVA_BARRA = 18            # espaço da barra de rolagem (sobreposta), reservado sempre para a disposição não oscilar
LARGURA_PADRAO = 900          # antes de a janela ser mostrada o Tk ainda não sabe a largura real

ESTADOS = {
    "consumindo": {"fundo": "#ffffff", "borda": "#9fb3e0", "texto": tema.COR["marinho"]},
    "parada": {"fundo": "#fdeaea", "borda": "#e39a9a", "texto": tema.COR["perigo"]},
    "conta": {"fundo": "#fff3dc", "borda": "#e2b25a", "texto": "#8a5a00"},
    "balcao": {"fundo": "#eaf6ef", "borda": "#8cc8a5", "texto": "#14623f"},
}


def montar_tiles(mesas: list[dict], balcao: dict | None = None) -> list[dict]:
    """Modelo dos ícones, sem Tk: o balcão primeiro e depois as mesas e comandas, na ordem recebida.

    `mesas` é o que `CaixaController.mesas()` devolve; `balcao`, a venda de balcão em andamento (ou None)."""
    tiles = [{"chave": "0", "rotulo": "Balcão", "tipo": "balcao", "estado": "balcao",
              "total": fmt.fmt_num(balcao["total_cent"]) if balcao and balcao["total_cent"] else "", "minutos": 0}]
    for m in mesas:
        if m["status"] == "conta_enviada":
            estado = "conta"
        elif m["inativa"]:
            estado = "parada"
        else:
            estado = "consumindo"
        tiles.append({"chave": m["rotulo"], "rotulo": m["rotulo"], "tipo": "comanda" if m["comanda"] else "mesa",
                      "estado": estado, "total": fmt.fmt_num(m["total_cent"]), "minutos": m["minutos_parada"]})
    return tiles


# ------------------------------------------------------------------ ícones (caixa de 36 x 32 px)
def _cartao(c: tk.Canvas, x1, y1, x2, y2, raio: int = 8, **kw) -> int:
    pontos = [x1 + raio, y1, x2 - raio, y1, x2, y1, x2, y1 + raio, x2, y2 - raio, x2, y2,
              x2 - raio, y2, x1 + raio, y2, x1, y2, x1, y2 - raio, x1, y1 + raio, x1, y1]
    return c.create_polygon(pontos, smooth=True, **kw)


def _icone_mesa(c: tk.Canvas, x: int, y: int, tags: tuple) -> None:
    c.create_rectangle(x + 1, y + 17, x + 35, y + 22, fill="#2f87b0", outline="#1b556f", tags=tags)           # tampo
    for lado in (5, 27):
        c.create_rectangle(x + lado, y + 22, x + lado + 4, y + 31, fill="#1b556f", outline="", tags=tags)    # pernas
    c.create_rectangle(x + 11, y + 2, x + 14, y + 8, fill="#2e8b57", outline="#1d5c39", tags=tags)           # gargalo
    c.create_rectangle(x + 9, y + 8, x + 16, y + 17, fill="#2e8b57", outline="#1d5c39", tags=tags)           # garrafa
    c.create_polygon(x + 21, y + 8, x + 31, y + 8, x + 29, y + 17, x + 23, y + 17,
                     fill="#f6c445", outline="#a97b12", tags=tags)                                           # copo
    c.create_rectangle(x + 21, y + 5, x + 31, y + 8, fill="#ffffff", outline="#cfd6e6", tags=tags)           # espuma


def _icone_comanda(c: tk.Canvas, x: int, y: int, tags: tuple) -> None:
    c.create_rectangle(x + 8, y + 1, x + 28, y + 31, fill="#ffffff", outline="#3a5bb5", width=2, tags=tags)
    c.create_rectangle(x + 9, y + 2, x + 27, y + 9, fill="#3a5bb5", outline="", tags=tags)
    c.create_oval(x + 16, y + 3, x + 20, y + 7, fill="#ffffff", outline="", tags=tags)                       # furo
    for i, comprimento in enumerate((14, 14, 8)):
        c.create_line(x + 12, y + 14 + i * 5, x + 12 + comprimento, y + 14 + i * 5, fill="#8da2d6", width=2, tags=tags)


def _icone_conta(c: tk.Canvas, x: int, y: int, tags: tuple) -> None:
    c.create_oval(x + 1, y + 21, x + 35, y + 31, fill="#d99a2b", outline="#8a5a00", tags=tags)               # bandeja
    c.create_oval(x + 4, y + 22, x + 32, y + 29, fill="#f2c566", outline="", tags=tags)
    c.create_rectangle(x + 10, y + 2, x + 26, y + 25, fill="#ffffff", outline="#8a5a00", tags=tags)          # conta
    for i, comprimento in enumerate((10, 10, 6)):
        c.create_line(x + 13, y + 7 + i * 5, x + 13 + comprimento, y + 7 + i * 5, fill="#b98a3a", width=2, tags=tags)


def _icone_balcao(c: tk.Canvas, x: int, y: int, tags: tuple) -> None:
    c.create_polygon(x + 2, y + 3, x + 34, y + 3, x + 31, y + 12, x + 5, y + 12,
                     fill="#d9534f", outline="#9c2f2c", tags=tags)                                           # toldo
    for deslocamento in (9, 21):
        c.create_polygon(x + deslocamento, y + 3, x + deslocamento + 6, y + 3,
                         x + deslocamento + 5, y + 12, x + deslocamento - 1, y + 12, fill="#ffffff", outline="", tags=tags)
    c.create_rectangle(x + 5, y + 12, x + 31, y + 31, fill="#3d9a6a", outline="#256a45", tags=tags)
    c.create_text(x + 18, y + 22, text="$", fill="#ffffff", font=("Segoe UI", 10, "bold"), tags=tags)


def _icone_relogio(c: tk.Canvas, x: int, y: int, tags: tuple) -> None:
    cx, cy, cor = x + 30, y + 7, tema.COR["perigo"]
    c.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill="#ffffff", outline=cor, width=2, tags=tags)
    c.create_line(cx, cy, cx, cy - 4, fill=cor, width=2, tags=tags)
    c.create_line(cx, cy, cx + 3, cy, fill=cor, width=2, tags=tags)


ICONES = {"mesa": _icone_mesa, "comanda": _icone_comanda, "conta": _icone_conta, "balcao": _icone_balcao}


class PainelMesas(ttk.Frame):
    """Os ícones, a navegação por teclado (setas, Enter, T, digitar o número) e o clique do mouse.

    Quem usa só informa o que fazer ao escolher um ícone (`ao_escolher`), ao pedir para transferir outras posições
    para ele (`ao_transferir`), ao voltar para o campo da posição (`ao_voltar`) e ao digitar um número ou a letra C
    com o foco no painel (`ao_digitar`, que passa o caractere ao campo da posição)."""

    def __init__(self, master, ao_escolher: Callable[[str], None], ao_transferir: Callable[[str], None],
                 ao_voltar: Callable[[], None], ao_digitar: Callable[[str], None]):
        super().__init__(master)
        self._ao_escolher, self._ao_transferir = ao_escolher, ao_transferir
        self._ao_voltar, self._ao_digitar = ao_voltar, ao_digitar
        self._tiles: list[dict] = []
        self._atual: str | None = None        # a posição que está na tela do caixa (borda grossa)
        self._cursor: str | None = None       # onde o teclado está (pontilhado, só com o foco no painel)
        self._com_foco = False
        self._assinatura = None
        self._largura = 0
        self._altura_total = 0
        self._por_linha = 1
        self._id_redesenho = None

        cabecalho = ttk.Frame(self)
        cabecalho.pack(fill="x")
        ttk.Label(cabecalho, text="Mesas e comandas abertas", style="Rotulo.TLabel").pack(side="left")
        ttk.Label(cabecalho, text="Esc marca a comanda   |   setas + Enter escolhem   |   T transfere outras para a escolhida"
                                  "   |   0 = balcão", font=("Segoe UI", 8), foreground=tema.COR["suave"]).pack(side="right")
        c = self.canvas = tk.Canvas(self, height=ALTURA + 2 * MARGEM, bg=tema.COR["fundo"], bd=0, takefocus=True,
                                    highlightthickness=1, highlightbackground=tema.COR["borda"],
                                    highlightcolor=tema.COR["marinho2"], yscrollincrement=ALTURA)
        c.pack(fill="x")
        self.barra = ttk.Scrollbar(c, orient="vertical", command=c.yview)    # sobreposta ao canvas (place)
        c.configure(yscrollcommand=self.barra.set)
        c.bind("<Configure>", self._ao_configurar)
        c.bind("<MouseWheel>", self._roda)
        c.bind("<FocusIn>", lambda ev: self._foco(True))
        c.bind("<FocusOut>", lambda ev: self._foco(False))
        c.bind("<Key>", self._tecla)
        c.bind("<Button-1>", self._clique_fundo)
        c.tag_bind("tile", "<Button-1>", self._clique)
        c.tag_bind("tile", "<Enter>", lambda ev: c.configure(cursor="hand2"))
        c.tag_bind("tile", "<Leave>", lambda ev: c.configure(cursor=""))

    # -------------------------------------------------------------- dados
    def atualizar(self, mesas: list[dict], balcao: dict | None = None, atual: str | None = None) -> None:
        tiles = montar_tiles(mesas, balcao)
        assinatura = ([(t["chave"], t["tipo"], t["estado"], t["total"]) for t in tiles], atual)
        if assinatura == self._assinatura:
            return
        self._assinatura = assinatura
        self._tiles, self._atual = tiles, atual
        if self._cursor not in {t["chave"] for t in tiles}:
            self._cursor = atual
        self._desenhar()

    def tiles(self) -> list[dict]:
        return [dict(t) for t in self._tiles]

    def cursor(self) -> str | None:
        return self._cursor

    def focar(self, chave: str | None = None) -> None:
        """Põe o foco do teclado no painel, no ícone `chave` (ou no atual, ou no primeiro)."""
        chaves = [t["chave"] for t in self._tiles]
        for candidata in (chave, self._cursor, self._atual):
            if candidata in chaves:
                self._cursor = candidata
                break
        else:
            self._cursor = chaves[0] if chaves else None
        self._com_foco = True
        self.canvas.focus_set()
        self._marcar_cursor()
        self._garantir_visivel(self._cursor)

    # ------------------------------------------------------------- desenho
    def _ao_configurar(self, ev) -> None:
        if ev.width != self._largura:         # só a largura muda a disposição dos ícones
            self._agendar()

    def _agendar(self) -> None:
        if self._id_redesenho is None:
            self._id_redesenho = self.after_idle(self._redesenhar)

    def _redesenhar(self) -> None:
        self._id_redesenho = None
        try:
            self._desenhar()
        except tk.TclError:                    # janela destruída antes do redesenho
            pass

    def destroy(self) -> None:
        if self._id_redesenho is not None:
            try:
                self.after_cancel(self._id_redesenho)
            except tk.TclError:
                pass
        super().destroy()

    def _desenhar(self) -> None:
        c = self.canvas
        c.delete("all")
        largura = c.winfo_width() if c.winfo_width() > 1 else LARGURA_PADRAO
        self._largura = largura
        self._por_linha = max(1, (largura - 2 * MARGEM - RESERVA_BARRA) // LARGURA)
        linhas = max(1, -(-len(self._tiles) // self._por_linha))
        self._altura_total = linhas * ALTURA + 2 * MARGEM
        # com rolagem, a margem de baixo some: senão o topo da linha seguinte aparece cortado
        visivel = min(linhas, LINHAS_VISIVEIS) * ALTURA + (2 * MARGEM if linhas <= LINHAS_VISIVEIS else MARGEM)
        c.configure(height=visivel, scrollregion=(0, 0, largura, self._altura_total))
        if self._altura_total > visivel:
            self.barra.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")
        else:
            self.barra.place_forget()
            c.yview_moveto(0)
        for i, t in enumerate(self._tiles):
            self._desenhar_tile(i, t)
        self._marcar_cursor()

    def _posicao(self, i: int) -> tuple[int, int]:
        return MARGEM + (i % self._por_linha) * LARGURA, MARGEM + (i // self._por_linha) * ALTURA

    def _desenhar_tile(self, i: int, t: dict) -> None:
        c = self.canvas
        x, y = self._posicao(i)
        marca = (f"t:{t['chave']}", "tile")        # o prefixo evita que "5" seja tomado por número de item do Tk
        estilo = ESTADOS[t["estado"]]
        atual = t["chave"] == self._atual
        _cartao(c, x + 3, y + 3, x + LARGURA - 3, y + ALTURA - 3, fill=estilo["fundo"],
                outline=tema.COR["marinho2"] if atual else estilo["borda"], width=3 if atual else 1,
                tags=marca + ("fundo",))
        ox, oy = x + (LARGURA - 36) // 2, y + 7
        tipo_icone = "conta" if t["estado"] == "conta" else t["tipo"]
        ICONES[tipo_icone](c, ox, oy, marca + ("icone", f"icone:{tipo_icone}"))
        if t["estado"] == "parada":
            _icone_relogio(c, ox, oy, marca + ("relogio",))
        meio = x + LARGURA // 2
        c.create_text(meio, y + 46, text=t["rotulo"], font=("Segoe UI", 11, "bold"), fill=estilo["texto"], tags=marca + ("rotulo",))
        if t["total"]:
            c.create_text(meio, y + 60, text=t["total"], font=("Segoe UI", 8), fill=tema.COR["suave"], tags=marca + ("total",))

    def _marcar_cursor(self) -> None:
        c = self.canvas
        c.delete("cursor")
        chaves = [t["chave"] for t in self._tiles]
        if self._com_foco and self._cursor in chaves:
            x, y = self._posicao(chaves.index(self._cursor))
            c.create_rectangle(x + 1, y + 1, x + LARGURA - 1, y + ALTURA - 1, outline=tema.COR["aviso"], width=2,
                               dash=(4, 3), tags=("cursor",))

    def _garantir_visivel(self, chave: str | None) -> None:
        chaves = [t["chave"] for t in self._tiles]
        if chave not in chaves or self._altura_total <= 0:
            return
        topo = MARGEM + (chaves.index(chave) // self._por_linha) * ALTURA
        base = topo + ALTURA
        janela_topo = self.canvas.canvasy(0)
        janela_base = janela_topo + self.canvas.winfo_height()
        if topo < janela_topo:
            self.canvas.yview_moveto(max(0.0, (topo - MARGEM) / self._altura_total))
        elif base + MARGEM > janela_base:
            self.canvas.yview_moveto(max(0.0, (base + MARGEM - self.canvas.winfo_height()) / self._altura_total))

    # --------------------------------------------------- mouse e teclado
    def _chave_do_item_atual(self) -> str | None:
        itens = self.canvas.find_withtag("current")
        for marca in self.canvas.gettags(itens[0]) if itens else ():
            if marca.startswith("t:"):
                return marca[2:]
        return None

    def _clique(self, _=None) -> None:
        chave = self._chave_do_item_atual()
        if chave is not None:
            self._ao_escolher(chave)

    def _clique_fundo(self, _=None) -> None:
        if self._chave_do_item_atual() is None:       # clicou no espaço vazio: leva o teclado para cá
            self.focar()

    def _roda(self, ev) -> None:
        if self._altura_total > self.canvas.winfo_height():
            self.canvas.yview_scroll(-1 if ev.delta > 0 else 1, "units")

    def _foco(self, com_foco: bool) -> None:
        self._com_foco = com_foco
        if com_foco and self._cursor is None:
            self._cursor = self._atual
        self._marcar_cursor()

    def _mover(self, passo: int) -> None:
        chaves = [t["chave"] for t in self._tiles]
        if not chaves:
            return
        i = chaves.index(self._cursor) if self._cursor in chaves else 0
        self._cursor = chaves[max(0, min(len(chaves) - 1, i + passo))]
        self._marcar_cursor()
        self._garantir_visivel(self._cursor)

    def _tecla(self, ev) -> str | None:
        k = ev.keysym
        chaves = [t["chave"] for t in self._tiles]
        if k in ("Left", "Right"):
            self._mover(-1 if k == "Left" else 1)
        elif k == "Down":
            self._mover(self._por_linha)
        elif k == "Up":
            if self._cursor in chaves and chaves.index(self._cursor) < self._por_linha:
                self._ao_voltar()              # no alto da faixa, a seta para cima volta ao campo da posição
            else:
                self._mover(-self._por_linha)
        elif k in ("Home", "End"):
            self._mover(-len(chaves) if k == "Home" else len(chaves))
        elif k in ("Return", "KP_Enter", "space"):
            if self._cursor:
                self._ao_escolher(self._cursor)
        elif k == "Escape":
            self._ao_voltar()
        elif k in ("t", "T"):
            if self._cursor and self._cursor != "0":
                self._ao_transferir(self._cursor)
        elif ev.char and (ev.char.isdigit() or ev.char in "cCmM"):
            self._ao_digitar(ev.char)
        else:
            return None                        # as teclas F continuam valendo (são tratadas na janela)
        return "break"
