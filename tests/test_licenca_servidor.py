"""Licenciamento por servidor (pdv_licenca.py + src/core/servico_licenca.py), com rede e Ed25519 simulados.

O par de chaves é gerado só dentro do teste; nenhuma chave real existe no repositório.
"""
from __future__ import annotations

import base64
import json
import tempfile
import time
import uuid
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdv_licenca
from pdv_licenca import Resultado, checar_licenca
from src.core import servico_licenca
from src.core.servico_licenca import ServicoLicenca, mascarar
from tests.base import BaseTeste

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    TEM_CRYPTO = True
except ImportError:                                   # pragma: no cover
    TEM_CRYPTO = False

CHAVE = "ABCD-1234-EFGH-5678"
MID = "m" * 32
AGORA = datetime(2026, 10, 3, 21, 0, 0, tzinfo=timezone.utc)
SERVER = "https://licencas.exemplo.test"


def _par():
    privada = Ed25519PrivateKey.generate()
    pem = privada.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return privada, pem.decode()


def _resposta(privada, status="ok", chave=CHAVE, mid=MID, emitido=AGORA, **extra):
    payload = json.dumps({"license_key": chave, "machine_id": mid, "iat": emitido.timestamp(), **extra})
    assinatura = base64.b64encode(privada.sign(payload.encode())).decode()
    return 200, {"status": status, "payload": payload, "signature": assinatura}


class Rede:
    """Servidor falso: devolve a resposta combinada ou simula internet caída."""

    def __init__(self, resposta=None, cai=False):
        self.resposta, self.cai, self.chamadas = resposta, cai, []

    def __call__(self, url, corpo, timeout):
        self.chamadas.append((url, corpo))
        if self.cai:
            raise OSError("sem internet")
        return self.resposta


@unittest.skipUnless(TEM_CRYPTO, "biblioteca cryptography não instalada")
class TesteCliente(unittest.TestCase):
    def setUp(self):
        self.privada, self.pem = _par()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)

    def checar(self, rede, agora=AGORA, chave=CHAVE):
        return checar_licenca(SERVER, chave, self.pem, self.pasta, http=rede, agora=agora, mid=MID)

    def test_servidor_ok_libera_e_salva_o_token(self):
        rede = Rede(_resposta(self.privada))
        r = self.checar(rede)
        self.assertTrue(r.permitido)
        self.assertEqual((r.motivo, r.aviso, r.offline), ("ok", "", False))
        self.assertEqual(rede.chamadas, [(f"{SERVER}/validar", {"license_key": CHAVE, "machine_id": MID})])
        self.assertTrue((self.pasta / "licenca.json").exists())

    def test_token_valido_offline_segue_com_o_ultimo_token(self):
        self.checar(Rede(_resposta(self.privada)))
        r = self.checar(Rede(cai=True), agora=AGORA + timedelta(days=3))
        self.assertTrue(r.permitido)
        self.assertTrue(r.offline)

    def test_token_expirado_sem_internet_bloqueia(self):
        self.checar(Rede(_resposta(self.privada)))
        r = self.checar(Rede(cai=True), agora=AGORA + timedelta(days=7, minutes=1))
        self.assertEqual((r.permitido, r.motivo), (False, "sem_token_valido"))

    def test_primeira_vez_sem_internet_nao_tem_token(self):
        r = self.checar(Rede(cai=True))
        self.assertEqual((r.permitido, r.motivo), (False, "sem_token_valido"))

    def test_erro_5xx_do_servidor_tambem_usa_o_token_salvo(self):
        self.checar(Rede(_resposta(self.privada)))
        r = self.checar(Rede((503, {})), agora=AGORA + timedelta(days=1))
        self.assertTrue(r.permitido and r.offline)

    def test_bloqueada_bloqueia_e_apaga_o_token_salvo(self):
        self.checar(Rede(_resposta(self.privada)))
        for motivo in ("bloqueada", "invalida", "outra_maquina"):
            with self.subTest(motivo=motivo):
                r = self.checar(Rede((403, {"status": motivo})))
                self.assertEqual((r.permitido, r.motivo), (False, motivo))
                self.assertFalse((self.pasta / "licenca.json").exists())
                self.checar(Rede(_resposta(self.privada)))   # volta a ter token para o próximo motivo
        # com o token apagado, cair a internet depois do 403 não libera de novo
        self.checar(Rede((403, {"status": "bloqueada"})))
        self.assertFalse(self.checar(Rede(cai=True)).permitido)

    def test_atraso_libera_com_aviso(self):
        r = self.checar(Rede(_resposta(self.privada, status="atraso")))
        self.assertTrue(r.permitido)
        self.assertEqual(r.motivo, "atraso")
        self.assertEqual(r.aviso, pdv_licenca.AVISO_ATRASO)
        offline = self.checar(Rede(cai=True), agora=AGORA + timedelta(days=1))   # o aviso continua offline
        self.assertEqual((offline.permitido, offline.aviso), (True, pdv_licenca.AVISO_ATRASO))

    def test_assinatura_falsa_nao_vale_nem_apaga_o_token_bom(self):
        self.checar(Rede(_resposta(self.privada)))
        outra, _ = _par()
        r = self.checar(Rede(_resposta(outra)), agora=AGORA + timedelta(days=1))   # servidor falso assinou com outra chave
        self.assertTrue(r.permitido and r.offline)                                    # seguiu no token bom
        sem_token = tempfile.TemporaryDirectory()
        self.addCleanup(sem_token.cleanup)
        r = checar_licenca(SERVER, CHAVE, self.pem, sem_token.name, http=Rede(_resposta(outra)), agora=AGORA, mid=MID)
        self.assertEqual((r.permitido, r.motivo), (False, "sem_token_valido"))

    def test_token_de_outra_maquina_ou_licenca_nao_serve(self):
        self.checar(Rede(_resposta(self.privada)))
        r = checar_licenca(SERVER, CHAVE, self.pem, self.pasta, http=Rede(cai=True), agora=AGORA, mid="x" * 32)
        self.assertFalse(r.permitido)
        self.assertFalse(self.checar(Rede(cai=True), chave="OUTRA-CHAVE").permitido)

    def test_relogio_voltado_nao_estende_o_token_offline(self):
        self.checar(Rede(_resposta(self.privada)))
        self.checar(Rede(cai=True), agora=AGORA + timedelta(days=6))            # registra que o relógio chegou ao dia 6
        r = self.checar(Rede(cai=True), agora=AGORA + timedelta(days=8))
        self.assertFalse(r.permitido)
        r = self.checar(Rede(cai=True), agora=AGORA)                            # relógio voltou ao dia 0: continua vencido
        self.assertFalse(r.permitido)

    def test_servidor_sem_https_e_chave_vazia_nao_consultam(self):
        rede = Rede(_resposta(self.privada))
        self.assertFalse(checar_licenca("http://servidor.exemplo.test", CHAVE, self.pem, self.pasta, http=rede, mid=MID).permitido)
        self.assertFalse(checar_licenca(SERVER, "  ", self.pem, self.pasta, http=rede, mid=MID).permitido)
        self.assertEqual(rede.chamadas, [])

    def test_token_salvo_nao_guarda_a_chave_em_texto_alem_do_payload_assinado(self):
        self.checar(Rede(_resposta(self.privada)))
        dados = json.loads((self.pasta / "licenca.json").read_text(encoding="utf-8"))
        self.assertEqual(set(dados), {"status", "payload", "signature", "recebido_em", "visto_em"})


class FalsoChecar:
    """Substitui checar_licenca no serviço: devolve o Resultado combinado (sem rede, sem cripto)."""

    def __init__(self, resultado):
        self.resultado, self.chamadas = resultado, []

    def __call__(self, servidor, chave, publica, pasta):
        self.chamadas.append((servidor, chave))
        return self.resultado


class TesteServico(BaseTeste):
    def servico(self, resultado=None, extra=None):
        self.falso = FalsoChecar(resultado or Resultado(True, "ok"))
        s = ServicoLicenca(self.banco, checar=self.falso, extra_em_andamento=extra, servidor=SERVER, chave_publica="PEM-DE-TESTE")
        s.salvar_chave(CHAVE)
        return s

    def verificar(self, s):
        self.assertTrue(s.iniciar_verificacao())
        for _ in range(200):
            if s.coletar():
                return
            time.sleep(0.01)
        self.fail("a verificação não terminou")

    def abrir_venda(self, status="aberta"):
        self.banco.executar("INSERT INTO vendas(uuid, status, modalidade, aberta_em) VALUES (?, ?, 'mesa', ?)",
                            (str(uuid.uuid4()), status, "2026-10-03 20:00:00"))

    def test_desligado_enquanto_servidor_e_chave_forem_placeholders(self):
        s = ServicoLicenca(self.banco)
        self.assertFalse(s.ativo)
        self.assertFalse(s.iniciar_verificacao())
        self.assertFalse(s.bloqueado)

    def test_permitido_sem_aviso_funciona_normal(self):
        s = self.servico()
        self.verificar(s)
        self.assertFalse(s.bloqueado)
        self.assertEqual(s.aviso, "")
        self.assertEqual(self.falso.chamadas, [(SERVER, CHAVE)])

    def test_aviso_de_atraso_nao_bloqueia(self):
        s = self.servico(Resultado(True, "atraso", pdv_licenca.AVISO_ATRASO))
        self.verificar(s)
        self.assertEqual(s.aviso, pdv_licenca.AVISO_ATRASO)
        self.assertFalse(s.bloqueado)
        self.assertFalse(s.bloqueio_pendente)

    def test_bloqueada_bloqueia_com_mensagem_pelo_motivo(self):
        for motivo, trecho in (("bloqueada", "bloqueada"), ("invalida", "não é válida"), ("outra_maquina", "outro computador"),
                               ("sem_token_valido", "internet")):
            with self.subTest(motivo=motivo):
                s = self.servico(Resultado(False, motivo))
                self.verificar(s)
                self.assertTrue(s.bloqueio_pendente)
                self.assertIn(trecho, s.mensagem_bloqueio())

    def test_bloqueio_nao_interrompe_venda_nem_comanda_em_andamento(self):
        for status in ("aberta", "conta_enviada"):
            with self.subTest(status=status):
                self.banco.executar("DELETE FROM vendas")
                self.abrir_venda(status)
                s = self.servico(Resultado(False, "bloqueada"))
                self.verificar(s)
                self.assertTrue(s.bloqueado)
                self.assertFalse(s.bloqueio_pendente)        # adiado: a venda segue
        self.banco.executar("UPDATE vendas SET status = 'fechada'")
        self.assertTrue(s.bloqueio_pendente)                 # a venda acabou: agora vale

    def test_caixa_aberto_na_tela_tambem_adia_o_bloqueio(self):
        estado = {"caixa": True}
        s = self.servico(Resultado(False, "bloqueada"), extra=lambda: estado["caixa"])
        self.verificar(s)
        self.assertFalse(s.bloqueio_pendente)
        estado["caixa"] = False
        self.assertTrue(s.bloqueio_pendente)

    def test_so_uma_consulta_por_vez_e_o_resultado_chega_pela_coleta(self):
        s = self.servico()
        self.assertTrue(s.iniciar_verificacao())
        self.assertFalse(s.iniciar_verificacao())
        self.assertIsNone(s.resultado)                       # ainda não coletado: a tela não vê nada pela metade
        for _ in range(200):
            if s.coletar():
                break
            time.sleep(0.01)
        self.assertTrue(s.resultado.permitido)

    def test_falha_inesperada_na_thread_vira_sem_validacao(self):
        s = self.servico()
        s._checar = lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))
        self.verificar(s)
        self.assertEqual(s.resultado.motivo, "sem_token_valido")

    def test_licenca_mascarada_mostra_so_os_4_ultimos(self):
        s = self.servico()
        self.assertTrue(s.chave_mascarada().endswith("5678"))
        self.assertNotIn("ABCD", s.chave_mascarada())
        self.assertEqual(mascarar(""), "—")
        self.assertEqual(s.contato_suporte(), servico_licenca.SUPORTE_PADRAO)
        self.banco.cfg_set("lic_suporte", "WhatsApp (11) 90000-0000")
        self.assertEqual(s.contato_suporte(), "WhatsApp (11) 90000-0000")

    def test_chave_fica_na_configuracao_e_nunca_no_texto_de_status(self):
        s = self.servico()
        self.verificar(s)
        self.assertEqual(self.banco.cfg("lic_chave"), CHAVE)
        self.assertNotIn(CHAVE, s.status_texto())


if __name__ == "__main__":
    unittest.main()
