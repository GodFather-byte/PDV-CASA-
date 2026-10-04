"""Nuvem: contrato PDV <-> API (FastAPI) e cliente de sincronização."""
from __future__ import annotations

import atexit
import copy
import io
import logging
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from contextlib import redirect_stdout
from unittest import mock

from src.controllers.caixa_controller import CaixaController
from src.controllers.sync_controller import SyncController
from src.controllers.turno_controller import TurnoController
from src.controllers.utilitario_controller import UtilitarioController
from src.core.erros import ErroNegocio
from src.sync import sincronizador
from src.sync.sincronizador import Sincronizador, proxima_espera
from tests.base import BaseTeste

# O backend lê o banco e o token do ambiente quando é importado: aponta para uma pasta temporária.
_PASTA = tempfile.mkdtemp(prefix="pdv_nuvem_")
os.environ["PDV_NUVEM_DB_URL"] = "sqlite:///" + (Path(_PASTA) / "nuvem.db").as_posix()
os.environ["PDV_API_TOKEN"] = "token-de-teste"
try:
    from fastapi.testclient import TestClient
    from backend import lojas
    from backend import main as nuvem
except (ImportError, RuntimeError):      # o backend é opcional: sem fastapi/httpx só roda o cliente
    TestClient = nuvem = lojas = None

ADMIN = {"Authorization": "Bearer token-de-teste"}                  # PDV_API_TOKEN: só o painel de todas as lojas
TOKENS = {"LOJA-1": "token-da-loja-1", "LOJA-2": "token-da-loja-2"}


def cabecalho(loja="LOJA-1"):
    return {"Authorization": f"Bearer {TOKENS[loja]}"}


def preparar_lojas():
    """A nuvem de teste é compartilhada: garante as duas lojas, ativas e com os tokens conhecidos."""
    db = nuvem.SessionLocal()
    try:
        db.query(nuvem.Loja).delete()
        for chave, token in TOKENS.items():
            db.add(nuvem.Loja(chave_loja=chave, nome=chave, token_hash=nuvem.hash_token(token), ativa=True))
        db.commit()
    finally:
        db.close()


def _limpar():
    if nuvem is not None:
        nuvem.engine.dispose()
    shutil.rmtree(_PASTA, ignore_errors=True)


atexit.register(_limpar)


class BasePDV(BaseTeste):
    def setUp(self):
        super().setUp()
        registro = logging.getLogger("pdv")      # os erros provocados de propósito não poluem a saída
        nivel = registro.level
        registro.setLevel(logging.CRITICAL)
        self.addCleanup(registro.setLevel, nivel)
        self.op = self.operador_adm()
        TurnoController(self.banco).abrir(self.op, 1, 0)
        self.caixa = CaixaController(self.banco, self.op)
        self.produto = self.novo_produto("SKOL", 1000)
        self.banco.cfg_set("chave_loja", "LOJA-1")

    def vender(self, mesa=None, qtd=1):
        if mesa:
            v, _ = self.caixa.abrir_mesa(mesa)
        else:
            v = self.caixa.abrir_balcao()
        self.caixa.adicionar_item(v, self.produto, qtd)
        total = self.banco.valor("SELECT total_cent FROM vendas WHERE id = ?", (v,))
        self.caixa.adicionar_pagamento(v, self.tipo("Dinheiro"), total)
        self.caixa.fechar(v)
        return v

    def uuid_de(self, venda_id):
        return self.banco.valor("SELECT uuid FROM vendas WHERE id = ?", (venda_id,))

    def sincronizado(self, venda_id):
        return self.banco.valor("SELECT sincronizado FROM vendas WHERE id = ?", (venda_id,))


@unittest.skipIf(TestClient is None, "fastapi/httpx não instalados")
class TesteApi(BasePDV):
    H = cabecalho()

    def setUp(self):
        super().setUp()
        preparar_lojas()
        self.http = TestClient(nuvem.app)

    def post(self, lote, headers=None):
        return self.http.post("/v1/sincronizar", json=lote, headers=self.H if headers is None else headers)

    def na_nuvem(self, uuid):
        db = nuvem.SessionLocal()
        try:
            return (db.query(nuvem.Venda).filter_by(uuid=uuid).all(),
                    db.query(nuvem.VendaItem).filter_by(venda_uuid=uuid).count(),
                    db.query(nuvem.VendaPagamento).filter_by(venda_uuid=uuid).count())
        finally:
            db.close()

    def test_lote_real_do_pdv_e_aceito_e_confirmado(self):
        self.vender(), self.vender(mesa=7)
        sync = SyncController(self.banco)
        lote = sync.montar_lote()
        r = self.post(lote)
        self.assertEqual(r.status_code, 200, r.text)
        enviados = {v["uuid"]: v["status"] for v in lote["vendas"]}
        self.assertCountEqual(r.json()["aceitas"], enviados)
        self.assertEqual(sync.confirmar(r.json()["aceitas"], enviados), 2)
        self.assertEqual(sync.contagem_pendentes(), 0)
        vendas, itens, pagamentos = self.na_nuvem(lote["vendas"][1]["uuid"])
        self.assertEqual((vendas[0].posicao, vendas[0].total_cent, itens, pagamentos), (7, 1100, 1, 1))
        self.assertEqual((vendas[0].chave_loja, vendas[0].status), ("LOJA-1", "fechada"))

    def test_reenvio_do_mesmo_lote_nao_duplica(self):
        self.vender()
        lote = SyncController(self.banco).montar_lote()
        uuid = lote["vendas"][0]["uuid"]
        for _ in range(2):
            self.assertEqual(self.post(lote).json()["aceitas"], [uuid])
        vendas, itens, pagamentos = self.na_nuvem(uuid)
        self.assertEqual((len(vendas), itens, pagamentos), (1, 1, 1))

    def test_cancelamento_depois_do_envio_e_aplicado_na_nuvem(self):
        v = self.vender()
        sync = SyncController(self.banco)
        lote = sync.montar_lote()
        uuid = lote["vendas"][0]["uuid"]
        sync.confirmar(self.post(lote).json()["aceitas"], {uuid: "fechada"})
        self.caixa.cancelar_venda(v, "cliente desistiu")
        self.assertEqual(sync.contagem_pendentes(), 1)
        lote2 = sync.montar_lote()
        self.assertEqual(lote2["vendas"][0]["status"], "cancelada")
        self.assertEqual(self.post(lote2).json()["aceitas"], [uuid])
        self.assertEqual(self.na_nuvem(uuid)[0][0].status, "cancelada")

    def test_status_antigo_nao_desfaz_o_cancelamento(self):
        v = self.vender()
        self.caixa.cancelar_venda(v, "erro")
        lote = SyncController(self.banco).montar_lote()
        uuid = lote["vendas"][0]["uuid"]
        self.assertEqual(self.post(lote).json()["aceitas"], [uuid])
        antigo = copy.deepcopy(lote)
        antigo["vendas"][0]["status"] = "fechada"
        self.assertEqual(self.post(antigo).json()["aceitas"], [uuid])
        self.assertEqual(self.na_nuvem(uuid)[0][0].status, "cancelada")

    def test_token_obrigatorio_e_conferido_antes_do_corpo(self):
        lote = SyncController(self.banco).montar_lote()
        self.assertEqual(self.post(lote, headers={}).status_code, 401)
        self.assertEqual(self.post(lote, headers={"Authorization": "Bearer errado"}).status_code, 401)
        self.assertEqual(self.post(lote, headers={"Authorization": TOKENS["LOJA-1"]}).status_code, 401)   # sem "Bearer"
        self.assertEqual(self.http.post("/v1/sincronizar", json={"lixo": 1}).status_code, 401)   # sem token nem valida o corpo
        with mock.patch.dict(os.environ):
            os.environ.pop("PDV_API_TOKEN")
            self.assertEqual(self.post(lote).status_code, 200)              # a loja não depende do token do administrador
            db = nuvem.SessionLocal()
            db.query(nuvem.Loja).delete()
            db.commit()
            db.close()
            self.assertEqual(self.post(lote).status_code, 503)              # nem loja nem administrador: servidor sem configuração

    def test_token_de_uma_loja_nao_envia_vendas_de_outra(self):
        self.vender()
        lote = SyncController(self.banco).montar_lote()                      # chave_loja = LOJA-1
        r = self.post(lote, headers=cabecalho("LOJA-2"))
        self.assertEqual(r.status_code, 403)
        self.assertIn("LOJA-2", r.json()["detail"])
        self.assertEqual(self.na_nuvem(lote["vendas"][0]["uuid"])[0], [])

    def test_token_do_administrador_nao_envia_vendas(self):
        self.vender()
        lote = SyncController(self.banco).montar_lote()
        self.assertEqual(self.post(lote, headers=ADMIN).status_code, 403)

    def test_loja_desativada_e_recusada(self):
        self.vender()
        lote = SyncController(self.banco).montar_lote()
        db = nuvem.SessionLocal()
        lojas.definir_ativa(db, "LOJA-1", False)
        db.close()
        r = self.post(lote)
        self.assertEqual(r.status_code, 403)
        self.assertIn("desativada", r.json()["detail"])

    def test_payload_invalido_e_recusado(self):
        self.vender()
        lote = SyncController(self.banco).montar_lote()

        def com(**mudancas):
            c = copy.deepcopy(lote)
            c["vendas"][0].update(mudancas)
            return c
        invalidos = {
            "total negativo": com(total_cent=-1), "status invalido": com(status="qualquer-coisa"),
            "modalidade invalida": com(modalidade="drive-thru"), "data malformada": com(fechada_em="ontem"),
            "cupom zero": com(cupom=0),
        }
        for nome, corpo in invalidos.items():
            with self.subTest(nome):
                self.assertEqual(self.post(corpo).status_code, 422)
        sem_loja = copy.deepcopy(lote)
        sem_loja["chave_loja"] = ""
        self.assertEqual(self.post(sem_loja).status_code, 422)
        grande = copy.deepcopy(lote)
        grande["vendas"] = grande["vendas"] * 501
        self.assertEqual(self.post(grande).status_code, 422)

    def test_operador_e_posicao_nulos_sao_aceitos(self):
        self.vender()
        lote = SyncController(self.banco).montar_lote()
        lote["vendas"][0].update(operador=None, posicao=None, turno=None)
        self.assertEqual(self.post(lote).status_code, 200)

    def test_uuid_de_outra_loja_nao_e_confirmado(self):
        self.vender()
        lote = SyncController(self.banco).montar_lote()
        self.assertEqual(len(self.post(lote).json()["aceitas"]), 1)
        outra = copy.deepcopy(lote)
        outra["chave_loja"] = "LOJA-2"
        self.assertEqual(self.post(outra, headers=cabecalho("LOJA-2")).json()["aceitas"], [])

    def test_saude_nao_exige_token(self):
        self.assertEqual(self.http.get("/v1/saude").json(), {"status": "ok"})


@unittest.skipIf(TestClient is None, "fastapi/httpx não instalados")
class TestePainelDoDono(BasePDV):
    H = ADMIN

    def setUp(self):
        super().setUp()
        preparar_lojas()
        self.http = TestClient(nuvem.app)
        db = nuvem.SessionLocal()                       # a nuvem de teste é compartilhada: começa vazia
        for modelo in (nuvem.VendaPagamento, nuvem.VendaItem, nuvem.Venda):
            db.query(modelo).delete()
        db.commit()
        db.close()

    def enviar(self, lote):
        r = self.http.post("/v1/sincronizar", json=lote, headers=cabecalho(lote["chave_loja"]))
        self.assertEqual(r.status_code, 200, r.text)

    def resumo(self, headers=None, **params):
        return self.http.get("/v1/dashboard/resumo", params=params, headers=self.H if headers is None else headers)

    def test_dados_do_painel_exigem_o_token(self):
        self.vender()
        self.enviar(SyncController(self.banco).montar_lote())
        self.assertEqual(self.http.get("/v1/dashboard/resumo").status_code, 401)
        self.assertEqual(self.http.get("/v1/dashboard/resumo", headers={"Authorization": "Bearer errado"}).status_code, 401)
        with mock.patch.dict(os.environ):
            os.environ.pop("PDV_API_TOKEN")
            self.assertEqual(self.resumo().status_code, 401)                   # sem PDV_API_TOKEN não há administrador
            self.assertEqual(self.resumo(headers=cabecalho()).status_code, 200)
        self.assertEqual(self.resumo().status_code, 200)

    def test_pagina_do_painel_e_publica_mas_nao_traz_dados_nem_usa_innerhtml(self):
        self.vender()
        self.enviar(SyncController(self.banco).montar_lote())
        r = self.http.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("Authorization", r.text)                        # a página envia o token ao consultar
        self.assertNotIn("innerHTML", r.text)                         # nome de produto vem do PDV: nunca como HTML
        self.assertNotIn("R$ 11,00", r.text)

    def test_resumo_do_dia_conta_so_vendas_fechadas_com_itens(self):
        self.vender(), self.vender(mesa=3, qtd=2)
        cancelada = self.vender()
        self.caixa.cancelar_venda(cancelada, "erro")
        cliente = self.banco.inserir("clientes", {"numero_consulta": "9", "nome": "ANA"})
        recebimento = self.caixa.abrir_caderneta(cliente)               # recebimento de dívida: subtotal 0
        self.caixa.adicionar_pagamento(recebimento, self.tipo("Dinheiro"), 500)
        self.caixa.fechar(recebimento, excesso_como_credito=True)
        self.enviar(SyncController(self.banco).montar_lote())
        r = self.resumo().json()
        # 1 x 10,00 + 1 mesa com 2 x 10,00 e 10% de serviço = 10,00 + 22,00
        self.assertEqual((r["dia"], r["cupons"], r["receita_cent"]), ("2026-10-03", 2, 1000 + 2200))
        self.assertEqual(r["ticket_medio_cent"], 1600)
        self.assertIsInstance(r["ticket_medio_cent"], int)
        self.assertEqual(r["top_produtos"], [{"nome": "SKOL", "qtd": 3.0, "total_cent": 3000}])

    def test_ticket_medio_arredonda_para_centavos_inteiros(self):
        for _ in range(3):
            self.vender()
        self.vender(qtd=2)
        self.enviar(SyncController(self.banco).montar_lote())
        r = self.resumo().json()
        self.assertEqual((r["cupons"], r["receita_cent"], r["ticket_medio_cent"]), (4, 5000, 1250))

    def test_filtra_por_dia_e_por_loja_e_valida_a_data(self):
        self.vender()
        self._hora["t"] = datetime(2026, 10, 4, 1, 30, 0)
        self.vender(qtd=3)
        self.enviar(SyncController(self.banco).montar_lote())
        self.assertEqual(self.resumo().json()["dia"], "2026-10-04")           # padrão: dia da venda mais recente
        self.assertEqual(self.resumo(dia="2026-10-04").json()["receita_cent"], 3000)
        self.assertEqual(self.resumo(dia="2026-10-03").json()["receita_cent"], 1000)
        self.assertEqual(self.resumo(dia="2026-10-05").json()["cupons"], 0)
        self.assertEqual(self.resumo(dia="2026-10-03", chave_loja="OUTRA").json()["receita_cent"], 0)
        self.assertEqual(self.resumo(dia="2026-10-03", chave_loja="LOJA-1").json()["receita_cent"], 1000)
        for ruim in ("amanha", "2026-13-40", "2026-10-3"):
            self.assertEqual(self.resumo(dia=ruim).status_code, 422, ruim)

    def test_dia_padrao_do_painel_respeita_a_loja_pedida(self):
        sync = SyncController(self.banco)
        v1 = self.vender()                                                   # loja A, 03/10
        self.enviar(sync.montar_lote())
        sync.confirmar([self.uuid_de(v1)])
        self._hora["t"] = datetime(2026, 10, 5, 20, 0, 0)
        self.vender(qtd=2)                                                   # será enviada como loja B, 05/10
        lote_b = sync.montar_lote()
        lote_b["chave_loja"] = "LOJA-2"
        self.enviar(lote_b)
        a, b, todas = self.resumo(chave_loja="LOJA-1").json(), self.resumo(chave_loja="LOJA-2").json(), self.resumo().json()
        self.assertEqual((a["dia"], a["receita_cent"]), ("2026-10-03", 1000))     # não vaza a data da venda da loja B
        self.assertEqual((b["dia"], b["receita_cent"]), ("2026-10-05", 2000))
        self.assertEqual(todas["dia"], "2026-10-05")
        self.assertEqual(self.resumo(chave_loja="NAO-EXISTE").json()["cupons"], 0)

    def test_sem_nenhuma_venda_o_painel_responde_zerado(self):
        r = self.resumo().json()
        self.assertEqual((r["cupons"], r["receita_cent"], r["ticket_medio_cent"], r["top_produtos"]), (0, 0, 0, []))


class RespostaFalsa:
    def __init__(self, status=200, corpo=None, texto=""):
        self.status_code, self._corpo, self.text = status, corpo, texto

    def json(self):
        if self._corpo is None:
            raise ValueError("sem json")
        return self._corpo


class HttpFalso:
    def __init__(self, responder):
        self.responder, self.chamadas = responder, []

    def post(self, url, json=None, headers=None, timeout=None):
        self.chamadas.append({"url": url, "json": copy.deepcopy(json), "headers": headers, "timeout": timeout})
        return self.responder(json)


def aceitar_tudo(lote):
    return RespostaFalsa(200, {"aceitas": [v["uuid"] for v in lote["vendas"]]})


class TesteSincronizador(BasePDV):
    URL = "http://nuvem.local/v1/sincronizar"

    def setUp(self):
        super().setUp()
        self.banco.cfg_set("api_url", self.URL)
        self.banco.cfg_set("api_token", "segredo")

    def cliente(self, responder=aceitar_tudo):
        self.http = HttpFalso(responder)
        return Sincronizador(self.banco, http=self.http)

    def test_desligada_sem_endereco_e_pede_chave_e_token(self):
        self.vender()
        self.banco.cfg_set("api_url", "")
        s = self.cliente()
        self.assertEqual(s.enviar_pendentes()["estado"], "desligada")
        self.banco.cfg_set("api_url", self.URL)
        self.banco.cfg_set("api_token", "")
        self.assertEqual(s.enviar_pendentes()["estado"], "erro")
        self.assertEqual(self.http.chamadas, [])

    def test_usa_endereco_token_e_chave_configurados(self):
        v = self.vender()
        r = self.cliente().enviar_pendentes()
        self.assertEqual((r["estado"], r["enviadas"], r["restantes"]), ("ok", 1, 0))
        c = self.http.chamadas[0]
        self.assertEqual((c["url"], c["headers"]), (self.URL, {"Authorization": "Bearer segredo"}))
        self.assertEqual((c["json"]["chave_loja"], c["json"]["vendas"][0]["uuid"]), ("LOJA-1", self.uuid_de(v)))
        self.assertEqual(self.sincronizado(v), 1)
        self.assertEqual(self.cliente().enviar_pendentes()["estado"], "sem_pendentes")

    def test_confirma_so_o_que_a_nuvem_aceitou(self):
        v1, v2, v3 = self.vender(), self.vender(), self.vender()
        r = self.cliente(lambda lote: RespostaFalsa(200, {"aceitas": [self.uuid_de(v1), "uuid-desconhecido"]})).enviar_pendentes()
        self.assertEqual((r["enviadas"], r["restantes"]), (1, 2))
        self.assertEqual([self.sincronizado(v) for v in (v1, v2, v3)], [1, 0, 0])

    def test_cancelamento_durante_o_envio_continua_pendente_e_segue_no_proximo_lote(self):
        v = self.vender()

        def cancelar_no_meio(lote):
            self.caixa.cancelar_venda(v, "cancelada enquanto o lote estava a caminho")
            return aceitar_tudo(lote)
        r = self.cliente(cancelar_no_meio).enviar_pendentes()
        self.assertEqual((r["enviadas"], r["restantes"]), (0, 1))
        self.assertEqual((self.sincronizado(v), self.banco.valor("SELECT status FROM vendas WHERE id = ?", (v,))), (0, "cancelada"))
        r = self.cliente().enviar_pendentes()
        self.assertEqual(self.http.chamadas[0]["json"]["vendas"][0]["status"], "cancelada")
        self.assertEqual((r["enviadas"], self.sincronizado(v)), (1, 1))

    def test_token_recusado_nao_confirma_nem_poe_em_quarentena(self):
        v = self.vender()
        r = self.cliente(lambda lote: RespostaFalsa(401, {"detail": "Token invalido"})).enviar_pendentes()
        self.assertEqual(r["estado"], "erro")
        self.assertIn("token", r["mensagem"])
        self.assertEqual((self.sincronizado(v), SyncController(self.banco).contagem_rejeitadas()), (0, 0))

    def test_loja_errada_ou_desativada_mostra_o_motivo_da_nuvem(self):
        v = self.vender()
        r = self.cliente(lambda lote: RespostaFalsa(403, {"detail": "Loja desativada na nuvem."})).enviar_pendentes()
        self.assertEqual(r["estado"], "erro")
        self.assertIn("Loja desativada na nuvem.", r["mensagem"])
        self.assertEqual(self.sincronizado(v), 0)

    def test_422_poe_so_a_venda_invalida_em_quarentena(self):
        v1, v2, v3 = self.vender(), self.vender(), self.vender()
        detalhe = {"detail": [{"type": "string_type", "loc": ["body", "vendas", 1, "posicao"], "msg": "Input should be a valid string"}]}
        sync = SyncController(self.banco)
        r = self.cliente(lambda lote: RespostaFalsa(422, detalhe)).enviar_pendentes()
        self.assertEqual((r["estado"], r["rejeitadas"], r["restantes"]), ("rejeitadas", 1, 2))
        self.assertEqual([self.sincronizado(v) for v in (v1, v2, v3)], [0, 2, 0])
        self.assertEqual(self.banco.valor("SELECT COUNT(*) FROM log_eventos WHERE evento = 'sync_rejeitada'"), 1)
        r = self.cliente().enviar_pendentes()              # as outras seguem; a recusada fica de fora
        self.assertEqual((r["enviadas"], sync.contagem_pendentes(), sync.contagem_rejeitadas()), (2, 0, 1))
        self.assertEqual(sync.reenviar_rejeitadas(), 1)
        self.assertEqual((sync.contagem_pendentes(), sync.contagem_rejeitadas()), (1, 0))

    def test_422_sem_apontar_a_venda_nao_poe_nada_em_quarentena(self):
        v = self.vender()
        detalhe = {"detail": [{"loc": ["body", "chave_loja"], "msg": "String should have at least 1 character"}]}
        r = self.cliente(lambda lote: RespostaFalsa(422, detalhe)).enviar_pendentes()
        self.assertEqual(r["estado"], "erro")
        self.assertEqual(self.sincronizado(v), 0)

    def test_venda_em_quarentena_bloqueia_a_limpeza_do_movimento_com_mensagem_propria(self):
        self.vender()
        SyncController(self.banco).rejeitar([self.uuid_de(1)], "teste")
        self.avancar(days=2)
        with self.assertRaisesRegex(ErroNegocio, "recusadas pela nuvem.*--sync --reenviar"):
            UtilitarioController(self.banco).limpar_movimento("2026-10-04")
        self.assertEqual(SyncController(self.banco).reenviar_rejeitadas(), 1)
        with self.assertRaisesRegex(ErroNegocio, "ainda não enviadas"):          # agora é só uma pendente comum
            UtilitarioController(self.banco).limpar_movimento("2026-10-04")

    def test_422_em_todas_as_vendas_do_lote_nao_poe_ninguem_em_quarentena(self):
        v1, v2 = self.vender(), self.vender()
        detalhe = {"detail": [{"loc": ["body", "vendas", i, "modalidade"], "msg": "Input should be 'x'"} for i in (0, 1)]}
        sync = SyncController(self.banco)
        r = self.cliente(lambda lote: RespostaFalsa(422, detalhe)).enviar_pendentes()
        self.assertEqual(r["estado"], "erro")
        self.assertIn("TODAS", r["mensagem"])
        self.assertEqual(([self.sincronizado(v) for v in (v1, v2)], sync.contagem_rejeitadas()), ([0, 0], 0))
        esperas = []
        self.cliente(lambda lote: RespostaFalsa(422, detalhe)).iniciar_loop(rodadas=3, dormir=esperas.append)
        self.assertEqual(esperas, [120, 240, 480])                  # sem laço quente e sem esvaziar o backlog

    def test_lote_de_uma_venda_so_apontada_tambem_fica_pendente(self):
        v = self.vender()
        detalhe = {"detail": [{"loc": ["body", "vendas", 0, "posicao"], "msg": "x"}]}
        r = self.cliente(lambda lote: RespostaFalsa(422, detalhe)).enviar_pendentes()
        self.assertEqual(r["estado"], "erro")
        self.assertEqual(self.sincronizado(v), 0)

    def test_reenviar_devolve_a_quarentena_para_a_fila(self):
        self.vender(), self.vender()
        sync = SyncController(self.banco)
        sync.rejeitar([self.uuid_de(1), self.uuid_de(2)], "teste")
        self.assertEqual((sync.contagem_pendentes(), sync.contagem_rejeitadas()), (0, 2))
        self.assertEqual(sincronizador.reenviar(self.banco), 2)
        self.assertEqual((sync.contagem_pendentes(), sync.contagem_rejeitadas()), (2, 0))
        self.assertEqual(sincronizador.reenviar(self.banco), 0)

    def test_falhas_de_rede_e_respostas_quebradas_mantem_tudo_pendente(self):
        v = self.vender()

        def sem_rede(lote):
            raise ConnectionError("rede fora")
        for responder in (sem_rede, lambda l: RespostaFalsa(200, {"aceitas": "x"}), lambda l: RespostaFalsa(200),
                          lambda l: RespostaFalsa(500, None, "erro interno")):
            self.assertEqual(self.cliente(responder).enviar_pendentes()["estado"], "erro")
            self.assertEqual(self.sincronizado(v), 0)

    def test_laco_continua_sem_dormir_enquanto_ha_lotes_e_depois_espera_o_intervalo(self):
        for _ in range(3):
            self.vender()
        esperas = []
        with mock.patch.object(sincronizador, "LIMITE_LOTE", 2):
            self.cliente().iniciar_loop(rodadas=3, dormir=esperas.append)
        self.assertEqual(esperas, [0, 60, 60])          # 2 + 1 vendas, depois nada a enviar
        self.assertEqual(SyncController(self.banco).contagem_pendentes(), 0)

    def test_laco_sobrevive_a_excecao_e_aumenta_a_espera(self):
        self.vender()

        def quebrar(lote):
            raise RuntimeError("bug")
        esperas = []
        self.cliente(quebrar).iniciar_loop(rodadas=3, dormir=esperas.append)
        self.assertEqual(esperas, [120, 240, 480])

    def test_nuvem_que_responde_200_sem_confirmar_nada_nao_vira_laco_quente(self):
        v = self.vender()
        esperas = []
        r = self.cliente(lambda lote: RespostaFalsa(200, {"aceitas": []})).enviar_pendentes()
        self.assertEqual((r["estado"], r["enviadas"], r["restantes"]), ("ok", 0, 1))
        s = self.cliente(lambda lote: RespostaFalsa(200, {"aceitas": []}))
        s.iniciar_loop(rodadas=3, dormir=esperas.append)
        self.assertEqual(esperas, [120, 240, 480])                  # espera crescente, nunca 0
        self.assertEqual(self.sincronizado(v), 0)
        self.assertEqual(len(self.http.chamadas), 3)

    def test_cancelamento_durante_o_envio_reenvia_na_rodada_seguinte(self):
        v = self.vender()
        esperas, primeira = [], [True]

        def cancelar_so_na_primeira(lote):
            if primeira.pop() if primeira else False:
                self.caixa.cancelar_venda(v, "cancelada no meio do envio")
            return aceitar_tudo(lote)
        self.cliente(cancelar_so_na_primeira).iniciar_loop(rodadas=2, dormir=esperas.append)
        self.assertEqual(esperas[0], 120)                           # 1ª rodada sem confirmar nada: espera como numa falha
        self.assertEqual((self.sincronizado(v), self.banco.valor("SELECT status FROM vendas WHERE id = ?", (v,))), (1, "cancelada"))

    def test_espera_dobra_a_cada_falha_ate_o_limite(self):
        self.assertEqual([proxima_espera(60, n) for n in range(6)], [60, 120, 240, 480, 600, 600])
        self.assertEqual(proxima_espera(1, 0), 5)


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(TestClient is None, "fastapi/httpx não instalados")
class TesteSeparacaoDasLojas(BasePDV):
    """O token identifica a loja: cada uma só envia e só vê o que é dela."""

    def setUp(self):
        super().setUp()
        preparar_lojas()
        self.http = TestClient(nuvem.app)
        db = nuvem.SessionLocal()
        for modelo in (nuvem.VendaPagamento, nuvem.VendaItem, nuvem.Venda):
            db.query(modelo).delete()
        db.commit()
        db.close()
        sync = SyncController(self.banco)
        self.vender()                                                        # R$ 10,00 na LOJA-1
        lote_a = sync.montar_lote()
        self.assertEqual(self.http.post("/v1/sincronizar", json=lote_a, headers=cabecalho()).status_code, 200)
        sync.confirmar([v["uuid"] for v in lote_a["vendas"]])                # o próximo lote só leva a venda nova
        self.vender(qtd=3)                                                   # R$ 30,00 enviados como LOJA-2
        lote_b = sync.montar_lote()
        lote_b["chave_loja"] = "LOJA-2"
        self.assertEqual(self.http.post("/v1/sincronizar", json=lote_b, headers=cabecalho("LOJA-2")).status_code, 200)

    def resumo(self, headers, **params):
        return self.http.get("/v1/dashboard/resumo", params=params, headers=headers)

    def test_cada_loja_ve_so_o_proprio_painel(self):
        self.assertEqual(self.resumo(cabecalho("LOJA-1")).json()["receita_cent"], 1000)
        self.assertEqual(self.resumo(cabecalho("LOJA-2")).json()["receita_cent"], 3000)
        self.assertEqual(self.resumo(cabecalho("LOJA-1"), chave_loja="LOJA-1").status_code, 200)
        self.assertEqual(self.resumo(cabecalho("LOJA-1"), chave_loja="LOJA-2").status_code, 403)

    def test_administrador_ve_todas_ou_a_pedida(self):
        self.assertEqual(self.resumo(ADMIN).json()["receita_cent"], 4000)
        self.assertEqual(self.resumo(ADMIN, chave_loja="LOJA-2").json()["receita_cent"], 3000)


@unittest.skipIf(TestClient is None, "fastapi/httpx não instalados")
class TesteCadastroDeLojas(unittest.TestCase):
    def setUp(self):
        self.db = nuvem.SessionLocal()
        self.addCleanup(self.db.close)
        self.db.query(nuvem.Loja).filter(nuvem.Loja.chave_loja.like("CAD-%")).delete(synchronize_session=False)
        self.db.commit()
        self.http = TestClient(nuvem.app)

    def test_criar_mostra_o_token_uma_vez_e_guarda_so_o_hash(self):
        token = lojas.criar(self.db, "CAD-1", "Boate Teste")
        self.assertGreaterEqual(len(token), 40)
        loja = self.db.query(nuvem.Loja).filter_by(chave_loja="CAD-1").one()
        self.assertNotEqual(loja.token_hash, token)
        self.assertEqual(loja.token_hash, nuvem.hash_token(token))
        r = self.http.get("/v1/dashboard/resumo", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 200)

    def test_novo_token_invalida_o_antigo(self):
        antigo = lojas.criar(self.db, "CAD-2", "Boate Teste")
        novo = lojas.novo_token(self.db, "CAD-2")
        self.assertNotEqual(antigo, novo)
        self.assertEqual(self.http.get("/v1/dashboard/resumo", headers={"Authorization": f"Bearer {antigo}"}).status_code, 401)
        self.assertEqual(self.http.get("/v1/dashboard/resumo", headers={"Authorization": f"Bearer {novo}"}).status_code, 200)

    def test_validacoes(self):
        lojas.criar(self.db, "CAD-3", "Boate Teste")
        for chave, nome in (("CAD-3", "Repetida"), ("", "Sem chave"), ("CAD 4", "Com espaço"), ("CAD-5", "")):
            with self.subTest(chave=chave), self.assertRaises(lojas.ErroLoja):
                lojas.criar(self.db, chave, nome)
        with self.assertRaises(lojas.ErroLoja):
            lojas.novo_token(self.db, "CAD-NAO-EXISTE")

    def test_linha_de_comando(self):
        saida = io.StringIO()
        with mock.patch.object(lojas, "SessionLocal", return_value=self.db), mock.patch.object(self.db, "close"), \
                redirect_stdout(saida):
            self.assertEqual(lojas.main(["criar", "CAD-6", "Boate Linha"]), 0)
            self.assertEqual(lojas.main(["desativar", "CAD-6"]), 0)
            self.assertEqual(lojas.main(["listar"]), 0)
            self.assertEqual(lojas.main(["comando-errado"]), 2)
        self.assertIn("Token (guarde agora", saida.getvalue())
        self.assertRegex(saida.getvalue(), r"CAD-6\s+INATIVA\s+Boate Linha")

