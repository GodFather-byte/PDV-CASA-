"""Impressão térmica (ESC/POS), transportes, gaveta pela impressora, roteamento do
ImpressaoController, reimpressão de cupom e migração de esquema v1 -> v2."""
from __future__ import annotations

import contextlib
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from src.controllers.config_controller import ConfigController
from src.controllers.impressao_controller import ImpressaoController
from src.core.erros import ErroNegocio
from src.database.conexao import BancoDados
from src.database.esquema import MAQUINAS_DDL, VERSAO_ESQUEMA
from src.hardware import impressora_termica as term
from src.hardware.dispositivos import DispositivoIndisponivel, Gaveta
from src.hardware.impressora_termica import ErroImpressao, ImpressoraTermica
from tests.test_caixa import BaseCaixa


@contextlib.contextmanager
def impressora_falsa():
    """Servidor TCP que aceita uma conexão e guarda os bytes recebidos. Devolve (endereco, caixa)."""
    recebido: dict = {}
    pronto = threading.Event()
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    porta = srv.getsockname()[1]

    def aceitar():
        pronto.set()
        try:
            con, _ = srv.accept()
            dados = b""
            con.settimeout(2)
            try:
                while True:
                    pedaco = con.recv(4096)
                    if not pedaco:
                        break
                    dados += pedaco
            except OSError:
                pass
            recebido["dados"] = dados
            con.close()
        except OSError:
            pass
    th = threading.Thread(target=aceitar, daemon=True)
    th.start()
    pronto.wait()
    try:
        yield f"127.0.0.1:{porta}", recebido
    finally:
        th.join(timeout=3)
        srv.close()


class TesteEscPos(unittest.TestCase):
    def test_bytes_basicos(self):
        b = term.texto_para_escpos("LINHA 1\nLINHA 2", codepage="cp850", cortar=True)
        self.assertTrue(b.startswith(b"\x1b@"))              # inicializa
        self.assertIn(b"\x1bt\x02", b)                        # CP850 = tabela 2
        self.assertIn(b"\x1dV\x01", b)                        # corte parcial
        self.assertNotIn(b"\x1bp", b)                         # sem gaveta

    def test_codepage_por_nome(self):
        self.assertIn(b"\x1bt\x03", term.texto_para_escpos("x", codepage="cp860"))
        self.assertIn(b"\x1bt\x10", term.texto_para_escpos("x", codepage="cp1252"))
        self.assertNotIn(b"\x1bt", term.texto_para_escpos("x", codepage="utf-8"))  # utf-8: não seleciona tabela

    def test_acentos_na_pagina_de_codigo(self):
        b = term.texto_para_escpos("ação pão café", codepage="cp850")
        self.assertIn("ação pão café".encode("cp850"), b)
        self.assertNotIn("ção".encode("utf-8"), b)            # nunca UTF-8 cru

    def test_enfase_por_linha(self):
        b = term.texto_para_escpos("LOJA\nitem\nTOTAL: 10,00", negrito_linhas=1, grande_prefixos=("TOTAL",))
        self.assertIn(b"\x1bE\x01", b)                        # negrito (cabeçalho)
        self.assertIn(b"\x1d!\x01", b)                        # TOTAL em dobro de altura
        self.assertIn(b"\x1d!\x00", b)                        # volta ao normal depois

    def test_gaveta_e_pino(self):
        self.assertEqual(term.pulso_gaveta(0), b"\x1bp\x00\x19\xfa")
        self.assertEqual(term.pulso_gaveta(1), b"\x1bp\x01\x19\xfa")
        b = term.texto_para_escpos("x", abrir_gaveta=True, pino_gaveta=1)
        self.assertIn(b"\x1bp\x01\x19\xfa", b)

    def test_corte_total_vs_parcial(self):
        self.assertIn(b"\x1dV\x00", term.cortar_papel(parcial=False))
        self.assertIn(b"\x1dV\x01", term.cortar_papel(parcial=True))


class TesteTransportes(unittest.TestCase):
    def test_rede(self):
        with impressora_falsa() as (endereco, recebido):
            ImpressoraTermica(conexao="rede", endereco=endereco).imprimir("Cupom\nTOTAL: 5,00")
        self.assertTrue(recebido["dados"].startswith(b"\x1b@"))

    def test_rede_offline_da_erro_claro(self):
        with self.assertRaises(ErroImpressao) as e:
            # porta 1 fechada
            term.enviar_rede("127.0.0.1:1", b"x", timeout=1)
        self.assertIn("127.0.0.1", str(e.exception))

    def test_endereco_invalido(self):
        with self.assertRaises(ErroImpressao):
            term.enviar_rede("", b"x")
        with self.assertRaises(ErroImpressao):
            term.enviar_rede("host:abc", b"x")

    def test_arquivo(self):
        with tempfile.TemporaryDirectory() as d:
            arq = os.path.join(d, "saida.prn")
            ImpressoraTermica(conexao="arquivo", endereco=arq).imprimir("teste")
            self.assertTrue(Path(arq).read_bytes().startswith(b"\x1b@"))

    def test_serial_e_spooler_sem_biblioteca(self):
        # pyserial/pywin32 não estão instalados neste ambiente: mensagem clara, não crash.
        if term.enviar_serial.__module__:  # sempre verdadeiro; só documenta a intenção
            try:
                import serial  # noqa: F401
                self.skipTest("pyserial instalado")
            except ImportError:
                with self.assertRaises(ErroImpressao) as e:
                    term.enviar_serial("COM9", b"x")
                self.assertIn("pyserial", str(e.exception))
        try:
            import win32print  # noqa: F401
        except ImportError:
            with self.assertRaises(ErroImpressao) as e:
                term.enviar_spooler("Qualquer", b"x")
            self.assertIn("pywin32", str(e.exception))

    def test_nenhuma_conexao(self):
        with self.assertRaises(ErroImpressao):
            ImpressoraTermica(conexao="nenhuma").enviar_bytes(b"x")


class TesteImpressoraConfig(unittest.TestCase):
    def test_da_maquina(self):
        imp = ImpressoraTermica.da_maquina({
            "impressora_termica_conexao": "rede", "impressora_termica_endereco": "10.0.0.5:9100",
            "impressora_termica_codepage": "cp860", "colunas_fita": 32,
            "impressora_termica_cortar": 0, "impressora_termica_gaveta": 1, "impressora_termica_pino": 1})
        self.assertEqual((imp.conexao, imp.endereco, imp.codepage, imp.colunas), ("rede", "10.0.0.5:9100", "cp860", 32))
        self.assertEqual((imp.cortar, imp.tem_gaveta, imp.pino_gaveta), (False, True, 1))
        self.assertTrue(imp.configurada)

    def test_erro_de_impressao_e_erro_de_negocio(self):
        self.assertTrue(issubclass(ErroImpressao, ErroNegocio))


class TesteGaveta(unittest.TestCase):
    def test_abre_pela_impressora(self):
        with impressora_falsa() as (endereco, recebido):
            imp = ImpressoraTermica(conexao="rede", endereco=endereco, tem_gaveta=True, pino_gaveta=0)
            Gaveta(instalada=True, impressora=imp).abrir()
        self.assertEqual(recebido["dados"], term.INICIALIZAR + term.pulso_gaveta(0))

    def test_sem_impressora_pede_a_chave(self):
        imp = ImpressoraTermica(conexao="nenhuma", tem_gaveta=False)
        with self.assertRaises(DispositivoIndisponivel) as e:
            Gaveta(instalada=True, impressora=imp).abrir()
        self.assertIn("chave", str(e.exception).lower())

    def test_nada_configurado(self):
        with self.assertRaises(DispositivoIndisponivel):
            Gaveta(instalada=False, impressora=None).abrir()


class TesteRoteamento(BaseCaixa):
    """ImpressaoController escolhe a saída conforme o modo da máquina."""

    def setUp(self):
        super().setUp()
        self.imp = ImpressaoController(self.banco)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # histórico vai para a pasta temporária (não suja o repositório)
        self.imp.pasta_saida = lambda: Path(self.tmp.name)
        self.cfg = ConfigController(self.banco)

    def _modo_termica(self, arquivo):
        self.cfg.salvar_maquina({"modo_impressao": "termica", "impressora_termica_conexao": "arquivo",
                                 "impressora_termica_endereco": arquivo, "impressora_termica_codepage": "cp850",
                                 "impressora_termica_gaveta": "S"})

    def _venda_fechada(self, forma="Dinheiro"):
        vid = self.vender((self.skol, 2))
        self.pagar(vid, forma, 2000)
        self.caixa.fechar(vid)
        return vid

    def test_modo_tela_nao_imprime(self):
        self.assertTrue(self.imp.deve_mostrar_na_tela())
        vid = self._venda_fechada()
        caminho = self.imp.enviar(self.imp.cupom(vid), "cupom", tipo="cupom")
        self.assertTrue(Path(caminho).exists())              # histórico gravado
        self.assertEqual(self.imp.modo(), "tela")

    def test_modo_termica_envia_escpos_com_total_grande_e_gaveta(self):
        arq = os.path.join(self.tmp.name, "cupom.prn")
        self._modo_termica(arq)
        vid = self._venda_fechada()
        self.imp.enviar(self.imp.cupom(vid), "cupom", tipo="cupom", abrir_gaveta=True)
        dados = Path(arq).read_bytes()
        self.assertTrue(dados.startswith(b"\x1b@"))
        self.assertIn(b"\x1bt\x02", dados)                    # CP850
        self.assertIn(b"\x1d!\x01", dados)                    # TOTAL em destaque
        self.assertIn(b"\x1bp", dados)                        # gaveta abriu (venda em dinheiro)
        self.assertIn("TOTAL".encode("cp850"), dados)

    def test_termica_offline_levanta_erro_de_negocio(self):
        self._modo_termica("")  # endereço de arquivo vazio
        self.banco.executar("UPDATE maquinas SET impressora_termica_conexao='rede', impressora_termica_endereco='127.0.0.1:1'")
        vid = self._venda_fechada()
        with self.assertRaises(ErroNegocio):
            self.imp.enviar(self.imp.cupom(vid), "cupom", tipo="cupom")

    def test_reimpressao_marca_segunda_via(self):
        arq = os.path.join(self.tmp.name, "r.prn")
        self._modo_termica(arq)
        vid = self._venda_fechada()
        texto = self.imp.reimprimir_cupom(vid)
        self.assertIn("SEGUNDA VIA", texto)
        self.assertIn("SEGUNDA VIA".encode("cp850"), Path(arq).read_bytes())

    def test_pedido_remoto_por_rede_nao_vai_para_a_impressora_do_caixa(self):
        with impressora_falsa() as (endereco, recebido):
            self.banco.executar("UPDATE maquinas SET impressora_remota_conexao='rede', impressora_remota_endereco=?", (endereco,))
            self.banco.executar("UPDATE subgrupos SET impressora_remota=1")
            vid = self.caixa.abrir_balcao()
            item = self.caixa.adicionar_item(vid, self.skol, 1)
            tickets = self.imp.pedido_remoto(vid, [item])
            self.assertTrue(tickets)
            for sub, texto in tickets.items():
                self.imp.enviar_remoto(texto, f"pedido_{sub}")
        self.assertTrue(recebido["dados"].startswith(b"\x1b@"))

    def test_gaveta_do_contexto_abre_pela_termica(self):
        from src.ui.contexto import Contexto
        with impressora_falsa() as (endereco, recebido):
            self.banco.executar(
                "UPDATE maquinas SET impressora_termica_conexao='rede', impressora_termica_endereco=?, impressora_termica_gaveta=1, gaveta=1",
                (endereco,))
            ctx = Contexto(self.banco)
            ctx.gaveta().abrir()
        self.assertIn(b"\x1bp", recebido["dados"])


class TesteMigracao(unittest.TestCase):
    def test_v1_migra_ate_a_versao_atual_preservando_dados_e_adicionando_termica(self):
        import shutil
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)              # roda por último (LIFO)
        caminho = os.path.join(d, "v1.db")
        c = sqlite3.connect(caminho)
        c.execute("CREATE TABLE config (chave TEXT PRIMARY KEY, valor TEXT)")
        c.execute("""CREATE TABLE maquinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, terminal INTEGER NOT NULL UNIQUE DEFAULT 1,
            nome_computador TEXT, descricao TEXT,
            modo_impressao TEXT NOT NULL DEFAULT 'tela' CHECK (modo_impressao IN ('tela','arquivo','windows')),
            colunas_fita INTEGER NOT NULL DEFAULT 40, impressora_remota_pasta TEXT,
            balanca TEXT NOT NULL DEFAULT 'Nenhuma', balanca_porta TEXT,
            gaveta INTEGER NOT NULL DEFAULT 0, leitor_optico INTEGER NOT NULL DEFAULT 0)""")
        c.execute("INSERT INTO maquinas (terminal, nome_computador, colunas_fita) VALUES (1, 'CAIXA-01', 48)")
        c.execute("PRAGMA user_version = 1")
        c.commit()
        c.close()
        b = BancoDados(caminho)
        self.addCleanup(b.fechar)                            # roda antes do rmtree (LIFO)
        self.assertEqual(b.valor("PRAGMA user_version"), VERSAO_ESQUEMA)
        m = b.um("SELECT * FROM maquinas WHERE terminal = 1")
        self.assertEqual((m["nome_computador"], m["colunas_fita"]), ("CAIXA-01", 48))
        self.assertEqual(m["impressora_termica_codepage"], "cp850")       # coluna nova com default
        b.executar("UPDATE maquinas SET modo_impressao = 'termica'")       # CHECK antigo não impede mais
        self.assertEqual(b.valor("SELECT modo_impressao FROM maquinas"), "termica")

    def test_banco_novo_ja_nasce_na_versao_atual(self):
        b = BancoDados(":memory:")
        self.addCleanup(b.fechar)
        self.assertEqual(b.valor("PRAGMA user_version"), VERSAO_ESQUEMA)
        self.assertIn("impressora_termica_conexao", [r[1] for r in b.todos("PRAGMA table_info(maquinas)")])


class TesteConfigMaquina(BaseCaixa):
    def test_salvar_campos_termicos(self):
        cfg = ConfigController(self.banco)
        cfg.salvar_maquina({"modo_impressao": "termica", "impressora_termica_conexao": "rede",
                            "impressora_termica_endereco": "192.168.0.50:9100", "impressora_termica_cortar": "S",
                            "impressora_termica_gaveta": "S", "impressora_termica_pino": "1", "colunas_fita": "48"})
        m = cfg.maquina()
        self.assertEqual(m["modo_impressao"], "termica")
        self.assertEqual(m["impressora_termica_endereco"], "192.168.0.50:9100")
        self.assertEqual((m["impressora_termica_cortar"], m["impressora_termica_gaveta"], m["impressora_termica_pino"]), (1, 1, 1))

    def test_pino_invalido(self):
        from src.core.erros import ErroValidacao
        with self.assertRaises(ErroValidacao):
            ConfigController(self.banco).salvar_maquina({"impressora_termica_pino": "5"})


if __name__ == "__main__":
    unittest.main()
