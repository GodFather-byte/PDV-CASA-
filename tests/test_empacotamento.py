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


class TesteWorkflowDeBuild(unittest.TestCase):
    """O GitHub Actions que gera o instalador para baixar: não dá para rodá-lo aqui, então ao menos garante o que ele promete."""
    texto = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")

    def test_gera_programa_e_instalador_e_guarda_para_baixar(self):
        for trecho in ("windows-latest", "python build_pdv.py", "upload-artifact", "WillPDV-Setup-*.exe", "choco install innosetup"):
            self.assertIn(trecho, self.texto)

    def test_confere_o_programa_empacotado_e_o_instalado_antes_de_entregar(self):
        self.assertGreaterEqual(self.texto.count("--autoteste"), 2)           # no .exe e no instalado
        self.assertIn("/VERYSILENT", self.texto)                              # instala de verdade
        self.assertLess(self.texto.index("--autoteste"), self.texto.index("actions/upload-artifact"))

    def test_so_a_publicacao_na_release_escreve_no_repositorio(self):
        self.assertIn("permissions:\n  contents: read", self.texto)
        self.assertEqual(self.texto.count("contents: write"), 1)


class TesteChavesForaDoRepositorio(unittest.TestCase):
    raiz = Path(__file__).resolve().parents[1]

    def test_nenhuma_chave_privada_nem_licenca_no_repositorio(self):
        for caminho in self.raiz.rglob("*.py"):
            if "tests" in caminho.parts or ".venv" in caminho.parts:
                continue
            self.assertNotIn("PRIVATE KEY", caminho.read_text(encoding="utf-8", errors="ignore"), caminho)


if __name__ == "__main__":
    unittest.main()
