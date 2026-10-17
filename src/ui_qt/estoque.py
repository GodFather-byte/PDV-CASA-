"""Consulta de estoque Qt independente, sem integração de menu ou ações de escrita."""
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFormLayout, QHBoxLayout,
    QHeaderView, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from src.core import formatacao as fmt
from src.core.erros import ErroNegocio, ErroPermissao
from src.ui_qt.tema import texto


SITUACOES = (
    (None, "Todos os controlados"), ("sem", "Sem estoque"), ("ponto", "Repor"),
    ("normal", "Normal"), ("livre", "Sem controle"),
)
ROTULOS = dict(SITUACOES)


class JanelaEstoque(QDialog):
    LIMITE_HISTORICO = 30

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._exigir_acesso()
        self.linhas = []
        self.movimentos = []
        self.setWindowTitle("Estoque • somente leitura")
        self.resize(1200, 780)
        layout = QVBoxLayout(self)
        layout.addWidget(texto("Consulta de estoque", "titulo"))
        layout.addWidget(texto(
            "Somente leitura • sem entradas, saídas, ajustes ou pedidos. "
            "A busca por nome/código também inclui produtos sem controle.", "suave"))
        self.resumo = texto("", "suave")
        layout.addWidget(self.resumo)
        filtros = QHBoxLayout()
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Nome ou código • pressione Enter")
        self.busca.returnPressed.connect(self.atualizar)
        self.situacao, self.grupo = QComboBox(), QComboBox()
        for valor, rotulo in SITUACOES:
            self.situacao.addItem(rotulo, valor)
        self.grupo.addItem("Todos os grupos", None)
        for rotulo, campo in (("Busca", self.busca), ("Situação", self.situacao), ("Grupo", self.grupo)):
            formulario = QFormLayout()
            formulario.addRow(rotulo, campo)
            filtros.addLayout(formulario)
        self.btn_atualizar = QPushButton("Consultar / atualizar (F5)")
        self.btn_atualizar.clicked.connect(self.atualizar)
        filtros.addWidget(self.btn_atualizar)
        layout.addLayout(filtros)
        self.grade = self._tabela([
            "Situação", "Código", "Produto", "Grupo", "Saldo", "Mínimo",
            "Reposição sugerida", "Último custo", "Valor em estoque", "Última atualização",
        ])
        self.grade.itemSelectionChanged.connect(self.mostrar_historico)
        layout.addWidget(self.grade, 2)
        self.detalhe = texto("Selecione um produto para consultar os últimos movimentos.", "suave")
        layout.addWidget(self.detalhe)
        self.historico = self._tabela(["Quando", "Movimento", "Quantidade", "Saldo após"])
        layout.addWidget(self.historico, 1)
        self.mensagem = texto("", "aviso")
        layout.addWidget(self.mensagem)
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(self.reject)
        layout.addWidget(fechar)
        QShortcut(QKeySequence("F5"), self, activated=self.atualizar)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.busca.setFocus)
        self.atualizar()

    @staticmethod
    def _tabela(cabecalhos):
        tabela = QTableWidget(0, len(cabecalhos))
        tabela.setHorizontalHeaderLabels(cabecalhos)
        tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabela.setAlternatingRowColors(True)
        tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tabela.horizontalHeader().setStretchLastSection(True)
        return tabela

    def _exigir_acesso(self):
        if self.ctx.operador is None:
            raise ErroPermissao("Entre com um operador para consultar o estoque.")
        cadastro = self.ctx.cadastros.obter("operadores", self.ctx.operador_id)
        if cadastro is None or not cadastro["ativo"]:
            raise ErroPermissao("Operador inativo. Encerre a sessão.")
        self.ctx.acesso.exigir(self.ctx.acesso.operador(self.ctx.operador_id), "lanc_estoque")

    @staticmethod
    def _preencher(tabela, linhas):
        tabela.clearSelection()
        tabela.setRowCount(len(linhas))
        for linha, valores in enumerate(linhas):
            for coluna, valor in enumerate(valores):
                tabela.setItem(linha, coluna, QTableWidgetItem(str(valor)))

    def _limpar_historico(self):
        self.movimentos = []
        self.historico.setRowCount(0)
        self.detalhe.setText("Selecione um produto para consultar os últimos movimentos.")

    def _limpar(self):
        self.linhas = []
        self.grade.setRowCount(0)
        self.resumo.clear()
        self._limpar_historico()

    def atualizar(self):
        try:
            self._exigir_acesso()
            estoque = self.ctx.estoque
            resumo = estoque.resumo()
            grupos = estoque.grupos()
            grupo = self.grupo.currentData()
            linhas = estoque.painel(
                situacao=self.situacao.currentData(), texto=self.busca.text(), grupo=grupo)
        except ErroNegocio as erro:
            self._limpar()
            self.mensagem.setText(str(erro))
            return False
        self.grupo.clear()
        self.grupo.addItem("Todos os grupos", None)
        for nome in grupos:
            self.grupo.addItem(nome, nome)
        if grupo is not None:
            # Preserva o filtro mesmo se o grupo tiver sido removido durante a consulta.
            indice = self.grupo.findData(grupo)
            if indice < 0:
                self.grupo.addItem(grupo, grupo)
                indice = self.grupo.count() - 1
            self.grupo.setCurrentIndex(indice)
        self.linhas = linhas
        self.grade.blockSignals(True)
        try:
            self._preencher(self.grade, [
                (ROTULOS[p["situacao"]], p["codigo"], p["nome"], p["grupo"],
                 "—" if p["situacao"] == "livre" else
                 f"{fmt.fmt_qtd(p['qt_atual'], fmt.CASAS_QTD)} {p['unidade']}",
                 fmt.fmt_qtd(p["estoque_minimo"], fmt.CASAS_QTD),
                 fmt.fmt_qtd(p["repor"], fmt.CASAS_QTD),
                 fmt.fmt_brl(p["ult_preco_cent"]),
                 "—" if p["situacao"] == "livre" else fmt.fmt_brl(p["valor_cent"]),
                 fmt.fmt_datahora(p["ult_atualizacao"]) or "—")
                for p in linhas
            ])
        finally:
            self.grade.blockSignals(False)
        self._limpar_historico()
        self.resumo.setText(
            f"Resumo geral (ativos) • {resumo['total']} controlado(s) • "
            f"{resumo['sem']} sem estoque • {resumo['ponto']} para repor • "
            f"{resumo['normal']} normal(is) • {resumo['livre']} sem controle • "
            f"Valor: {fmt.fmt_brl(resumo['valor_cent'])} (saldo × último custo).")
        self.mensagem.setText(
            f"{len(linhas)} produto(s) encontrado(s)." if linhas else
            "Nenhum produto encontrado. Consulte também o filtro Sem controle.")
        return True

    def mostrar_historico(self):
        self._limpar_historico()
        linha = self.grade.currentRow()
        if not self.grade.selectedItems() or not 0 <= linha < len(self.linhas):
            return
        try:
            self._exigir_acesso()
            produto = self.linhas[linha]
            movimentos = self.ctx.estoque.historico(produto["id"], limite=self.LIMITE_HISTORICO)
        except ErroNegocio as erro:
            self._limpar()
            self.mensagem.setText(str(erro))
            return
        self.movimentos = movimentos
        self._preencher(self.historico, [
            (fmt.fmt_datahora(m["criado_em"]), m["rotulo"],
             fmt.fmt_qtd(m["quantidade"], fmt.CASAS_QTD),
             fmt.fmt_qtd(m["qt_apos"], fmt.CASAS_QTD))
            for m in movimentos
        ])
        self.detalhe.setText(
            f"{produto['nome']} • até {self.LIMITE_HISTORICO} movimentos, mais recentes primeiro "
            f"• unidade: {produto['unidade']}" +
            (" • nenhum movimento registrado." if not movimentos else ""))
