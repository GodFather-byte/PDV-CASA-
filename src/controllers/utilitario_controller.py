"""Utilitários (manual ADM seção 7): backup, limpeza do movimento e programa de comunicação."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from src.core import formatacao as fmt
from src.core.erros import ErroNegocio
from src.database.conexao import RAIZ


class UtilitarioController:
    def __init__(self, banco, operador_id: int | None = None):
        self.banco = banco
        self.operador_id = operador_id

    # --------------------------------------------------------------- backup
    def pasta_backup(self) -> Path:
        escolhida = self.banco.cfg("pasta_backup").strip()
        return Path(escolhida) if escolhida else RAIZ / "Backup"

    def backup(self, manter: int = 30) -> str:
        """Cópia consistente do banco com data e hora no nome. Mantém os `manter` mais novos."""
        pasta = self.pasta_backup()
        pasta.mkdir(parents=True, exist_ok=True)
        nome = f"loja_offline-{fmt.agora().replace(':', '').replace(' ', '-')}.db"
        destino = pasta / nome
        self.banco.copiar_para(str(destino))
        self.banco.cfg_set("ultimo_backup", fmt.agora())
        self.banco.log("backup", str(destino), self.operador_id)
        antigos = sorted(pasta.glob("loja_offline-*.db"), key=lambda p: p.name, reverse=True)[manter:]
        for p in antigos:
            try:
                p.unlink()
            except OSError:
                pass
        return str(destino)

    def ultimo_backup(self) -> str | None:
        return self.banco.cfg("ultimo_backup") or None

    # -------------------------------------------------------------- limpeza
    def limpar_movimento(self, antes_de: str) -> dict:
        """Apaga vendas e movimentos ANTERIORES à data (o período apagado termina no dia anterior).

        Salvaguardas: faz backup antes; não apaga o dia de hoje em diante; e, se a sincronização com a
        nuvem estiver configurada, recusa apagar vendas que ainda não foram enviadas."""
        data = fmt.para_data_iso(antes_de)
        if not data:
            raise ErroNegocio("Informe a data limite (dd/mm/aaaa).")
        if data > fmt.hoje():
            raise ErroNegocio("A data limite não pode ser futura.")
        if data == fmt.hoje():
            raise ErroNegocio("A limpeza apaga até o dia anterior à data informada; use no máximo a data de hoje "
                              "menos 1 dia para preservar o movimento atual.")
        alvo = ("status IN ('fechada','cancelada') AND date(COALESCE(fechada_em, aberta_em)) < ?")
        if self.banco.cfg("api_url").strip():
            pendentes = self.banco.valor(f"SELECT COUNT(*) FROM vendas WHERE sincronizado = 0 AND {alvo}", (data,), 0)
            if pendentes:
                raise ErroNegocio(f"Existem {pendentes} venda(s) do período ainda não enviadas à nuvem. "
                                  "Sincronize antes de limpar.")
            recusadas = self.banco.valor(f"SELECT COUNT(*) FROM vendas WHERE sincronizado = 2 AND {alvo}", (data,), 0)
            if recusadas:
                raise ErroNegocio(f"Existem {recusadas} venda(s) do período recusadas pela nuvem (em quarentena). Corrija a "
                                  "causa (veja logs/sync.log) e rode 'python -m src.app --sync --reenviar' antes de limpar.")
        copia = self.backup()
        with self.banco.transacao():
            ids = [r[0] for r in self.banco.todos(f"SELECT id FROM vendas WHERE {alvo}", (data,))]
            for i in range(0, len(ids), 500):
                lote = ids[i:i + 500]
                marcas = ",".join("?" * len(lote))
                self.banco.executar(f"UPDATE caderneta SET venda_id = NULL WHERE venda_id IN ({marcas})", lote)
                self.banco.executar(f"UPDATE repiques SET venda_id = NULL WHERE venda_id IN ({marcas})", lote)
                self.banco.executar(f"DELETE FROM vendas WHERE id IN ({marcas})", lote)
            turnos = [r[0] for r in self.banco.todos(
                """SELECT t.id FROM turnos t WHERE t.status = 'fechado' AND date(t.aberto_em) < ?
                   AND NOT EXISTS (SELECT 1 FROM vendas v WHERE v.turno_id = t.id)""", (data,))]
            comissoes = 0
            for t in turnos:
                # Comissões das garotas: a paga aponta para a sangria que vai ser apagada; as pagas e canceladas saem com o
                # turno, mas a PENDENTE é dinheiro devido e fica (só perde o turno).
                self.banco.executar("UPDATE comissoes_garotas SET movimento_id = NULL WHERE movimento_id IN "
                                    "(SELECT id FROM movimentos_caixa WHERE turno_id = ?)", (t,))
                self.banco.executar("UPDATE comissoes_garotas SET turno_id = NULL WHERE turno_id = ? AND status = 'pendente'", (t,))
                comissoes += self.banco.executar(
                    "DELETE FROM comissoes_garotas WHERE turno_id = ? AND status <> 'pendente'", (t,)).rowcount
                self.banco.executar("DELETE FROM movimentos_caixa WHERE turno_id = ?", (t,))
                self.banco.executar("DELETE FROM repiques WHERE turno_id = ?", (t,))
                self.banco.executar("DELETE FROM turnos WHERE id = ?", (t,))
            movs = self.banco.executar("DELETE FROM movimentos_estoque WHERE date(criado_em) < ?", (data,)).rowcount
            logs = self.banco.executar("DELETE FROM log_eventos WHERE date(quando) < ?", (data,)).rowcount
            self.banco.log("limpeza_movimento", f"até {data}: {len(ids)} vendas, {len(turnos)} turnos", self.operador_id)
        return {"vendas": len(ids), "turnos": len(turnos), "movimentos_estoque": movs, "logs": logs, "comissoes": comissoes,
                "backup": copia}

    # ------------------------------------------------------ comunicação
    def abrir_programa_comunicacao(self) -> None:
        """Abre o programa configurado (ex.: TeamViewer). Sem configuração, abre a Calculadora do Windows."""
        caminho = self.banco.cfg("programa_comunicacao").strip()
        try:
            if caminho:
                if not os.path.exists(caminho):
                    raise ErroNegocio(f"Programa não encontrado: {caminho}")
                subprocess.Popen([caminho])
            elif os.name == "nt":
                subprocess.Popen(["calc.exe"])
            else:
                raise ErroNegocio("Configure o programa de comunicação em Configurações > Configurações.")
        except OSError as e:
            raise ErroNegocio(f"Não foi possível abrir o programa: {e}") from e
