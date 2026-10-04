"""Cliente de sincronização PDV -> nuvem (contrato em docs/COORDENACAO.md).

Roda separado da interface (`python -m src.sync.sincronizador`, ou `WillPDV.exe --sync` no
executável). Lê o endereço, o token e a chave da loja de Configurações > Nuvem a cada rodada, só confirma
as vendas que o servidor aceitou e põe em quarentena a venda que a nuvem recusar por dado inválido
(para ela não travar as demais).
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
import time

from src.controllers.sync_controller import SyncController
from src.database.conexao import RAIZ, BancoDados

log = logging.getLogger("pdv.sync")

LIMITE_LOTE = 50
INTERVALO_MINIMO = 5
ESPERA_MAXIMA = 600


def proxima_espera(base: int, falhas: int) -> int:
    """Segundos até a próxima rodada: o intervalo configurado, dobrando a cada falha seguida (até 10 min)."""
    return min(max(base, INTERVALO_MINIMO) * 2 ** min(falhas, 6), ESPERA_MAXIMA)


class Sincronizador:
    def __init__(self, banco=None, http=None):
        self.banco = banco or BancoDados()
        self.sync = SyncController(self.banco)
        self._http = http          # qualquer objeto com .post(url, json=, headers=, timeout=) (nos testes, um falso)

    def _cliente(self):
        if self._http is None:
            try:
                import requests
            except ImportError:
                raise RuntimeError("Instale a biblioteca 'requests' (pip install requests) para sincronizar.") from None
            self._http = requests
        return self._http

    def configuracao(self) -> dict:
        b = self.banco
        return {"url": b.cfg("api_url").strip(), "token": b.cfg("api_token").strip(),
                "loja": b.cfg("chave_loja").strip(), "intervalo": b.cfg_int("sync_intervalo_seg", 60)}

    # ------------------------------------------------------------ uma rodada
    def enviar_pendentes(self) -> dict:
        """Envia um lote. Devolve {'estado': desligada|sem_pendentes|ok|rejeitadas|erro, ...}."""
        cfg = self.configuracao()
        if not cfg["url"]:
            return {"estado": "desligada", "mensagem": "Sincronização desligada: informe o endereço da API em Configurações > Nuvem."}
        if not cfg["loja"] or not cfg["token"]:
            return self._erro("Informe a chave da loja e o token da API em Configurações > Nuvem.")
        if self.sync.contagem_pendentes() == 0:
            return {"estado": "sem_pendentes"}
        lote = self.sync.montar_lote(LIMITE_LOTE)
        enviados = {v["uuid"]: v["status"] for v in lote["vendas"]}
        try:
            resposta = self._cliente().post(cfg["url"], json=lote, headers={"Authorization": f"Bearer {cfg['token']}"},
                                            timeout=(3, 15))
        except OSError as e:       # requests.RequestException herda de IOError
            return self._erro(f"Sem conexão com a nuvem: {e}")
        return self._tratar(resposta, lote, enviados)

    def _erro(self, mensagem: str) -> dict:
        return {"estado": "erro", "mensagem": mensagem}

    def _tratar(self, resposta, lote: dict, enviados: dict) -> dict:
        codigo = resposta.status_code
        if codigo == 200:
            try:
                aceitas = resposta.json().get("aceitas")
            except (ValueError, AttributeError):
                aceitas = None
            if not isinstance(aceitas, list):
                return self._erro("Resposta da nuvem ilegível.")
            n = self.sync.confirmar([u for u in aceitas if isinstance(u, str)], enviados)
            return {"estado": "ok", "enviadas": n, "enviados": len(enviados), "restantes": self.sync.contagem_pendentes()}
        if codigo in (401, 403):
            try:
                motivo = str(resposta.json().get("detail") or "")[:200]
            except (ValueError, AttributeError):
                motivo = ""
            return self._erro("A nuvem recusou o token da API" + (f" ({motivo})" if motivo else "")
                              + ". Confira o token e a chave da loja em Configurações > Nuvem.")
        if codigo == 422:
            return self._quarentena(resposta, lote)
        return self._erro(f"Erro da nuvem (HTTP {codigo}): {str(getattr(resposta, 'text', ''))[:200]}")

    def _quarentena(self, resposta, lote: dict) -> dict:
        """422: a nuvem aponta (em `detail[].loc`) quais vendas do lote são inválidas."""
        try:
            detalhes = [d for d in resposta.json().get("detail", []) if isinstance(d, dict)]
        except (ValueError, AttributeError):
            detalhes = []
        motivos: dict[int, list[str]] = {}
        for d in detalhes:
            loc = d.get("loc")
            if isinstance(loc, list) and len(loc) > 2 and loc[:2] == ["body", "vendas"] and isinstance(loc[2], int):
                motivos.setdefault(loc[2], []).append(f"{'.'.join(map(str, loc[3:]))}: {d.get('msg', '')}")
        vendas = lote["vendas"]
        indices = [i for i in sorted(motivos) if 0 <= i < len(vendas)]
        if not indices:
            return self._erro(f"A nuvem recusou o lote (HTTP 422) sem apontar a venda: {str(detalhes)[:200]}")
        if len(indices) >= len(vendas):
            # Todas as vendas do lote apontadas: é mais provável um contrato incompatível (servidor mais
            # estrito, versão errada) do que dado ruim. Não quarentena nada; espera e tenta de novo.
            return self._erro(f"A nuvem recusou TODAS as {len(vendas)} venda(s) do lote (HTTP 422): contrato incompatível? "
                              f"Ex.: {'; '.join(motivos[indices[0]])[:150]}")
        n = self.sync.rejeitar([vendas[i]["uuid"] for i in indices], "; ".join(motivos[indices[0]])[:200])
        log.error("Nuvem recusou %d venda(s) por dado inválido; em quarentena. Ex.: cupom %s: %s",
                  n, vendas[indices[0]].get("cupom"), "; ".join(motivos[indices[0]]))
        return {"estado": "rejeitadas", "rejeitadas": n, "restantes": self.sync.contagem_pendentes()}

    # ----------------------------------------------------------------- laço
    def iniciar_loop(self, rodadas: int | None = None, dormir=time.sleep) -> None:
        """Repete as rodadas; com falhas seguidas o intervalo dobra. `rodadas` limita o laço (testes)."""
        log.info("Sincronização iniciada.")
        falhas = feitas = 0
        while rodadas is None or feitas < rodadas:
            feitas += 1
            try:
                r = self.enviar_pendentes()
            except Exception:     # nunca deixa o laço morrer: registra e tenta de novo
                log.exception("Falha inesperada na sincronização.")
                r = self._erro("Falha inesperada (veja o log).")
            # 200 sem nenhuma confirmação (ex.: a nuvem recusa o uuid) não é progresso: espera como numa falha,
            # senão o laço reenviaria o mesmo lote sem parar.
            sem_progresso = r["estado"] == "ok" and r["enviados"] > 0 and r["enviadas"] == 0
            if r["estado"] == "erro" or sem_progresso:
                falhas += 1
                log.warning("%s (falhas seguidas: %d)",
                            r.get("mensagem") or "A nuvem não confirmou nenhuma venda do lote.", falhas)
            else:
                falhas = 0
                if r["estado"] == "ok" and r["enviadas"]:
                    log.info("%d venda(s) confirmada(s) pela nuvem; restam %d.", r["enviadas"], r["restantes"])
            tem_mais = r["estado"] in ("ok", "rejeitadas") and not sem_progresso and r.get("restantes", 0) > 0
            dormir(0 if tem_mais else proxima_espera(self.configuracao()["intervalo"], falhas))


def configurar_log() -> None:
    pasta = RAIZ / "logs"
    pasta.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.handlers.RotatingFileHandler(
        pasta / "sync.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")]
    if sys.stderr is not None:          # no executável sem console não há stderr
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers, format="%(asctime)s %(levelname)s %(message)s")


def reenviar(banco) -> int:
    """Devolve à fila as vendas em quarentena (depois de corrigir a causa da recusa da nuvem)."""
    n = SyncController(banco).reenviar_rejeitadas()
    log.info("%d venda(s) recusada(s) pela nuvem devolvida(s) à fila de envio.", n)
    return n


def main(argv: list[str] | None = None) -> None:
    """Sem argumentos: laço de envio. Com --reenviar: só devolve a quarentena à fila e termina."""
    configurar_log()
    s = Sincronizador()
    if "--reenviar" in (sys.argv[1:] if argv is None else argv):
        print(f"{reenviar(s.banco)} venda(s) devolvida(s) à fila de envio.")
        return
    s.iniciar_loop()


if __name__ == "__main__":
    main()
