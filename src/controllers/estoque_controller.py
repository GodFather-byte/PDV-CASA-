"""Lançamentos de estoque (manual ADM 5.2 e Evicommerce): compra, entrada, saída,
descarte, contagem/diferença, inicial, pedido (vira compra ao confirmar a entrega) e
descarte de produtos acabados. Também dá baixa/estorno de vendas.

Toda alteração de quantidade passa por `_mover`, que grava um registro em
movimentos_estoque. É esse histórico que permite estornar com exatidão.
"""
from __future__ import annotations

from src.controllers.produto_controller import ProdutoController
from src.core import formatacao as fmt
from src.core.erros import ErroNegocio

TIPOS = {
    "inicial": "Inicial", "pedido": "Pedido", "compra": "Compra", "entrada": "Entrada",
    "saida": "Saída", "descarte": "Descarte", "contagem": "Contagem (diferença)",
    "desc_acabados": "Descarte de produtos acabados",
}


class EstoqueController:
    def __init__(self, banco, operador_id: int | None = None):
        self.banco = banco
        self.produtos = ProdutoController(banco)
        self.operador_id = operador_id

    # ---------------------------------------------------------- primitivas
    def _mover(self, produto_id: int, delta: float, tipo: str, ref_tipo: str | None = None,
               ref_id: int | None = None) -> float:
        agora = fmt.agora()
        self.banco.executar(
            "UPDATE produtos SET qt_atual = ROUND(qt_atual + ?, 4), ult_atualizacao = ? WHERE id = ?",
            (delta, agora, produto_id))
        apos = self.banco.valor("SELECT qt_atual FROM produtos WHERE id = ?", (produto_id,))
        self.banco.inserir("movimentos_estoque", {
            "produto_id": produto_id, "tipo": tipo, "quantidade": fmt.arred_qtd(delta),
            "qt_apos": apos, "ref_tipo": ref_tipo, "ref_id": ref_id, "criado_em": agora})
        return apos

    def _estornar_referencia(self, ref_tipo: str, ref_id: int, tipo_original: str | None, tipo_estorno: str) -> None:
        sql = "SELECT produto_id, quantidade FROM movimentos_estoque WHERE ref_tipo = ? AND ref_id = ?"
        params = [ref_tipo, ref_id]
        if tipo_original:
            sql += " AND tipo = ?"
            params.append(tipo_original)
        for m in self.banco.todos(sql, params):
            self._mover(m["produto_id"], -m["quantidade"], tipo_estorno, ref_tipo, ref_id)

    # ----------------------------------------------------------- vendas
    def baixar_venda(self, venda_id: int) -> None:
        """Dá baixa nos produtos (e insumos da composição) dos itens não cancelados.

        Idempotente: se a venda já tem movimentos de baixa, repetir a chamada não faz nada."""
        if self.banco.um("SELECT 1 FROM movimentos_estoque WHERE ref_tipo = 'venda' AND ref_id = ? "
                         "AND tipo = 'venda' LIMIT 1", (venda_id,)):
            return
        for it in self.banco.todos(
                "SELECT id, produto_id, quantidade FROM itens_venda WHERE venda_id = ? AND cancelado = 0", (venda_id,)):
            partes = self.banco.todos("SELECT produto_id, fracao FROM itens_venda_partes WHERE item_id = ?", (it["id"],))
            alvos = [(p["produto_id"], it["quantidade"] * p["fracao"]) for p in partes] or [(it["produto_id"], it["quantidade"])]
            for pid, qtd in alvos:
                for consumo_id, q in self.produtos.consumos(pid, qtd):
                    self._mover(consumo_id, -q, "venda", "venda", venda_id)

    def estornar_venda(self, venda_id: int) -> None:
        """Desfaz a baixa da venda. Idempotente: um segundo estorno não faz nada."""
        if self.banco.um("SELECT 1 FROM movimentos_estoque WHERE ref_tipo = 'venda' AND ref_id = ? "
                         "AND tipo = 'estorno_venda' LIMIT 1", (venda_id,)):
            return
        self._estornar_referencia("venda", venda_id, "venda", "estorno_venda")

    # ------------------------------------------------------- lançamentos
    def criar_lancamento(self, tipo: str, data: str | None = None, descricao: str | None = None,
                         documento: str | None = None, nota_fiscal: str | None = None,
                         fornecedor_id: int | None = None, valor_cent: int = 0) -> int:
        if tipo not in TIPOS:
            raise ErroNegocio(f"Tipo de movimento inválido: {tipo}")
        if tipo in ("compra", "pedido") and not fornecedor_id:
            raise ErroNegocio("Informe o fornecedor (cadastre em Manutenção de Cadastros > Fornecedores).")
        return self.banco.inserir("lancamentos_estoque", {
            "tipo": tipo, "data": fmt.para_data_iso(data) or fmt.hoje(),
            "descricao": descricao or TIPOS[tipo], "documento": documento, "nota_fiscal": nota_fiscal,
            "fornecedor_id": fornecedor_id, "valor_cent": valor_cent,
            "operador_id": self.operador_id, "criado_em": fmt.agora()})

    def lancamento(self, lanc_id: int) -> dict:
        r = self.banco.um(
            """SELECT l.*, f.nome AS fornecedor FROM lancamentos_estoque l
               LEFT JOIN fornecedores f ON f.id = l.fornecedor_id WHERE l.id = ?""", (lanc_id,))
        if r is None:
            raise ErroNegocio("Lançamento de estoque não encontrado.")
        return dict(r)

    def lancamentos(self, tipo: str | None = None, de: str | None = None, ate: str | None = None) -> list[dict]:
        onde, params = [], []
        if tipo:
            onde.append("l.tipo = ?"); params.append(tipo)
        if de:
            onde.append("l.data >= ?"); params.append(de)
        if ate:
            onde.append("l.data <= ?"); params.append(ate)
        sql = ("SELECT l.*, f.nome AS fornecedor, (SELECT COALESCE(SUM(valor_cent),0) FROM itens_estoque "
               "WHERE lancamento_id = l.id) AS total_itens FROM lancamentos_estoque l "
               "LEFT JOIN fornecedores f ON f.id = l.fornecedor_id")
        if onde:
            sql += " WHERE " + " AND ".join(onde)
        return [dict(r) for r in self.banco.todos(sql + " ORDER BY l.data DESC, l.id DESC", params)]

    def itens(self, lanc_id: int) -> list[dict]:
        return [dict(r) for r in self.banco.todos(
            """SELECT i.*, p.codigo, p.nome, u.abreviatura AS unidade FROM itens_estoque i
               JOIN produtos p ON p.id = i.produto_id JOIN unidades u ON u.id = p.unidade_id
               WHERE i.lancamento_id = ? ORDER BY i.id""", (lanc_id,))]

    def total_itens(self, lanc_id: int) -> int:
        return self.banco.valor("SELECT SUM(valor_cent) FROM itens_estoque WHERE lancamento_id = ?", (lanc_id,), 0)

    # ----------------------------------------------------------- itens
    def adicionar_item(self, lanc_id: int, produto_id: int, quantidade: float, valor_cent: int = 0,
                       desconto_cent: int = 0, estoque_minimo: float | None = None) -> int:
        """Lança um item e já atualiza o estoque (como o sistema original).

        `valor_cent` é o total do item na nota (não o unitário)."""
        lanc = self.lancamento(lanc_id)
        tipo = lanc["tipo"]
        p = self.produtos.por_id(produto_id)
        if p is None:
            raise ErroNegocio("Produto não encontrado.")
        quantidade = fmt.arred_qtd(quantidade)
        if quantidade < 0 or (quantidade == 0 and tipo not in ("inicial", "contagem")):
            raise ErroNegocio("Informe uma quantidade maior que zero.")
        if tipo == "desc_acabados" and not self.produtos.composicao(produto_id):
            raise ErroNegocio(f"'{p['nome']}' não tem composição (ficha técnica) cadastrada.")
        if tipo not in ("inicial", "desc_acabados") and not p["controla_estoque"]:
            raise ErroNegocio(f"'{p['nome']}' não controla estoque. Marque 'Controla estoque' no cadastro do produto.")
        if tipo in ("inicial", "contagem") and self.banco.um(
                "SELECT 1 FROM itens_estoque WHERE lancamento_id = ? AND produto_id = ?", (lanc_id, produto_id)):
            raise ErroNegocio(f"'{p['nome']}' já foi lançado neste movimento. Exclua o item para lançá-lo de novo.")

        with self.banco.transacao():
            item_id = self.banco.inserir("itens_estoque", {
                "lancamento_id": lanc_id, "produto_id": produto_id, "quantidade": quantidade,
                "preco_unit_cent": fmt.dividir_cent(max(valor_cent - desconto_cent, 0), quantidade),
                "desconto_cent": desconto_cent, "valor_cent": valor_cent,
                "qt_anterior": p["qt_atual"], "diferenca": 0, "aplicado": 0})
            if tipo != "pedido":
                self._aplicar_item(item_id, tipo, p, quantidade, valor_cent, desconto_cent)
            if estoque_minimo is not None:
                self.banco.executar("UPDATE produtos SET estoque_minimo = ? WHERE id = ?",
                                    (fmt.arred_qtd(estoque_minimo), produto_id))
            self._atualizar_total(lanc_id)
        return item_id

    def _aplicar_item(self, item_id: int, tipo: str, p: dict, qtd: float, valor_cent: int, desconto_cent: int) -> None:
        pid = p["id"]
        antes = p["qt_atual"]
        if tipo == "inicial":
            self.banco.executar("UPDATE produtos SET controla_estoque = 1, qt_inicial = ? WHERE id = ?", (qtd, pid))
            self._mover(pid, qtd - antes, "inicial", "item_estoque", item_id)
        elif tipo == "compra":
            self._mover(pid, qtd, "compra", "item_estoque", item_id)
            unit = fmt.dividir_cent(max(valor_cent - desconto_cent, 0), qtd)
            self.banco.executar("UPDATE produtos SET ult_preco_cent = ? WHERE id = ?", (unit, pid))
        elif tipo == "entrada":
            self._mover(pid, qtd, "entrada", "item_estoque", item_id)
        elif tipo in ("saida", "descarte"):
            self._mover(pid, -qtd, tipo, "item_estoque", item_id)
        elif tipo == "contagem":
            self._mover(pid, qtd - antes, "contagem", "item_estoque", item_id)
        elif tipo == "desc_acabados":
            for consumo_id, q in self.produtos.consumos(pid, qtd):
                self._mover(consumo_id, -q, "desc_acabados", "item_estoque", item_id)
        depois = self.banco.valor("SELECT qt_atual FROM produtos WHERE id = ?", (pid,))
        self.banco.executar("UPDATE itens_estoque SET aplicado = 1, diferenca = ? WHERE id = ?",
                            (fmt.arred_qtd(depois - antes), item_id))

    def remover_item(self, item_id: int) -> None:
        """Exclui o item e desfaz o efeito dele no estoque."""
        item = self.banco.um("SELECT * FROM itens_estoque WHERE id = ?", (item_id,))
        if item is None:
            raise ErroNegocio("Item não encontrado.")
        with self.banco.transacao():
            if item["aplicado"]:
                self._estornar_referencia("item_estoque", item_id, None, "estorno")
            self.banco.executar("DELETE FROM itens_estoque WHERE id = ?", (item_id,))
            lanc = self.lancamento(item["lancamento_id"])
            if lanc["tipo"] == "compra":
                self._recalcular_ult_preco(item["produto_id"])
            self._atualizar_total(item["lancamento_id"])

    def excluir_lancamento(self, lanc_id: int) -> None:
        with self.banco.transacao():
            for it in self.banco.todos("SELECT id FROM itens_estoque WHERE lancamento_id = ?", (lanc_id,)):
                self.remover_item(it["id"])
            self.banco.executar("DELETE FROM contas WHERE lancamento_estoque_id = ? AND dt_quitacao IS NULL", (lanc_id,))
            self.banco.executar("DELETE FROM lancamentos_estoque WHERE id = ?", (lanc_id,))

    def _atualizar_total(self, lanc_id: int) -> None:
        total = self.total_itens(lanc_id)
        self.banco.executar("UPDATE lancamentos_estoque SET valor_cent = CASE WHEN tipo = 'compra' "
                            "THEN valor_cent ELSE ? END WHERE id = ?", (total, lanc_id))

    def _recalcular_ult_preco(self, produto_id: int) -> None:
        r = self.banco.um(
            """SELECT i.valor_cent, i.desconto_cent, i.quantidade FROM itens_estoque i
               JOIN lancamentos_estoque l ON l.id = i.lancamento_id
               WHERE i.produto_id = ? AND l.tipo = 'compra' AND i.quantidade > 0
               ORDER BY l.data DESC, i.id DESC LIMIT 1""", (produto_id,))
        unit = fmt.dividir_cent(max(r["valor_cent"] - r["desconto_cent"], 0), r["quantidade"]) if r else 0
        self.banco.executar("UPDATE produtos SET ult_preco_cent = ? WHERE id = ?", (unit, produto_id))

    def definir_minimo(self, produto_id: int, minimo: float) -> None:
        self.banco.executar("UPDATE produtos SET estoque_minimo = ? WHERE id = ?", (fmt.arred_qtd(minimo), produto_id))

    # ------------------------------------------------------------ pedido
    def confirmar_pedido(self, lanc_id: int, valores: dict | None = None) -> None:
        """Confirma a entrega de um pedido: ele vira COMPRA e passa a mexer no estoque.
        `valores` = {item_id: total_do_item_em_centavos} (o valor só é conhecido na entrega)."""
        lanc = self.lancamento(lanc_id)
        if lanc["tipo"] != "pedido":
            raise ErroNegocio("Somente pedidos podem ter a entrega confirmada.")
        itens = self.itens(lanc_id)
        if not itens:
            raise ErroNegocio("O pedido não tem itens.")
        with self.banco.transacao():
            for it in itens:
                total = (valores or {}).get(it["id"], it["valor_cent"])
                self.banco.executar(
                    "UPDATE itens_estoque SET valor_cent = ?, preco_unit_cent = ? WHERE id = ?",
                    (total, fmt.dividir_cent(total, it["quantidade"]), it["id"]))
            self.banco.executar("UPDATE lancamentos_estoque SET tipo = 'compra' WHERE id = ?", (lanc_id,))
            for it in self.itens(lanc_id):
                p = self.produtos.por_id(it["produto_id"])
                self.banco.executar("UPDATE itens_estoque SET qt_anterior = ? WHERE id = ?", (p["qt_atual"], it["id"]))
                self._aplicar_item(it["id"], "compra", p, it["quantidade"], it["valor_cent"], it["desconto_cent"])
            self.banco.executar("UPDATE lancamentos_estoque SET valor_cent = ? WHERE id = ?",
                                (self.total_itens(lanc_id), lanc_id))

    # ----------------------------------------------------- listas de apoio
    def itens_para_contagem(self) -> list[dict]:
        """Base do formulário de contagem física."""
        return [dict(r) for r in self.banco.todos(
            """SELECT p.id, p.codigo, p.nome, p.qt_atual, u.abreviatura AS unidade FROM produtos p
               JOIN unidades u ON u.id = p.unidade_id
               WHERE p.controla_estoque = 1 AND p.ativo = 1 ORDER BY p.nome""")]
