"""Telas do licenciamento (bloqueio, faixa de aviso e tela Licença) contra um serviço com resultado simulado."""
from __future__ import annotations

import tkinter as tk
import unittest
from types import SimpleNamespace

from pdv_licenca import AVISO_ATRASO, Resultado
from src.core.servico_licenca import ServicoLicenca
from src.ui import tema
from src.ui.licenca_ui import GuardaLicenca, JanelaBloqueio
from tests.base import BaseTeste


def _tk_disponivel() -> bool:
    try:
        r = tk.Tk()
        r.destroy()
        return True
    except tk.TclError:
        return False


@unittest.skipUnless(_tk_disponivel(), "Tk indisponível neste ambiente")
class TesteTelasLicenca(BaseTeste):
    def setUp(self):
        super().setUp()
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        tema.aplicar_tema(self.root)
        self.app = SimpleNamespace(root=self.root, banco=self.banco, lbl_licenca=None, lbl_backup=None)
        self.guarda = GuardaLicenca(self.app)
        self.s = self.guarda.servico = ServicoLicenca(self.banco, servidor="https://x.test", chave_publica="PEM",
                                                      checar=lambda *a: self.proximo)
        self.s.salvar_chave("ABCD-1234")
        self.proximo = Resultado(False, "bloqueada")

    def test_bloqueio_mostra_motivo_contato_e_tentar_novamente_libera(self):
        self.banco.cfg_set("lic_suporte", "suporte@exemplo.test")
        self.s.resultado = Resultado(False, "outra_maquina")
        janela = JanelaBloqueio(self.root, self.s)
        self.root.update()
        textos = []

        def coletar(w):
            textos.append(str(w.cget("text")) if "text" in w.keys() else "")
            for f in w.winfo_children():
                coletar(f)
        coletar(janela)
        tudo = " | ".join(textos)
        self.assertIn("outro computador", tudo)
        self.assertIn("suporte@exemplo.test", tudo)
        self.assertIn("Tentar novamente", tudo)
        self.proximo = Resultado(True, "ok")
        janela.tentar()
        for _ in range(100):
            self.root.update()
            if not janela.winfo_exists():
                break
            self.root.after(20)
        self.assertFalse(janela.winfo_exists())
        self.assertFalse(janela.saiu)
        self.assertFalse(self.s.bloqueado)

    def test_faixa_de_aviso_aparece_e_some_sem_bloquear(self):
        painel = tk.Frame(self.root)
        painel.pack()
        self.app.lbl_backup = tk.Label(painel)
        self.app.lbl_backup.pack()
        self.app.lbl_licenca = tk.Label(painel)
        self.s.resultado = Resultado(True, "atraso", AVISO_ATRASO)
        self.guarda.atualizar_faixa()
        self.root.update()
        self.assertEqual(self.app.lbl_licenca.cget("text"), AVISO_ATRASO)
        self.assertEqual(self.app.lbl_licenca.winfo_manager(), "pack")
        self.s.resultado = Resultado(True, "ok")
        self.guarda.atualizar_faixa()
        self.assertEqual(self.app.lbl_licenca.winfo_manager(), "")

    def test_bloqueio_com_venda_aberta_e_adiado_sem_abrir_tela(self):
        import uuid
        self.banco.executar("INSERT INTO vendas(uuid, status, modalidade, aberta_em) VALUES (?, 'aberta', 'mesa', '2026-10-03 20:00:00')",
                            (str(uuid.uuid4()),))
        self.s.resultado = Resultado(False, "bloqueada")
        self.guarda.avaliar()
        self.root.update()
        self.assertFalse(self.guarda._bloqueio_aberto)
        self.assertFalse([w for w in self.root.winfo_children() if isinstance(w, JanelaBloqueio)])
        self.assertIsNotNone(self.guarda._reavaliacao)       # olha de novo mais tarde
        self.root.after_cancel(self.guarda._reavaliacao)


if __name__ == "__main__":
    unittest.main()
