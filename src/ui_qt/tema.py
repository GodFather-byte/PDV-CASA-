"""Identidade visual compartilhada pelas telas do piloto Qt."""
import os
import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QLabel


ESTILO = """
QWidget { background: #101827; color: #e6edf7; font-family: 'Segoe UI'; font-size: 14px; }
QMainWindow, QDialog { background: #101827; }
QFrame#cartao { background: #1b2739; border: 1px solid #324158; border-radius: 12px; }
QLabel { background: transparent; }
QLabel#titulo { font-size: 28px; font-weight: 700; }
QLabel#marca { color: #5ee2bb; font-size: 24px; font-weight: 800; }
QLabel#suave { color: #afbdd1; }
QLabel#aviso { color: #ffd28a; }
QPushButton { background: #24364d; border: 1px solid #405570; border-radius: 7px;
              padding: 11px 18px; text-align: left; }
QPushButton:hover { background: #304864; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus { border: 2px solid #5ee2bb; }
QPushButton#primario { background: #187e65; border-color: #32b38e; font-weight: 700; }
QPushButton:disabled { color: #8190a6; background: #1b2534; }
QLineEdit, QComboBox { background: #182437; border: 1px solid #405570;
                       border-radius: 6px; padding: 9px; min-height: 20px; }
QComboBox QAbstractItemView { background: #182437; selection-background-color: #187e65; }
QTableWidget { background: #182437; alternate-background-color: #1d2d43;
               gridline-color: #324158; selection-background-color: #187e65; }
QHeaderView::section { background: #24364d; color: #e6edf7; padding: 9px; border: 0; }
QTabWidget::pane { border: 1px solid #324158; }
QTabBar::tab { background: #24364d; padding: 10px; }
QTabBar::tab:selected { background: #187e65; }
QScrollArea { border: 0; }
"""


def aplicar(aplicacao: QApplication) -> None:
    # O plugin offscreen do Windows não enumera fontes do sistema por conta própria.
    if sys.platform == "win32" and "Segoe UI" not in QFontDatabase.families():
        pasta = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for nome in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf"):
            caminho = pasta / nome
            if caminho.is_file():
                QFontDatabase.addApplicationFont(str(caminho))
    aplicacao.setStyle("Fusion")
    aplicacao.setStyleSheet(ESTILO)
    aplicacao.setApplicationName("WillPDV • Qt piloto")


def texto(conteudo: str, nome: str = "", quebra: bool = True) -> QLabel:
    rotulo = QLabel(conteudo)
    rotulo.setObjectName(nome)
    rotulo.setWordWrap(quebra)
    return rotulo
