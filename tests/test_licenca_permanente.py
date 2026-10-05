"""Licença permanente emitida pelo dono (tools/gerar_licenca_permanente.py + pdv_licenca.py + serviço)."""
from __future__ import annotations

import base64
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdv_licenca
from pdv_licenca import CodigoInvalido
from src.core.servico_licenca import ServicoLicenca
from tests.base import BaseTeste

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from tools import gerar_licenca_permanente as ferramenta
    TEM_CRYPTO = True
except ImportError:                                   # pragma: no cover
    TEM_CRYPTO = False

MID = "a1b2c3d4" * 4
OUTRO = "0f" * 16


def _par(pasta: Path):
    privada = Ed25519PrivateKey.generate()
    arquivo = pasta / "teste.key"
    arquivo.write_bytes(privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                              serialization.NoEncryption()))
    pem = privada.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return privada, arquivo, pem.decode()


@unittest.skipUnless(TEM_CRYPTO, "biblioteca cryptography não instalada")
class TestePermanente(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)
        self.privada, self.arquivo_chave, self.pem = _par(self.pasta)
        self.codigo = ferramenta.emitir(str(self.arquivo_chave), MID, "Boate Teste")

    def ativar(self, codigo=None, mid=MID):
        return pdv_licenca.ativar_permanente(self.codigo if codigo is None else codigo, self.pem, self.pasta, mid)

    def test_emitir_e_ativar_guarda_o_codigo_na_pasta_de_dados(self):
        dados = self.ativar()
        self.assertEqual((dados["machine_id"], dados["nome"]), (MID, "Boate Teste"))
        self.assertTrue((self.pasta / "licenca_permanente.json").exists())
        self.assertIsNotNone(pdv_licenca.permanente_valida(self.pem, self.pasta, MID))

    def test_checar_licenca_libera_sem_rede_sem_chave_e_sem_vencer(self):
        self.ativar()

        def sem_rede(*a, **k):
            raise AssertionError("licença permanente não pode consultar o servidor")
        r = pdv_licenca.checar_licenca("https://x.test", "", self.pem, self.pasta, http=sem_rede, mid=MID,
                                       agora=datetime.now(timezone.utc) + timedelta(days=365 * 20))
        self.assertEqual((r.permitido, r.motivo, r.aviso), (True, "permanente", ""))

    def test_vale_so_no_computador_para_o_qual_foi_emitida(self):
        with self.assertRaisesRegex(CodigoInvalido, "outro computador"):
            self.ativar(mid=OUTRO)
        self.ativar()
        self.assertIsNone(pdv_licenca.permanente_valida(self.pem, self.pasta, OUTRO))   # arquivo copiado para outro PC

    def test_codigo_adulterado_ou_de_outra_chave_e_recusado(self):
        corpo = json.loads(base64.urlsafe_b64decode(self.codigo[len("PDVP1."):] + "=="))
        adulterado = json.loads(corpo["payload"])
        adulterado["machine_id"] = OUTRO
        corpo["payload"] = json.dumps(adulterado, separators=(",", ":"), sort_keys=True)
        falso = pdv_licenca.montar_codigo_permanente(corpo["payload"], corpo["signature"])
        with self.assertRaisesRegex(CodigoInvalido, "assinatura"):
            self.ativar(falso, mid=OUTRO)
        _, outra_chave, _ = _par(self.pasta)
        de_outro = ferramenta.emitir(str(outra_chave), MID)
        with self.assertRaisesRegex(CodigoInvalido, "assinatura"):
            self.ativar(de_outro)

    def test_token_comum_assinado_nao_serve_como_permanente(self):
        payload = json.dumps({"license_key": "K", "machine_id": MID, "exp": 9999999999})
        assinatura = base64.b64encode(self.privada.sign(payload.encode())).decode()
        with self.assertRaisesRegex(CodigoInvalido, "não é de uma licença permanente"):
            self.ativar(pdv_licenca.montar_codigo_permanente(payload, assinatura))

    def test_lixo_e_recusado_e_quebras_de_linha_do_copiar_e_colar_sao_aceitas(self):
        for lixo in ("", "abc", "PDVP1.", "PDVP1.@@@", "PDVL1.a.b"):
            with self.subTest(lixo=lixo), self.assertRaises(CodigoInvalido):
                self.ativar(lixo)
        quebrado = "\n  ".join(self.codigo[i:i + 40] for i in range(0, len(self.codigo), 40))
        self.assertEqual(self.ativar(quebrado)["machine_id"], MID)

    def test_remover_desfaz_a_ativacao(self):
        self.ativar()
        pdv_licenca.remover_permanente(self.pasta)
        self.assertIsNone(pdv_licenca.permanente_valida(self.pem, self.pasta, MID))

    def test_ferramenta_valida_entrada_e_nao_imprime_a_chave_privada(self):
        for args in (["--chave-privada", str(self.arquivo_chave), "--machine-id", "curto"],
                     ["--chave-privada", str(self.pasta / "nao_existe.key"), "--machine-id", MID]):
            with self.subTest(args=args), redirect_stderr(io.StringIO()) as err:
                self.assertEqual(ferramenta.main(args), 1)
                self.assertIn("Erro", err.getvalue())
        saida = io.StringIO()
        with redirect_stdout(saida):
            self.assertEqual(ferramenta.main(["--chave-privada", str(self.arquivo_chave), "--machine-id", MID.upper(),
                                              "--nome", "Boate X"]), 0)
        self.assertIn("PDVP1.", saida.getvalue())
        self.assertNotIn("PRIVATE", saida.getvalue())
        codigo = next(l for l in saida.getvalue().splitlines() if l.startswith("PDVP1."))
        self.assertEqual(self.ativar(codigo)["nome"], "Boate X")


@unittest.skipUnless(TEM_CRYPTO, "biblioteca cryptography não instalada")
class TesteServicoPermanente(BaseTeste):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)
        _, arquivo, self.pem = _par(self.pasta)
        self.s = ServicoLicenca(self.banco, servidor="https://x.test", chave_publica=self.pem, pasta=self.pasta)
        self.codigo = ferramenta.emitir(str(arquivo), pdv_licenca.machine_id())

    def test_ativar_libera_o_caixa_e_muda_o_status(self):
        self.s.resultado = pdv_licenca.Resultado(False, "bloqueada")
        self.assertTrue(self.s.bloqueado)
        self.assertFalse(self.s.tem_permanente())
        self.s.ativar_permanente(self.codigo)
        self.assertTrue(self.s.tem_permanente())
        self.assertFalse(self.s.bloqueado)
        self.assertIn("permanente", self.s.status_texto())

    def test_codigo_ruim_nao_ativa_nada(self):
        with self.assertRaises(CodigoInvalido):
            self.s.ativar_permanente("PDVP1.lixo")
        self.assertFalse(self.s.tem_permanente())

    def test_verificacao_real_depois_de_ativar_continua_permitida(self):
        self.s.ativar_permanente(self.codigo)
        s2 = ServicoLicenca(self.banco, servidor="https://x.test", chave_publica=self.pem, pasta=self.pasta)
        self.assertTrue(s2.iniciar_verificacao())
        for _ in range(200):
            if s2.coletar():
                break
            import time
            time.sleep(0.01)
        self.assertEqual(s2.resultado.motivo, "permanente")


if __name__ == "__main__":
    unittest.main()
