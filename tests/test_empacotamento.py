"""Dados do executável (PyInstaller) e arquivos que nunca podem ir para o repositório."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.database import conexao
from src.database.conexao import BancoDados


class TesteDadosDoExecutavel(unittest.TestCase):
    def test_codigo_fonte_usa_a_raiz_do_projeto(self):
        self.assertTrue((conexao._raiz_dados() / "src" / "database" / "conexao.py").exists())

    def test_executavel_grava_em_localappdata_e_nao_dentro_do_pacote(self):
        with tempfile.TemporaryDirectory() as pasta, mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.dict(os.environ, {"LOCALAPPDATA": pasta}):
            self.assertEqual(conexao._raiz_dados(), Path(pasta) / "WILL-PDV")

    def test_banco_cria_a_pasta_que_ainda_nao_existe(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "novo" / "dados" / "loja.db"
            BancoDados(str(destino)).fechar()
            self.assertTrue(destino.exists())

    def test_gitignore_cobre_banco_wal_build_e_chaves(self):
        linhas = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8").splitlines()
        for padrao in ("*.db", "*.db-wal", "*.db-shm", "*.db-journal", "build/", "dist/", "*.key"):
            self.assertIn(padrao, linhas)


class TesteEmpacotamentoDaLicenca(unittest.TestCase):
    raiz = Path(__file__).resolve().parents[1]

    def test_requirements_traz_cryptography(self):
        texto = (self.raiz / "requirements.txt").read_text(encoding="utf-8")
        self.assertTrue(any(l.startswith("cryptography") for l in texto.splitlines()))

    def test_executavel_inclui_modulo_e_biblioteca_de_criptografia(self):
        sys.path.insert(0, str(self.raiz))
        self.addCleanup(sys.path.remove, str(self.raiz))
        import build_pdv
        opcoes = " ".join(build_pdv.OPCOES_LICENCA)
        for item in ("pdv_licenca", "src.core.servico_licenca", "cryptography"):
            self.assertIn(item, opcoes)
        self.assertTrue((self.raiz / "pdv_licenca.py").exists())

    def test_nenhuma_chave_privada_nem_licenca_no_repositorio(self):
        for caminho in self.raiz.rglob("*.py"):
            if "tests" in caminho.parts or ".venv" in caminho.parts:
                continue
            self.assertNotIn("PRIVATE KEY", caminho.read_text(encoding="utf-8", errors="ignore"), caminho)


if __name__ == "__main__":
    unittest.main()
