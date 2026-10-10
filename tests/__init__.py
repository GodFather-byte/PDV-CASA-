"""Pacote dos testes.

Protege a suíte de um aborto do Tcl ("Tcl_AsyncDelete: async handler deleted by the wrong thread"): a coleta automática de
lixo cíclico roda na thread que alocou memória, inclusive as de fundo (Telegram, fila de impressão), e destruir o interpretador
do Tk fora da thread que o criou derruba o processo inteiro. Aqui a coleta automática fica desligada e cada teste termina com uma
coleta feita pela thread principal, a dona do Tk. (Reproduzido na própria `main`: uma thread que só fabrica lixo cíclico abortava
o test_ui; sem isso o aborto aparece ao acaso, conforme o momento em que o coletor dispara.)"""
from __future__ import annotations

import gc
import unittest

gc.disable()

_executar = unittest.TestCase.run


def _executar_e_coletar(self, result=None):
    try:
        return _executar(self, result)
    finally:
        gc.collect()


unittest.TestCase.run = _executar_e_coletar
