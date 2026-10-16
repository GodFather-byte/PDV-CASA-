"""Caixa em PySide6 (piloto opt-in). Usa o MESMO fluxo de venda do caixa clássico: tudo passa pelo `CaixaController` e pelo
`TurnoController` do contexto; esta tela só lê o que o operador digita, confirma e mostra o resultado.

O que já funciona aqui: abertura do turno (fundo de caixa), venda de balcão, chamar mesa ou comanda (e retomar as abertas),
lançar produto por código, código de barras, atalho ou nome com quantidade, cancelar item, receber pagamentos (troco e
contra-vale), fechar a venda (cupom), cancelar a venda e trocar o turno. Cancelamentos pedem a senha do supervisor quando
a configuração exige, como no caixa clássico.

O que ainda NÃO foi migrado fica bloqueado com aviso (use o caixa clássico): produto dividido em partes, comissão das
garotas (código 50), saída sem consumo (1002), desconto e serviço manual, observação, transferência, pré-conta, caderneta,
entrega, sangria, gaveta e balança.
"""
from __future__ import annotations

import re
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from src.core import formatacao as fmt
from src.core.erros import ErroNegocio
from src.core.posicao import exemplos, parece_posicao, rotulo_do_campo
from src.core.posicao import nome as nome_posicao
from src.hardware.impressora_termica import ErroImpressao
from src.ui.caixa_pagamento import LIMITE_TROCO_CENT, ler_valor_pagamento

PAGINA_SEM_OPERADOR, PAGINA_ABERTURA, PAGINA_VENDA, PAGINA_FECHAMENTO = range(4)
TENTATIVAS_SUPERVISOR = 3
MSG_CLASSICO = "Esta operação ainda não foi migrada para o caixa novo. Use o caixa clássico."
VERDE, AMBAR, VERMELHO = "#1f7a3d", "#a15c00", "#b32020"

ESTILO = """
QWidget#fundo { background: #f4f5f7; }
QFrame#cartao { background: #ffffff; border: 1px solid #d5d9e0; border-radius: 6px; }
QLabel#titulo { font-size: 16pt; font-weight: bold; color: #1d2733; }
QLabel#total { font-size: 28pt; font-weight: bold; color: #1d2733; }
QLabel#troco { font-size: 16pt; font-weight: bold; color: #1f5fb3; }
QLabel#mudo { color: #5b6573; }
QLabel#alerta { color: #a15c00; font-weight: bold; }
QLabel#status { padding: 4px; }
QPushButton { padding: 6px 12px; }
QPushButton#primario { background: #1f7a3d; color: white; font-weight: bold; border-radius: 4px; padding: 8px 14px; }
QPushButton#perigo { background: #b32020; color: white; border-radius: 4px; padding: 6px 12px; }
QPushButton:disabled { background: #c9ced6; color: #6b7480; }
"""


def _fmt_qtd(q) -> str:
    """Quantidade com até 4 casas, sem zeros sobrando: 1 -> '1', 0.5 -> '0,5', 1.2345 -> '1,2345'."""
    texto = fmt.fmt_qtd(q, fmt.CASAS_QTD)
    return texto.rstrip("0").rstrip(",") if "," in texto else texto


def ler_dinheiro(texto: str, permitir_zero: bool = False) -> int:
    """Valor digitado -> centavos, com as mesmas proteções do pagamento do caixa clássico (sem letras, sinal, 1e5...).
    Com `permitir_zero`, vazio ou zero valem 0 (fundo de caixa ou gaveta vazia)."""
    s = (texto or "").strip()
    if permitir_zero and (not s or re.fullmatch(r"(?:R\$\s*)?0+(?:[.,]0{1,2})?", s)):
        return 0
    return ler_valor_pagamento(s)


def _vivo(widget) -> bool:
    try:
        from shiboken6 import isValid
    except ImportError:          # pragma: no cover - shiboken6 vem junto com o PySide6
        return True
    return isValid(widget)


class Dialogos:
    """Janelas de pergunta do caixa (todas em português). Os testes trocam por uma versão roteirizada."""

    def __init__(self, pai: QWidget):
        self.pai = pai

    def _mensagem(self, icone, titulo: str, texto: str) -> None:
        caixa = QMessageBox(icone, titulo, texto, QMessageBox.NoButton, self.pai)
        caixa.addButton("OK", QMessageBox.AcceptRole)
        caixa.exec()

    def aviso(self, titulo: str, texto: str) -> None:
        self._mensagem(QMessageBox.Warning, titulo, texto)

    def erro(self, titulo: str, texto: str) -> None:
        self._mensagem(QMessageBox.Critical, titulo, texto)

    def confirmar(self, titulo: str, texto: str, padrao_sim: bool = True) -> bool:
        caixa = QMessageBox(QMessageBox.Question, titulo, texto, QMessageBox.NoButton, self.pai)
        sim = caixa.addButton("Sim", QMessageBox.YesRole)
        nao = caixa.addButton("Não", QMessageBox.NoRole)
        caixa.setDefaultButton(sim if padrao_sim else nao)
        caixa.setEscapeButton(nao)
        caixa.exec()
        return caixa.clickedButton() is sim

    def _entrada(self, titulo: str, rotulo: str) -> QInputDialog:
        dlg = QInputDialog(self.pai)
        dlg.setWindowTitle(titulo)
        dlg.setLabelText(rotulo)
        dlg.setOkButtonText("OK")
        dlg.setCancelButtonText("Cancelar")
        return dlg

    def pedir_texto(self, titulo: str, rotulo: str, senha: bool = False, padrao: str = "") -> str | None:
        dlg = self._entrada(titulo, rotulo)
        dlg.setTextValue(padrao)
        dlg.setTextEchoMode(QLineEdit.Password if senha else QLineEdit.Normal)
        return dlg.textValue() if dlg.exec() == QDialog.Accepted else None

    def escolher(self, titulo: str, rotulo: str, opcoes: list[tuple]):
        """`opcoes` = [(valor, texto)]. Devolve o valor escolhido ou None."""
        if not opcoes:
            return None
        dlg = self._entrada(titulo, rotulo)
        dlg.setComboBoxItems([t for _, t in opcoes])
        dlg.setComboBoxEditable(False)
        if dlg.exec() != QDialog.Accepted:
            return None
        return next((v for v, t in opcoes if t == dlg.textValue()), None)


class Documento(QDialog):
    """Mostra um cupom ou fechamento na tela (modo de impressão 'tela' ou impressora fora). Não bloqueia o caixa."""

    def __init__(self, pai: QWidget, titulo: str, texto: str):
        super().__init__(pai)
        self.setWindowTitle(titulo)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        caixa = QVBoxLayout(self)
        self.texto = QPlainTextEdit(texto)
        self.texto.setReadOnly(True)
        self.texto.setFont(QFont("Consolas", 10))
        caixa.addWidget(self.texto)
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(self.close)
        caixa.addWidget(fechar, alignment=Qt.AlignRight)
        self.resize(460, 560)


def _cartao() -> tuple[QFrame, QVBoxLayout]:
    quadro = QFrame()
    quadro.setObjectName("cartao")
    caixa = QVBoxLayout(quadro)
    caixa.setContentsMargins(12, 10, 12, 10)
    return quadro, caixa


def _rotulo(texto: str = "", nome: str | None = None) -> QLabel:
    lbl = QLabel(texto)
    if nome:
        lbl.setObjectName(nome)
    lbl.setWordWrap(True)
    return lbl

class JanelaCaixa(QMainWindow):
    """Caixa Qt. Contrato: `JanelaCaixa(ctx, parent=None).show()` não bloqueia; quem abre guarda a referência.
    Fechar a janela (inclusive na saída da sessão) nunca encerra o turno nem a venda de balcão: ela fica aberta para
    continuar depois. Durante uma gravação o fechamento é recusado (a janela continua visível)."""

    def __init__(self, ctx, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.venda_id: int | None = None
        self.dialogos = Dialogos(self)
        self.documentos: list[QDialog] = []
        self._ocupado = False
        self._fechando_venda = False
        self.setWindowTitle(f"Caixa - {self._nome_loja()}")
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setStyleSheet(ESTILO)
        self.resize(1240, 760)
        self._montar()
        self.recarregar_tudo()

    def _nome_loja(self) -> str:
        try:
            return self.ctx.config.nome_loja()
        except Exception:  # noqa: BLE001 - o título não pode impedir o caixa de abrir
            return "WillPDV"

    # ================================================================ layout
    def _montar(self) -> None:
        fundo = QWidget()
        fundo.setObjectName("fundo")
        geral = QVBoxLayout(fundo)
        self.lbl_cabecalho = _rotulo("", "titulo")
        geral.addWidget(self.lbl_cabecalho)
        self.paginas = QStackedWidget()
        self.paginas.addWidget(self._pagina_sem_operador())
        self.paginas.addWidget(self._pagina_abertura())
        self.paginas.addWidget(self._pagina_venda())
        self.paginas.addWidget(self._pagina_fechamento())
        geral.addWidget(self.paginas, 1)
        self.lbl_status = _rotulo("", "status")
        geral.addWidget(self.lbl_status)
        self.setCentralWidget(fundo)
        atalho = QShortcut(QKeySequence("F12"), self)
        atalho.activated.connect(self.fechar_venda)

    def _pagina_sem_operador(self) -> QWidget:
        pagina, caixa = _cartao()
        caixa.addWidget(_rotulo("Nenhum operador na sessão. Entre no sistema para usar o caixa.", "titulo"))
        caixa.addStretch(1)
        return pagina

    def _pagina_abertura(self) -> QWidget:
        pagina = QWidget()
        externo = QVBoxLayout(pagina)
        quadro, caixa = _cartao()
        quadro.setMaximumWidth(520)
        caixa.addWidget(_rotulo("Abertura do turno", "titulo"))
        caixa.addWidget(_rotulo("Não há turno aberto. Informe o número do turno e o dinheiro encontrado na gaveta "
                                "(fundo de caixa) para começar a vender.", "mudo"))
        form = QFormLayout()
        self.spin_turno = QSpinBox()
        self.spin_turno.setRange(1, 9)
        form.addRow("Turno:", self.spin_turno)
        self.ent_fundo = QLineEdit("0,00")
        form.addRow("Valor inicial (R$):", self.ent_fundo)
        caixa.addLayout(form)
        self.btn_abrir_turno = QPushButton("Abrir turno")
        self.btn_abrir_turno.setObjectName("primario")
        self.btn_abrir_turno.clicked.connect(self.abrir_turno)
        self.ent_fundo.returnPressed.connect(self.abrir_turno)
        caixa.addWidget(self.btn_abrir_turno)
        externo.addWidget(quadro, alignment=Qt.AlignHCenter | Qt.AlignTop)
        externo.addStretch(1)
        return pagina

    def _pagina_venda(self) -> QWidget:
        pagina = QWidget()
        grade = QHBoxLayout(pagina)

        esq, c_esq = _cartao()
        esq.setFixedWidth(230)
        c_esq.addWidget(_rotulo("Mesas e comandas", "titulo"))
        self.lbl_dica_pos = _rotulo("", "mudo")
        c_esq.addWidget(self.lbl_dica_pos)
        linha = QHBoxLayout()
        self.ent_pos = QLineEdit()
        self.ent_pos.setPlaceholderText("Número")
        self.ent_pos.returnPressed.connect(self.chamar_posicao)
        linha.addWidget(self.ent_pos)
        self.btn_chamar = QPushButton("Chamar")
        self.btn_chamar.clicked.connect(self.chamar_posicao)
        linha.addWidget(self.btn_chamar)
        c_esq.addLayout(linha)
        self.btn_balcao = QPushButton("Venda de balcão")
        self.btn_balcao.clicked.connect(self.ir_para_balcao)
        c_esq.addWidget(self.btn_balcao)
        c_esq.addWidget(_rotulo("Abertas (duplo clique para chamar):", "mudo"))
        self.lista_mesas = QListWidget()
        self.lista_mesas.itemActivated.connect(self._mesa_escolhida)
        c_esq.addWidget(self.lista_mesas, 1)
        grade.addWidget(esq)

        centro, c_cen = _cartao()
        self.lbl_venda = _rotulo("Balcão", "titulo")
        c_cen.addWidget(self.lbl_venda)
        self.lbl_aviso_venda = _rotulo("", "alerta")
        self.lbl_aviso_venda.hide()
        c_cen.addWidget(self.lbl_aviso_venda)
        entrada = QGridLayout()
        entrada.addWidget(QLabel("Código ou nome do produto:"), 0, 0)
        entrada.addWidget(QLabel("Quantidade:"), 0, 1)
        self.ent_codigo = QLineEdit()
        self.ent_codigo.setPlaceholderText("Código, código de barras ou parte do nome")
        self.ent_codigo.returnPressed.connect(self.lancar_item)
        self.ent_codigo.textEdited.connect(self._esconder_produtos)
        entrada.addWidget(self.ent_codigo, 1, 0)
        self.ent_qtd = QLineEdit("1")
        self.ent_qtd.setMaximumWidth(110)
        self.ent_qtd.returnPressed.connect(self.lancar_item)
        entrada.addWidget(self.ent_qtd, 1, 1)
        self.btn_lancar = QPushButton("Lançar")
        self.btn_lancar.setObjectName("primario")
        self.btn_lancar.clicked.connect(self.lancar_item)
        entrada.addWidget(self.btn_lancar, 1, 2)
        entrada.setColumnStretch(0, 1)
        c_cen.addLayout(entrada)
        self.lista_produtos = QListWidget()
        self.lista_produtos.setMaximumHeight(150)
        self.lista_produtos.itemActivated.connect(lambda _item: self.lancar_item())
        self.lista_produtos.hide()
        c_cen.addWidget(self.lista_produtos)
        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(["Código", "Produto", "Un.", "Preço (R$)", "Qtd.", "Total (R$)"])
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        c_cen.addWidget(self.tabela, 1)
        botoes = QHBoxLayout()
        self.btn_cancelar_item = QPushButton("Cancelar item")
        self.btn_cancelar_item.clicked.connect(self.cancelar_item)
        botoes.addWidget(self.btn_cancelar_item)
        self.btn_cancelar_venda = QPushButton("Cancelar venda")
        self.btn_cancelar_venda.setObjectName("perigo")
        self.btn_cancelar_venda.clicked.connect(self.cancelar_venda)
        botoes.addWidget(self.btn_cancelar_venda)
        botoes.addStretch(1)
        c_cen.addLayout(botoes)
        grade.addWidget(centro, 1)

        dir_, c_dir = _cartao()
        dir_.setFixedWidth(320)
        c_dir.addWidget(_rotulo("Total (R$)", "mudo"))
        self.lbl_total = _rotulo("0,00", "total")
        c_dir.addWidget(self.lbl_total)
        self.lbl_detalhe = _rotulo("", "mudo")
        c_dir.addWidget(self.lbl_detalhe)
        self.lbl_falta_rotulo = _rotulo("Troco (R$)", "mudo")
        c_dir.addWidget(self.lbl_falta_rotulo)
        self.lbl_troco = _rotulo("0,00", "troco")
        c_dir.addWidget(self.lbl_troco)
        form = QFormLayout()
        self.cmb_forma = QComboBox()
        self.cmb_forma.currentIndexChanged.connect(lambda _i: self._sugerir_valor())
        form.addRow("Forma:", self.cmb_forma)
        self.ent_valor = QLineEdit()
        self.ent_valor.returnPressed.connect(self.receber)
        form.addRow("Valor (R$):", self.ent_valor)
        c_dir.addLayout(form)
        self.btn_receber = QPushButton("Receber")
        self.btn_receber.clicked.connect(self.receber)
        c_dir.addWidget(self.btn_receber)
        self.lista_pagamentos = QListWidget()
        self.lista_pagamentos.setMaximumHeight(130)
        c_dir.addWidget(self.lista_pagamentos)
        self.btn_remover_pag = QPushButton("Remover pagamento")
        self.btn_remover_pag.clicked.connect(self.remover_pagamento)
        c_dir.addWidget(self.btn_remover_pag)
        self.lbl_msg_pag = _rotulo("", "mudo")
        c_dir.addWidget(self.lbl_msg_pag)
        c_dir.addStretch(1)
        self.btn_fechar_venda = QPushButton("Fechar venda (F12)")
        self.btn_fechar_venda.setObjectName("primario")
        self.btn_fechar_venda.clicked.connect(self.fechar_venda)
        c_dir.addWidget(self.btn_fechar_venda)
        self.btn_trocar_turno = QPushButton("Trocar turno")
        self.btn_trocar_turno.clicked.connect(self.ir_para_fechamento)
        c_dir.addWidget(self.btn_trocar_turno)
        c_dir.addWidget(_rotulo("Ainda no caixa clássico: partes, comissão, saída, desconto, serviço, observação, "
                                "transferência, pré-conta, caderneta, entrega, sangria e gaveta.", "mudo"))
        grade.addWidget(dir_)
        return pagina
    def _pagina_fechamento(self) -> QWidget:
        pagina = QWidget()
        externo = QVBoxLayout(pagina)
        quadro, caixa = _cartao()
        quadro.setMaximumWidth(620)
        caixa.addWidget(_rotulo("Troca de turno", "titulo"))
        caixa.addWidget(_rotulo("Confira primeiro o que foi lançado em cartão e Pix com o fechamento da maquininha. "
                                "Depois conte a gaveta e digite o valor encontrado (o esperado não é mostrado).", "mudo"))
        self.txt_maquininha = QPlainTextEdit()
        self.txt_maquininha.setReadOnly(True)
        self.txt_maquininha.setMaximumHeight(140)
        caixa.addWidget(self.txt_maquininha)
        self.lbl_avisos_turno = _rotulo("", "alerta")
        caixa.addWidget(self.lbl_avisos_turno)
        form = QFormLayout()
        self.ent_gaveta = QLineEdit()
        self.ent_gaveta.setPlaceholderText("0,00")
        form.addRow("Valor na gaveta (+ cheques/tickets) R$:", self.ent_gaveta)
        caixa.addLayout(form)
        botoes = QHBoxLayout()
        self.btn_voltar_venda = QPushButton("Voltar ao caixa")
        self.btn_voltar_venda.clicked.connect(self.voltar_para_venda)
        botoes.addWidget(self.btn_voltar_venda)
        botoes.addStretch(1)
        self.btn_confirmar_turno = QPushButton("Encerrar turno")
        self.btn_confirmar_turno.setObjectName("perigo")
        self.btn_confirmar_turno.clicked.connect(self.fechar_turno)
        botoes.addWidget(self.btn_confirmar_turno)
        caixa.addLayout(botoes)
        externo.addWidget(quadro, alignment=Qt.AlignHCenter | Qt.AlignTop)
        externo.addStretch(1)
        return pagina

    # ========================================================= utilidades
    def avisar(self, texto: str, cor: str = VERDE) -> None:
        self.lbl_status.setText(texto)
        self.lbl_status.setStyleSheet(f"color: {cor}; font-weight: bold;" if texto else "")

    def _executar(self, funcao, *args, **kwargs):
        """Como `tema.tratar` do caixa clássico: erro de negócio vira mensagem; erro inesperado é registrado e avisado,
        sem derrubar a tela. Devolve (ok, resultado). Enquanto grava, a janela recusa ser fechada."""
        anterior, self._ocupado = self._ocupado, True
        try:
            return True, funcao(*args, **kwargs)
        except ErroNegocio as e:
            self.dialogos.erro("Caixa", str(e))
        except Exception as e:  # noqa: BLE001 - nunca deixar o caixa morrer
            from src.core import registro
            registro.registrar_excecao(*sys.exc_info(), origem=getattr(funcao, "__name__", "caixa_qt"))
            self.dialogos.erro("Erro", f"Erro inesperado: {e}\nO movimento já gravado foi preservado.")
        finally:
            self._ocupado = anterior
        return False, None

    def _autorizar(self, modulo: str, chave_config: str, motivo: str) -> bool:
        """A mesma regra do caixa clássico: se a configuração exige e o operador não tem nível, pede a senha de um
        supervisor (3 tentativas; senhas erradas demais bloqueiam pelo AcessoController)."""
        if not self.ctx.acesso.precisa_senha(self.ctx.operador, modulo, chave_config):
            return True
        for _ in range(TENTATIVAS_SUPERVISOR):
            senha = self.dialogos.pedir_texto("Autorização", f"{motivo}\nDigite uma senha válida:", senha=True)
            if senha is None:
                return False
            try:
                sup = self.ctx.acesso.validar_supervisor(senha, modulo)
            except ErroNegocio as e:
                self.dialogos.erro("Autorização", str(e))
                return False
            if sup is not None:
                return True
            self.dialogos.erro("Autorização", "Senha inválida ou sem permissão para esta operação.")
        return False

    def _pedir_motivo(self, titulo: str, rotulo: str, padrao: str) -> str | None:
        """Motivo do cancelamento: só é perguntado quando a configuração exige (e então não pode ficar vazio)."""
        if not self.ctx.banco.cfg_bool("exigir_motivo_cancelamento", False):
            return padrao
        while True:
            texto = self.dialogos.pedir_texto(titulo, rotulo)
            if texto is None:
                return None
            if texto.strip():
                return texto.strip()
            self.dialogos.aviso(titulo, "Informe o motivo.")

    def venda(self) -> dict | None:
        if self.venda_id is None:
            return None
        v = self.ctx.banco.um("SELECT * FROM vendas WHERE id = ?", (self.venda_id,))
        if v is None or v["status"] not in ("aberta", "conta_enviada"):
            self.venda_id = None
            return None
        return dict(v)

    def _turno(self) -> dict | None:
        return self.ctx.turnos.atual()

    def _pronto(self) -> bool:
        """Só vende com operador na sessão, turno aberto e a tela de venda à mostra."""
        if self.ctx.operador is None:
            self.recarregar_tudo()
            return False
        if self._turno() is None:
            self.dialogos.aviso("Caixa", "Não há turno aberto. Abra o turno antes de vender.")
            self.recarregar_tudo()
            return False
        return self.paginas.currentIndex() == PAGINA_VENDA

    # ========================================================= recarregar
    def recarregar_tudo(self) -> None:
        if self.ctx.operador is None:
            self.lbl_cabecalho.setText("Caixa")
            self.paginas.setCurrentIndex(PAGINA_SEM_OPERADOR)
            return
        turno = self._turno()
        if turno is None:
            self.venda_id = None
            self.lbl_cabecalho.setText(f"Caixa  ·  {self.ctx.operador.nome.upper()}  ·  sem turno aberto")
            max_turnos = max(self.ctx.banco.cfg_int("num_turnos", 3), 1)
            self.spin_turno.setRange(1, max(max_turnos, 9))
            self.spin_turno.setValue(self.ctx.turnos.numero_sugerido())
            self.ent_fundo.setText("0,00")
            self.paginas.setCurrentIndex(PAGINA_ABERTURA)
            self.ent_fundo.setFocus()
            return
        self.lbl_cabecalho.setText(f"Caixa  ·  TURNO {turno['numero']}  ·  {self.ctx.operador.nome.upper()}")
        if self.venda() is None:
            balcao = self.ctx.caixa.balcao_aberto()       # retoma o balcão interrompido (queda de energia, saída do caixa)
            self.venda_id = balcao["id"] if balcao else None
        if self.paginas.currentIndex() != PAGINA_FECHAMENTO:
            self.paginas.setCurrentIndex(PAGINA_VENDA)
        padrao = self.ctx.caixa.padrao_posicao()
        comum, outra = exemplos(padrao)
        self.lbl_dica_pos.setText(f"{rotulo_do_campo(padrao)}. Ex.: {comum} ou {outra}; 0 volta ao balcão.")
        self._carregar_formas()
        self.recarregar()

    def _carregar_formas(self) -> None:
        atual = self.cmb_forma.currentData()
        self.cmb_forma.blockSignals(True)
        self.cmb_forma.clear()
        for f in self.ctx.caixa.formas_pagamento():
            self.cmb_forma.addItem(f["tipo"], int(f["id"]))
        i = self.cmb_forma.findData(atual) if atual is not None else -1
        self.cmb_forma.setCurrentIndex(i if i >= 0 else 0)
        self.cmb_forma.blockSignals(False)
    def recarregar(self) -> None:
        """Atualiza a venda da tela (itens, total, pagamentos) e a lista de mesas e comandas abertas."""
        v = self.venda()
        caixa = self.ctx.caixa
        self.tabela.setRowCount(0)
        itens = caixa.itens(v["id"]) if v else []
        for it in itens:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            nome = it["nome"] + (f"  [{' / '.join(it['partes_nomes'])}]" if it["partes_nomes"] else "")
            valores = [it["codigo"], nome, it["unidade"], fmt.fmt_num(it["preco_unit_cent"]), _fmt_qtd(it["quantidade"]),
                       fmt.fmt_num(it["total_cent"])]
            for col, texto in enumerate(valores):
                celula = QTableWidgetItem(str(texto))
                celula.setData(Qt.UserRole, int(it["id"]))
                if col >= 3:
                    celula.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabela.setItem(linha, col, celula)
        if itens:
            self.tabela.scrollToBottom()
        total = v["total_cent"] if v else 0
        pags = caixa.pagamentos(v["id"]) if v else []
        recebido = sum(p["valor_cent"] for p in pags)
        if v is None or v["modalidade"] == "balcao":
            self.lbl_venda.setText("Balcão" + ("" if v else "  ·  nova venda"))
        else:
            situacao = "Conta enviada" if v["status"] == "conta_enviada" else "Aberta"
            self.lbl_venda.setText(f"{caixa.rotular_posicao(v['comanda'], v['posicao'])}  ·  "
                                   f"{nome_posicao(v['comanda'], v['posicao'])}  ·  {situacao}")
        self.lbl_total.setText(fmt.fmt_num(total))
        self.lbl_detalhe.setText(self._detalhe_total(v))
        self.lista_pagamentos.clear()
        for p in pags:
            item = QListWidgetItem(f"{p['tipo']}: {fmt.fmt_brl(p['valor_cent'])}")
            item.setData(Qt.UserRole, int(p["id"]))
            self.lista_pagamentos.addItem(item)
        if recebido:
            falta = max(total - recebido, 0)
            self.lbl_falta_rotulo.setText("Falta receber (R$)" if falta else "Troco (R$)")
            self.lbl_troco.setText(fmt.fmt_num(falta if falta else recebido - total))
            self.lbl_msg_pag.setText(f"Recebido: {fmt.fmt_brl(recebido)}")
        else:
            self.lbl_falta_rotulo.setText("Troco (R$)")
            self.lbl_troco.setText("0,00")
            self.lbl_msg_pag.setText("")
        self._aviso_comissao(v)
        tem_itens = bool(itens)
        self.btn_cancelar_item.setEnabled(tem_itens)
        self.btn_cancelar_venda.setEnabled(v is not None)
        self.btn_receber.setEnabled(tem_itens)
        self.btn_remover_pag.setEnabled(bool(pags))
        self.btn_fechar_venda.setEnabled(tem_itens)
        self._sugerir_valor()
        self.carregar_mesas()

    def _detalhe_total(self, v: dict | None) -> str:
        if not v:
            return ""
        partes = []
        if v["desconto_cent"]:
            partes.append(f"Desconto: - {fmt.fmt_brl(v['desconto_cent'])}")
        if v["servico_cent"]:
            partes.append(f"Serviço: {fmt.fmt_brl(v['servico_cent'])}")
        if v["taxa_cent"]:
            partes.append(f"{'Compl. consumação' if v['comanda'] else 'Taxa de entrega'}: {fmt.fmt_brl(v['taxa_cent'])}")
        if v["acrescimo_cent"]:
            partes.append(f"Taxa do crédito: {fmt.fmt_brl(v['acrescimo_cent'])}")
        return "\n".join(partes)

    def _aviso_comissao(self, v: dict | None) -> None:
        """Comanda de garota com comissão marcada: o acerto com a garota ainda é feito no caixa clássico."""
        texto = ""
        if v and v["modalidade"] == "mesa" and v["comanda"]:
            turno = self._turno()
            try:
                marcadas = self.ctx.comissoes.marcadas(v["posicao"], turno["id"] if turno else None)
            except (ErroNegocio, ValueError):
                marcadas = []
            pendente = sum(c["valor_cent"] for c in marcadas if c["status"] == "pendente")
            if pendente:
                texto = (f"Esta comanda tem comissão a pagar à garota ({fmt.fmt_brl(pendente)}). "
                         "O pagamento da comissão ainda é feito no caixa clássico; aqui só se cobra o consumo.")
        self.lbl_aviso_venda.setText(texto)
        self.lbl_aviso_venda.setVisible(bool(texto))

    def carregar_mesas(self) -> None:
        self.lista_mesas.clear()
        for m in self.ctx.caixa.mesas():
            situacao = " (conta)" if m["status"] == "conta_enviada" else " (parada)" if m["inativa"] else ""
            item = QListWidgetItem(f"{m['rotulo']}  ·  {fmt.fmt_brl(m['total_cent'])}  ·  {m['n_itens']} item(ns){situacao}")
            item.setData(Qt.UserRole, m["rotulo"])
            self.lista_mesas.addItem(item)
            if m["id"] == self.venda_id:
                item.setSelected(True)

    def _sugerir_valor(self) -> None:
        """No campo do valor já vem o que falta (com a taxa da forma escolhida, se ela cobrar)."""
        v = self.venda()
        if v is None:
            self.ent_valor.clear()
            return
        pago = sum(p["valor_cent"] for p in self.ctx.caixa.pagamentos(v["id"]))
        falta = max(v["total_cent"] - pago, 0)
        forma = self.cmb_forma.currentData()
        if falta and forma is not None:
            falta += self.ctx.caixa.acrescimo_da_forma(v["id"], int(forma))
        self.ent_valor.setText(fmt.fmt_num(falta) if falta else "")

    # ========================================================= turno
    def abrir_turno(self) -> None:
        if self.ctx.operador is None or self._turno() is not None:
            self.recarregar_tudo()
            return
        try:
            valor = ler_dinheiro(self.ent_fundo.text(), permitir_zero=True)
        except ValueError as e:
            self.dialogos.aviso("Abertura do turno", str(e))
            return
        numero = self.spin_turno.value()
        if not self.dialogos.confirmar("Abertura do turno", f"Abrir o turno {numero} com valor inicial de "
                                                            f"{fmt.fmt_brl(valor)}?"):
            return
        ok, _ = self._executar(self.ctx.turnos.abrir, self.ctx.operador_id, numero, valor)
        if ok:
            self.avisar(f"Turno {numero} aberto com {fmt.fmt_brl(valor)}.")
            self.recarregar_tudo()
            self.ent_codigo.setFocus()
    # ========================================================= itens
    def _esconder_produtos(self, _texto: str = "") -> None:
        self.lista_produtos.clear()
        self.lista_produtos.hide()

    def _mostrar_produtos(self, produtos: list[dict]) -> None:
        self.lista_produtos.clear()
        for p in produtos:
            item = QListWidgetItem(f"{p['codigo']}  ·  {p['nome']}  ·  {fmt.fmt_brl(self.ctx.produtos.preco_vigente(p))}")
            item.setData(Qt.UserRole, int(p["id"]))
            self.lista_produtos.addItem(item)
        self.lista_produtos.show()
        self.lista_produtos.setCurrentRow(0)
        self.lista_produtos.setFocus()

    def _produto_digitado(self, texto: str) -> dict | None | bool:
        """O produto do campo do código: escolhido na lista, pelo código/barras/atalho ou pelo nome. Devolve False quando o
        texto foi tratado de outro jeito (posição, lista para escolher ou operação bloqueada)."""
        escolhido = self.lista_produtos.currentItem() if self.lista_produtos.isVisible() else None
        if escolhido is not None:
            return self.ctx.produtos.por_id(int(escolhido.data(Qt.UserRole)))
        if not texto:
            self.avisar("Digite o código ou parte do nome do produto.", AMBAR)
            return False
        if self.ctx.comissoes.eh_codigo(texto):
            self.dialogos.aviso("Comissão", "O lançamento de comissão das garotas ainda não foi migrado para o caixa novo. "
                                            "Use o caixa clássico.")
            return False
        if self.ctx.caixa.eh_codigo_saida(texto):
            self.dialogos.aviso("Saída", "A liberação de saída sem consumo ainda não foi migrada para o caixa novo. "
                                         "Use o caixa clássico.")
            return False
        p = self.ctx.produtos.buscar_codigo(texto)
        if p is None and parece_posicao(texto):      # "C2" ou "M5" no campo do código troca de posição
            self.ent_codigo.clear()
            self.ent_pos.setText(texto)
            self.chamar_posicao()
            return False
        if p is None and not texto.isdigit():
            achados = self.ctx.produtos.pesquisar(texto)
            if len(achados) == 1:
                p = achados[0]
            elif achados:
                self._mostrar_produtos(achados)
                self.avisar(f"{len(achados)} produtos com '{texto}'. Escolha na lista e tecle Enter.", AMBAR)
                return False
        if p is None:
            self.avisar(f"Produto '{texto}' não encontrado.", VERMELHO)
            self.ent_codigo.selectAll()
            return False
        return p

    def lancar_item(self) -> None:
        if not self._pronto() or self._ocupado:
            return
        p = self._produto_digitado(self.ent_codigo.text().strip())
        if p is False:
            return
        if p is None or not p["ativo"]:
            self.avisar("Produto não encontrado.", VERMELHO)
            return
        try:
            qtd = fmt.para_qtd(self.ent_qtd.text() or "1")
        except ValueError:
            self.avisar("Quantidade inválida.", VERMELHO)
            self.ent_qtd.setFocus()
            self.ent_qtd.selectAll()
            return
        if p["partes"] > 1 and (p["composto"] or self.ctx.banco.valor(
                "SELECT COUNT(*) FROM produtos WHERE montagem = 1 AND ativo = 1")):
            self.dialogos.aviso("Produto dividido", f"'{p['nome']}' é vendido em partes (montagem). " + MSG_CLASSICO)
            return
        ok, _ = self._executar(self._lancar, p["id"], qtd)
        if not ok:
            self.recarregar()
            self.ent_qtd.setFocus()
            self.ent_qtd.selectAll()
            return
        self.avisar(f"{_fmt_qtd(fmt.arred_qtd(qtd))} x {p['nome']} lançado.")
        self.ent_codigo.clear()
        self.ent_qtd.setText("1")
        self._esconder_produtos()
        self.recarregar()
        self.ent_codigo.setFocus()

    def _lancar(self, produto_id: int, qtd: float) -> int:
        """Abre o balcão se preciso e lança o item na MESMA transação: se o item for recusado, nenhuma venda vazia fica."""
        caixa = self.ctx.caixa
        anterior = self.venda_id
        try:
            with self.ctx.banco.transacao():
                if self.venda_id is None:
                    self.venda_id = caixa.abrir_balcao()
                item_id = caixa.adicionar_item(self.venda_id, produto_id, qtd)
        except BaseException:
            self.venda_id = anterior
            raise
        self._enviar_remoto([item_id])
        return item_id

    def _enviar_remoto(self, item_ids: list[int]) -> None:
        """Manda os itens para a cozinha/bar. Falha da impressora remota não bloqueia a venda."""
        try:
            for sub, texto in self.ctx.impressao.pedido_remoto(self.venda_id, item_ids).items():
                self.ctx.impressao.enviar_remoto(texto, f"pedido_{sub}")
        except ErroImpressao as e:
            self.avisar(f"Impressora da cozinha/bar indisponível: {e}", VERMELHO)

    def _item_selecionado(self) -> tuple[int, str] | None:
        linha = self.tabela.currentRow()
        if linha < 0 or self.tabela.item(linha, 0) is None:
            return None
        return int(self.tabela.item(linha, 0).data(Qt.UserRole)), self.tabela.item(linha, 1).text()

    def cancelar_item(self) -> None:
        if not self._pronto() or self._ocupado:
            return
        sel = self._item_selecionado()
        if sel is None:
            self.dialogos.aviso("Cancela item", "Selecione na lista o item a cancelar.")
            return
        item_id, nome = sel
        if not self._autorizar("caixa_cancelamento", "exigir_senha_cancelamento", "Cancelar item exige autorização:"):
            return
        if not self.dialogos.confirmar("Cancela item", f"Cancelar o item '{nome}'?", padrao_sim=False):
            return
        motivo = self._pedir_motivo("Cancela item", f"Motivo do cancelamento de '{nome}':", "")
        if motivo is None:
            return
        ok, _ = self._executar(self.ctx.caixa.cancelar_item, item_id, motivo)
        self.recarregar()
        if ok:
            self.avisar("Item cancelado.", AMBAR)

    def cancelar_venda(self) -> None:
        if not self._pronto() or self._ocupado:
            return
        v = self.venda()
        if v is None:
            self.dialogos.aviso("Cancela venda", "Não há venda em andamento.")
            return
        if not self._autorizar("caixa_cancelamento", "exigir_senha_cancelamento", "Cancelar a venda exige autorização:"):
            return
        if not self.dialogos.confirmar("Cancela venda", "Cancelar a venda inteira?\nTodos os itens lançados serão eliminados.",
                                       padrao_sim=False):
            return
        motivo = self._pedir_motivo("Cancela venda", "Motivo do cancelamento da venda:", "cancelada no caixa")
        if motivo is None:
            return
        ok, _ = self._executar(self.ctx.caixa.cancelar_venda, v["id"], motivo)
        if ok:
            self.venda_id = None
            self.avisar("Venda cancelada.", AMBAR)
        self.recarregar()
    # ========================================================= mesas e comandas
    def _descartar_se_vazia(self) -> None:
        """Ao sair de uma mesa ou comanda recém-aberta e sem nada, ela é eliminada para não deixar mesa fantasma."""
        v = self.venda()
        if v and v["modalidade"] == "mesa" and not self.ctx.caixa.itens(v["id"], cancelados=True) \
                and not self.ctx.caixa.pagamentos(v["id"]):
            self.ctx.caixa.cancelar_venda(v["id"], "mesa vazia descartada")
            self.venda_id = None

    def _mesa_escolhida(self, item: QListWidgetItem) -> None:
        self.ent_pos.setText(str(item.data(Qt.UserRole)))
        self.chamar_posicao()

    def ir_para_balcao(self) -> None:
        self.ent_pos.setText("0")
        self.chamar_posicao()

    def chamar_posicao(self) -> None:
        if not self._pronto() or self._ocupado:
            return
        texto = self.ent_pos.text().strip() or "0"
        try:
            comanda, n = self.ctx.caixa.ler_posicao(texto)
        except ValueError as e:
            self.dialogos.aviso("Mesa ou comanda", str(e))
            return
        atual = self.venda()
        self.ent_pos.clear()
        if atual and atual["modalidade"] == "mesa" and atual["posicao"] == n and bool(atual["comanda"]) == comanda:
            self.ent_codigo.setFocus()
            return
        if atual and n == 0 and atual["modalidade"] == "balcao":
            self.ent_codigo.setFocus()
            return
        if atual and atual["modalidade"] != "mesa" and self.ctx.caixa.itens(atual["id"]):
            self.dialogos.aviso("Mesa ou comanda", "Conclua, pague ou cancele a venda em andamento antes de chamar uma "
                                                   "mesa ou comanda.")
            return
        ok, _ = self._executar(self._descartar_se_vazia)
        if not ok:
            return
        if n == 0:
            balcao = self.ctx.caixa.balcao_aberto()
            self.venda_id = balcao["id"] if balcao else None
            self.recarregar()
            self.ent_codigo.setFocus()
            return
        pessoas = 0
        existente = self.ctx.banco.valor(
            "SELECT id FROM vendas WHERE modalidade='mesa' AND comanda=? AND posicao=? AND status IN ('aberta','conta_enviada')",
            (int(comanda), n))
        if not existente and not comanda and self.ctx.banco.cfg_bool("pergunta_pessoas"):
            pessoas = self._pedir_pessoas(f"Mesa {n}")
            if pessoas is None:
                self.recarregar()
                return
        ok, res = self._executar(self.ctx.caixa.abrir_mesa, n, pessoas, comanda)
        if ok:
            self.venda_id = res[0]
            self.avisar(f"{nome_posicao(comanda, n)} {'aberta' if res[1] else 'chamada'}.")
        self.recarregar()
        self.ent_codigo.setFocus()

    def _pedir_pessoas(self, titulo: str) -> int | None:
        while True:
            texto = self.dialogos.pedir_texto(titulo, "Número de pessoas na mesa (1 a 999):", padrao="1")
            if texto is None:
                return None
            if texto.strip().isdigit() and 1 <= int(texto) <= 999:
                return int(texto)
            self.dialogos.aviso(titulo, "Digite um número de 1 a 999.")

    # ========================================================= pagamento
    def _receber(self, venda_id: int, forma_id: int, cent: int) -> tuple[int, dict]:
        """Grava o pagamento e confere a conta; se a forma não pode ficar com a sobra (troco), desfaz tudo."""
        caixa = self.ctx.caixa
        pago_antes = sum(p["valor_cent"] for p in caixa.pagamentos(venda_id))
        with self.ctx.banco.transacao():
            pid = caixa.adicionar_pagamento(venda_id, forma_id, cent)
            total = caixa.obter(venda_id)["total_cent"]       # já com a taxa do crédito, se esta forma a cobra
            try:
                return pid, caixa.liquidar(venda_id, total)
            except ErroNegocio:
                nome = self.cmb_forma.currentText() or "Esta forma"
                raise ErroNegocio(f"{nome} não dá troco: o valor não pode passar do que falta "
                                  f"({fmt.fmt_brl(max(total - pago_antes, 0))}).") from None

    def receber(self) -> None:
        if not self._pronto() or self._ocupado or self._fechando_venda:
            return
        v = self.venda()
        if v is None or not self.ctx.caixa.itens(v["id"]):
            self.dialogos.aviso("Pagamento", "Lance ao menos um item antes de receber.")
            return
        forma = self.cmb_forma.currentData()
        if forma is None:
            self.dialogos.aviso("Pagamento", "Escolha a forma de pagamento.")
            return
        try:
            cent = ler_valor_pagamento(self.ent_valor.text())
        except ValueError as e:
            self.dialogos.aviso("Pagamento", str(e))
            self.ent_valor.setFocus()
            self.ent_valor.selectAll()
            return
        ok, r = self._executar(self._receber, v["id"], int(forma), cent)
        if not ok:
            self.recarregar()
            return
        pid, liq = r
        if liq.get("troco", 0) > LIMITE_TROCO_CENT and not self.dialogos.confirmar(
                "Troco alto", f"O troco será de {fmt.fmt_brl(liq['troco'])} (recebido: {fmt.fmt_brl(cent)}).\n"
                              "O valor recebido está certo?", padrao_sim=False):
            self._executar(self.ctx.caixa.remover_pagamento, pid)
            self.recarregar()
            return
        self.recarregar()
        if liq.get("falta", 0) == 0:
            self.avisar(f"Pagamento completo. Troco {fmt.fmt_brl(liq.get('troco', 0))}. Feche a venda (F12).")
            self.btn_fechar_venda.setFocus()

    def remover_pagamento(self) -> None:
        if not self._pronto() or self._ocupado or self._fechando_venda:
            return
        item = self.lista_pagamentos.currentItem()
        if item is None and self.lista_pagamentos.count():
            item = self.lista_pagamentos.item(self.lista_pagamentos.count() - 1)   # sem seleção: o último lançado
        if item is None:
            self.avisar("Não há pagamento lançado para remover.", AMBAR)
            return
        ok, _ = self._executar(self.ctx.caixa.remover_pagamento, int(item.data(Qt.UserRole)))
        self.recarregar()
        if ok:
            self.avisar("Pagamento removido.", AMBAR)
    # ========================================================= fechamento da venda
    def fechar_venda(self) -> None:
        if self._fechando_venda or self._ocupado or not self._pronto():   # duas teclas F12 seguidas não gravam duas vezes
            return
        self._fechando_venda = True
        try:
            self._fechar_venda()
        finally:
            self._fechando_venda = False

    def _fechar_venda(self) -> None:
        v = self.venda()
        if v is None or not self.ctx.caixa.itens(v["id"]):
            self.dialogos.aviso("Fechar venda", "Lance ao menos um item antes de fechar a venda.")
            return
        garcom = pessoas = None
        if v["modalidade"] == "mesa":
            if self.ctx.banco.cfg_bool("controle_garcom") and not v["garcom_id"]:
                garcom = self._escolher_garcom()
                if garcom is None:
                    return
            if self.ctx.banco.cfg_bool("pergunta_pessoas") and not v["pessoas"] and not v["comanda"]:
                pessoas = self._pedir_pessoas("Mesa")
                if pessoas is None:
                    return
        ok, venda = self._executar(self.ctx.caixa.fechar, v["id"], garcom, pessoas)
        if not ok:
            self.recarregar()
            return
        self.venda_id = None
        self._pos_fechamento(venda)

    def _escolher_garcom(self) -> int | None:
        ativos = self.ctx.cadastros.listar("operadores", apenas_ativos=True)
        garcons = [(r["id"], r["nome"]) for r in ativos if r["garcom"]] or [(r["id"], r["nome"]) for r in ativos]
        return self.dialogos.escolher("Garçom", "Garçom que atendeu:", garcons)

    def _pos_fechamento(self, venda: dict) -> None:
        """A venda já está gravada: falha de impressão só é avisada (o cupom é mostrado na tela, nunca se perde)."""
        try:
            saida = self.ctx.impressao.saida_da_venda(venda["id"])
        except Exception as e:  # noqa: BLE001 - a venda já está gravada
            saida = None
            self._registrar_falha(e)
        try:
            if self.ctx.banco.cfg_bool("imprimir_cupom", True):
                op = self.ctx.impressao.opcoes_cupom(venda["id"])
                self._emitir(f"Cupom {venda['cupom']}", self.ctx.impressao.cupom(venda["id"]), f"cupom_{venda['cupom']}",
                             tipo="cupom", abrir_gaveta=op["abrir_gaveta"], copias=op["copias"], venda_id=venda["id"])
            if saida:
                self._emitir("Ticket de saída", saida, f"saida_cupom_{venda['cupom']}", tipo="saida")
        except Exception as e:  # noqa: BLE001 - venda gravada: erro de impressão não derruba o caixa
            self._registrar_falha(e)
            self.dialogos.erro("Impressão", f"A venda foi gravada (cupom {venda['cupom']}), mas não foi possível preparar "
                                            f"a impressão:\n{e}\nReimprima o cupom pelo caixa clássico.")
        self.ent_codigo.clear()
        self.ent_qtd.setText("1")
        self._esconder_produtos()
        self.recarregar()
        self.lbl_falta_rotulo.setText("Troco (R$)")
        self.lbl_troco.setText(fmt.fmt_num(venda["troco_cent"]))
        texto = f"Venda {venda['cupom']} fechada. Troco {fmt.fmt_brl(venda['troco_cent'])}."
        if venda.get("vale_cent"):
            texto += f" Contra-vale {fmt.fmt_brl(venda['vale_cent'])}."
        alerta = self._alerta_gaveta()
        self.avisar(f"{texto}   {alerta}" if alerta else texto, AMBAR if alerta else VERDE)
        self.ent_codigo.setFocus()

    @staticmethod
    def _registrar_falha(e: Exception) -> None:
        from src.core import registro
        registro.registrar_excecao(type(e), e, e.__traceback__, origem="caixa_qt_impressao")

    def _emitir(self, titulo: str, texto: str, nome: str, tipo: str | None = None, abrir_gaveta: bool = False,
                copias: int = 1, venda_id: int | None = None) -> bool:
        """Como `enviar_ou_mostrar` do caixa clássico: modo 'tela' mostra; senão imprime e, se falhar, mostra com aviso."""
        if self.ctx.impressao.deve_mostrar_na_tela():
            self._mostrar(titulo, texto)
            return False
        try:
            self.ctx.impressao.enviar(texto, nome, tipo=tipo, abrir_gaveta=abrir_gaveta, copias=copias, venda_id=venda_id)
            return True
        except ErroImpressao as e:
            self.dialogos.erro("Impressão", f"Não foi possível imprimir: {e}\nMostrando o documento na tela.")
            self._mostrar(titulo, texto)
            return False

    def _mostrar(self, titulo: str, texto: str) -> None:
        self.documentos = [d for d in self.documentos if _vivo(d) and d.isVisible()]
        doc = Documento(self, titulo, texto)
        self.documentos.append(doc)
        doc.show()

    def _alerta_gaveta(self) -> str:
        turno = self._turno()
        if turno is None:
            return ""
        horario = self.ctx.turnos.sangria_do_horario(turno["id"])
        if horario:
            return f"ATENÇÃO: está na hora da sangria das {horario} (faça no caixa clássico)."
        limite = self.ctx.banco.cfg_int("limite_gaveta", 0) * 100
        if limite <= 0 or self.ctx.turnos.dinheiro_esperado(turno["id"]) <= limite:
            return ""
        return f"ATENÇÃO: a gaveta passou de {fmt.fmt_brl(limite)}. Faça uma sangria (no caixa clássico)."
    # ========================================================= troca de turno
    def ir_para_fechamento(self) -> None:
        if not self._pronto() or self._ocupado:
            return
        v = self.venda()
        if v and v["modalidade"] != "mesa" and self.ctx.caixa.itens(v["id"]):
            self.dialogos.aviso("Troca de turno", "Há uma venda em andamento. Conclua ou cancele antes de trocar o turno.")
            return
        ok, _ = self._executar(self._descartar_se_vazia)
        if not ok:
            return
        self.venda_id = None
        turno = self._turno()
        maq = self.ctx.turnos.maquininha(turno["id"])
        linhas = [f"{r['tipo']}: {r['qtd']} lançamento(s), {fmt.fmt_brl(r['valor'])}" for r in maq["linhas"]]
        self.txt_maquininha.setPlainText("\n".join(linhas) or "Nenhum lançamento em cartão ou Pix neste turno.")
        self.lbl_avisos_turno.setText(self._avisos_turno().strip())
        self.ent_gaveta.clear()
        self.paginas.setCurrentIndex(PAGINA_FECHAMENTO)
        self.ent_gaveta.setFocus()

    def _avisos_turno(self) -> str:
        aviso = ""
        abertas = self.ctx.turnos.posicoes_abertas()
        if abertas:
            nomes = ", ".join(p["nome"] for p in abertas[:6]) + (", ..." if len(abertas) > 6 else "")
            aviso = (f"\n\nATENÇÃO: {len(abertas)} mesa(s)/comanda(s) aberta(s), "
                     f"{fmt.fmt_brl(sum(p['total_cent'] for p in abertas))}:\n{nomes}.\nElas continuam abertas no próximo turno.")
        a_pagar = self.ctx.comissoes.pendentes_por_garota()
        if a_pagar:
            aviso += (f"\n\nComissão das garotas a pagar: {fmt.fmt_brl(sum(p['total_cent'] for p in a_pagar))} "
                      f"({len(a_pagar)} garota(s)).\nSe vai pagar com dinheiro da gaveta, responda Não, pague "
                      "(no caixa clássico) e conte o caixa de novo.")
        return aviso

    def voltar_para_venda(self) -> None:
        self.paginas.setCurrentIndex(PAGINA_VENDA)
        self.recarregar_tudo()
        self.ent_codigo.setFocus()

    def fechar_turno(self) -> None:
        if self._ocupado or self.paginas.currentIndex() != PAGINA_FECHAMENTO:
            return
        turno = self._turno()
        if turno is None:
            self.recarregar_tudo()
            return
        try:
            valor = ler_dinheiro(self.ent_gaveta.text(), permitir_zero=True)
        except ValueError as e:
            self.dialogos.aviso("Troca de turno", str(e))
            return
        if not self.dialogos.confirmar("Troca de turno", f"Confirma {fmt.fmt_brl(valor)} como valor final?\n"
                                       "Depois de confirmar o turno é encerrado e não pode ser acertado."
                                       + self._avisos_turno(), padrao_sim=False):
            return
        ok, res = self._executar(self.ctx.turnos.fechar, turno["id"], self.ctx.operador_id, valor)
        if not ok:
            return
        if self.ctx.utilitarios.backup_automatico("troca de turno") is None:
            self.dialogos.aviso("Backup", "O turno foi fechado, mas o BACKUP automático falhou.\n"
                                          "Faça um backup manual em Utilitários > Backup de dados e confira a pasta/disco.")
        self._documento_fechamento(res)
        self.paginas.setCurrentIndex(PAGINA_VENDA)
        self.recarregar_tudo()
        self.avisar(f"Turno {turno['numero']} encerrado.", AMBAR)

    def _documento_fechamento(self, res: dict) -> None:
        """O fechamento sai na impressora (se configurado) ou é mostrado na tela; erro aqui não desfaz o turno fechado."""
        try:
            texto = self.ctx.impressao.fechamento(res)
            nome = f"fechamento_turno_{res['turno']['numero']}"
            if self.ctx.banco.cfg_bool("imprimir_fechamento_ao_trocar", True) and not self.ctx.impressao.deve_mostrar_na_tela():
                vias = max(1, min(self.ctx.banco.cfg_int("vias_fechamento", 1), 3))
                try:
                    self.ctx.impressao.enviar(texto, nome, tipo="fechamento", copias=vias)
                    return
                except ErroImpressao as e:
                    self.dialogos.erro("Impressão", f"O fechamento não foi impresso: {e}\nMostrando na tela.")
            self._mostrar("Fechamento do turno", texto)
        except Exception as e:  # noqa: BLE001 - o turno já está fechado
            self._registrar_falha(e)
            self.dialogos.erro("Fechamento", f"O turno foi fechado, mas o relatório não pôde ser preparado:\n{e}")

    # ========================================================= sair
    def closeEvent(self, evento) -> None:
        """Sair nunca fecha o turno. Venda de balcão com itens fica aberta para continuar depois (pergunta antes);
        mesa ou comanda vazia é descartada. Durante uma gravação o fechamento é recusado."""
        if self._ocupado or self._fechando_venda:
            evento.ignore()
            return
        try:
            v = self.venda() if self.ctx.operador is not None else None
            if v and v["modalidade"] == "balcao" and self.ctx.caixa.itens(v["id"]):
                if not self.dialogos.confirmar("Sair do caixa", "Há uma venda em andamento no balcão.\n"
                                               "Sair mantém a venda aberta para continuar depois. Sair mesmo?"):
                    evento.ignore()
                    return
            else:
                self._descartar_se_vazia()
        except ErroNegocio:
            pass
        for doc in self.documentos:
            if _vivo(doc):
                doc.close()
        self.documentos = []
        evento.accept()