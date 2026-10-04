"""Lado PDV da sincronização com a nuvem (contrato em docs/COORDENACAO.md).

Este módulo só monta o lote e registra a confirmação. O HTTP fica em src/sync/sincronizador.py.
"""
from __future__ import annotations

from src.core import formatacao as fmt


class SyncController:
    def __init__(self, banco):
        self.banco = banco

    def contagem_pendentes(self) -> int:
        return self.banco.valor(
            "SELECT COUNT(*) FROM vendas WHERE sincronizado = 0 AND cupom IS NOT NULL "
            "AND status IN ('fechada','cancelada')", (), 0)

    def montar_lote(self, limite: int = 50) -> dict:
        vendas = self.banco.todos(
            """SELECT v.*, o.nome AS operador_nome, t.numero AS turno_numero FROM vendas v
               LEFT JOIN operadores o ON o.id = v.operador_id LEFT JOIN turnos t ON t.id = v.turno_id
               WHERE v.sincronizado = 0 AND v.cupom IS NOT NULL AND v.status IN ('fechada','cancelada')
               ORDER BY v.id LIMIT ?""", (limite,))
        return {
            "chave_loja": self.banco.cfg("chave_loja"),
            "terminal": self.banco.cfg_int("terminal", 1),
            "enviado_em": fmt.agora(),
            "vendas": [self._venda(v) for v in vendas],
        }

    def _venda(self, v) -> dict:
        itens = self.banco.todos(
            """SELECT p.codigo, p.nome, i.quantidade, i.preco_unit_cent, i.total_cent, i.cancelado
               FROM itens_venda i JOIN produtos p ON p.id = i.produto_id WHERE i.venda_id = ? ORDER BY i.id""", (v["id"],))
        pagamentos = self.banco.todos(
            """SELECT t.tipo, p.valor_cent, p.troco_cent FROM pagamentos_venda p
               JOIN tipos_pagamento t ON t.id = p.tipo_pagamento_id WHERE p.venda_id = ? ORDER BY p.id""", (v["id"],))
        return {
            "uuid": v["uuid"], "cupom": v["cupom"], "turno": v["turno_numero"], "terminal": v["terminal"],
            "modalidade": v["modalidade"], "posicao": v["posicao"], "comanda": bool(v["comanda"]), "status": v["status"],
            "aberta_em": v["aberta_em"], "fechada_em": v["fechada_em"], "operador": v["operador_nome"],
            "subtotal_cent": v["subtotal_cent"], "desconto_cent": v["desconto_cent"],
            "servico_cent": v["servico_cent"], "taxa_cent": v["taxa_cent"], "total_cent": v["total_cent"],
            "troco_cent": v["troco_cent"], "vale_cent": v["vale_cent"], "pessoas": v["pessoas"],
            "itens": [{"codigo": i["codigo"], "nome": i["nome"], "quantidade": i["quantidade"],
                       "preco_unit_cent": i["preco_unit_cent"], "total_cent": i["total_cent"],
                       "cancelado": bool(i["cancelado"])} for i in itens],
            "pagamentos": [{"tipo": p["tipo"], "valor_cent": p["valor_cent"], "troco_cent": p["troco_cent"]}
                           for p in pagamentos],
        }

    def confirmar(self, uuids: list[str], enviados: dict[str, str] | None = None) -> int:
        """Marca como sincronizadas SOMENTE as vendas que o servidor confirmou.

        `enviados` ({uuid: status que foi no lote}) protege da corrida em que a venda é cancelada
        enquanto o lote está a caminho: se o status mudou depois do envio, a venda continua pendente
        e o cancelamento segue no próximo lote (sem isso o aceite do lote antigo o apagaria)."""
        n = 0
        with self.banco.transacao():
            for u in uuids:
                if enviados is None:
                    n += self.banco.executar("UPDATE vendas SET sincronizado = 1 WHERE uuid = ?", (u,)).rowcount
                elif u in enviados:
                    n += self.banco.executar(
                        "UPDATE vendas SET sincronizado = 1 WHERE uuid = ? AND status = ?", (u, enviados[u])).rowcount
        return n

    def contagem_rejeitadas(self) -> int:
        return self.banco.valor("SELECT COUNT(*) FROM vendas WHERE sincronizado = 2", (), 0)

    def rejeitar(self, uuids: list[str], motivo: str = "") -> int:
        """Quarentena (sincronizado = 2): a nuvem recusou a venda por dado inválido (HTTP 422). Ela sai da
        fila, para uma venda ruim não travar todas as outras, mas continua guardada e visível no painel."""
        n = 0
        with self.banco.transacao():
            for u in uuids:
                n += self.banco.executar("UPDATE vendas SET sincronizado = 2 WHERE uuid = ? AND sincronizado = 0", (u,)).rowcount
            if n:
                self.banco.log("sync_rejeitada", f"{n} venda(s) recusada(s) pela nuvem: {motivo}"[:500])
        return n

    def reenviar_rejeitadas(self) -> int:
        """Devolve as vendas em quarentena para a fila (depois de corrigir a causa)."""
        return self.banco.executar("UPDATE vendas SET sincronizado = 0 WHERE sincronizado = 2").rowcount
