"""Vendas do caixa (manual do Caixa): balcão, mesas, itens, desconto, serviço,
pagamentos, troco/vale, fechamento e cancelamento.

Regras principais:
  * Toda venda pertence a um turno aberto e recebe o nº do cupom ao fechar/cancelar.
  * O estoque só é baixado quando a venda é FECHADA (e estornado se o cupom for cancelado).
  * Desconto incide só sobre os produtos; o serviço (só em mesa) não sofre desconto.
  * Troco sai das formas que permitem troco; excedente em forma que 'emite vale' vira contra-vale.
"""
from __future__ import annotations

from uuid import uuid4

from src.controllers.estoque_controller import EstoqueController
from src.controllers.produto_controller import ProdutoController
from src.controllers.turno_controller import TurnoController
from src.core import formatacao as fmt
from src.core.erros import ErroNegocio

ABERTAS = ("aberta", "conta_enviada")


class CaixaController:
    def __init__(self, banco, operador_id: int | None = None):
        self.banco = banco
        self.operador_id = operador_id
        self.turnos = TurnoController(banco)
        self.estoque = EstoqueController(banco, operador_id)
        self.produtos = ProdutoController(banco)

    # ============================================================ consulta
    def obter(self, venda_id: int) -> dict:
        r = self.banco.um("SELECT * FROM vendas WHERE id = ?", (venda_id,))
        if r is None:
            raise ErroNegocio("Venda não encontrada.")
        return dict(r)

    def itens(self, venda_id: int, cancelados: bool = False) -> list[dict]:
        sql = """SELECT i.*, p.codigo, p.nome, u.abreviatura AS unidade
                 FROM itens_venda i JOIN produtos p ON p.id = i.produto_id
                 JOIN unidades u ON u.id = p.unidade_id WHERE i.venda_id = ?"""
        if not cancelados:
            sql += " AND i.cancelado = 0"
        linhas = [dict(r) for r in self.banco.todos(sql + " ORDER BY i.id", (venda_id,))]
        for ln in linhas:
            ln["partes_nomes"] = [r[0] for r in self.banco.todos(
                "SELECT p.nome FROM itens_venda_partes x JOIN produtos p ON p.id = x.produto_id "
                "WHERE x.item_id = ? ORDER BY x.id", (ln["id"],))]
        return linhas

    def pagamentos(self, venda_id: int) -> list[dict]:
        return [dict(r) for r in self.banco.todos(
            """SELECT p.*, t.tipo, t.permite_troco, t.emite_vale FROM pagamentos_venda p
               JOIN tipos_pagamento t ON t.id = p.tipo_pagamento_id WHERE p.venda_id = ? ORDER BY p.id""",
            (venda_id,))]

    def formas_pagamento(self) -> list[dict]:
        return [dict(r) for r in self.banco.todos(
            "SELECT * FROM tipos_pagamento WHERE ativo = 1 AND caixa = 1 ORDER BY ordem, tipo")]

    def _aberta(self, venda_id: int) -> dict:
        v = self.obter(venda_id)
        if v["status"] not in ABERTAS:
            raise ErroNegocio("Esta venda já foi encerrada.")
        return v

    # ============================================================ abertura
    def _nova(self, modalidade: str, posicao: int = 0, **extra) -> int:
        turno = self.turnos.exigir_aberto()
        agora = fmt.agora()
        dados = {"uuid": str(uuid4()), "turno_id": None, "terminal": turno["terminal"],
                 "operador_id": self.operador_id, "modalidade": modalidade, "posicao": posicao,
                 "aberta_em": agora, "ultimo_lancamento_em": agora}
        dados.update(extra)
        return self.banco.inserir("vendas", dados)

    def abrir_balcao(self) -> int:
        """Retoma a venda de balcão em andamento (ex.: após queda de energia) ou abre outra."""
        self.turnos.exigir_aberto()
        r = self.banco.valor(
            "SELECT id FROM vendas WHERE modalidade = 'balcao' AND status = 'aberta' ORDER BY id DESC LIMIT 1")
        return r or self._nova("balcao")

    def abrir_caderneta(self, cliente_id: int) -> int:
        """Venda a prazo ou recebimento de dívida do cliente (a mesma tela serve aos dois:
        com itens é débito, sem itens é crédito). Reaproveita a que estiver aberta."""
        self.turnos.exigir_aberto()
        c = self.banco.um("SELECT ativo FROM clientes WHERE id = ?", (cliente_id,))
        if c is None or not c["ativo"]:
            raise ErroNegocio("Cliente inativo ou inexistente.")
        r = self.banco.valor(
            "SELECT id FROM vendas WHERE modalidade = 'caderneta' AND cliente_id = ? AND status = 'aberta'",
            (cliente_id,))
        return r or self._nova("caderneta", cliente_id=cliente_id)

    def validar_mesa(self, posicao: int) -> None:
        maximo = self.banco.cfg_int("num_mesas", 50)
        if not 1 <= posicao <= maximo:
            raise ErroNegocio(f"Mesa inválida. Use de 1 a {maximo}.")

    def abrir_mesa(self, posicao: int, pessoas: int = 0) -> tuple[int, bool]:
        """Chama a mesa se já estiver aberta; senão abre. Retorna (venda_id, criada)."""
        self.validar_mesa(posicao)
        r = self.banco.valor(
            "SELECT id FROM vendas WHERE modalidade = 'mesa' AND posicao = ? AND status IN ('aberta','conta_enviada')",
            (posicao,))
        if r:
            return r, False
        return self._nova("mesa", posicao, pessoas=max(pessoas, 0)), True

    def mesas(self) -> list[dict]:
        limite = self.banco.cfg_int("tempo_inatividade_min", 30)
        linhas = [dict(r) for r in self.banco.todos(
            """SELECT v.*, (SELECT COUNT(*) FROM itens_venda i WHERE i.venda_id = v.id AND i.cancelado = 0) AS n_itens
               FROM vendas v WHERE modalidade = 'mesa' AND status IN ('aberta','conta_enviada') ORDER BY posicao""")]
        for m in linhas:
            m["minutos_parada"] = fmt.minutos_entre(m["ultimo_lancamento_em"] or m["aberta_em"])
            m["inativa"] = bool(limite > 0 and m["status"] == "aberta" and m["minutos_parada"] >= limite)
        return linhas

    def definir_pessoas(self, venda_id: int, pessoas: int) -> None:
        self._aberta(venda_id)
        self.banco.executar("UPDATE vendas SET pessoas = ? WHERE id = ?", (max(int(pessoas), 0), venda_id))

    # ============================================================== itens
    def adicionar_item(self, venda_id: int, produto_id: int, quantidade: float, observacao: str | None = None,
                       partes: list[int] | None = None) -> int:
        v = self._aberta(venda_id)
        p = self.produtos.por_id(produto_id)
        if p is None or not p["ativo"]:
            raise ErroNegocio("Produto não encontrado.")
        if not p["venda"]:
            raise ErroNegocio(f"'{p['nome']}' não está liberado para venda.")
        quantidade = fmt.arred_qtd(quantidade)
        if quantidade <= 0:
            raise ErroNegocio("Informe uma quantidade maior que zero.")
        if not p["aceita_decimal"] and quantidade != int(quantidade):
            raise ErroNegocio(f"'{p['nome']}' não aceita quantidade fracionada.")
        if v["modalidade"] == "caderneta" and v["cliente_id"] is None:
            raise ErroNegocio("Selecione o cliente da caderneta antes de lançar itens.")

        if partes:
            qtd_partes = len(partes)
            if qtd_partes > p["partes"]:
                raise ErroNegocio(f"'{p['nome']}' pode ser dividido em no máximo {p['partes']} partes.")
            componentes = []
            for pid in partes:
                c = self.produtos.por_id(pid)
                if c is None or not c["ativo"]:
                    raise ErroNegocio("Produto de montagem não encontrado.")
                if not (c["compoe"] if p["composto"] else c["montagem"]):
                    raise ErroNegocio(f"'{c['nome']}' não pode compor '{p['nome']}'.")
                componentes.append(c)
            preco = self.produtos.preco_partes(p, componentes)
        else:
            componentes = []
            preco = self.produtos.preco_vigente(p)

        total = fmt.mult_cent(preco, quantidade)
        agora = fmt.agora()
        with self.banco.transacao():
            item_id = self.banco.inserir("itens_venda", {
                "venda_id": venda_id, "produto_id": produto_id, "quantidade": quantidade,
                "preco_unit_cent": preco, "total_cent": total, "cobra_servico": p["cobrar_servico"],
                "observacao": observacao, "comissao_cent": fmt.pct_de(total, p["comissao_pct"]),
                "partes": max(len(componentes), 1), "operador_id": self.operador_id, "criado_em": agora})
            for c in componentes:
                self.banco.inserir("itens_venda_partes", {
                    "item_id": item_id, "produto_id": c["id"], "fracao": round(1 / len(componentes), 6)})
            self.banco.executar(
                "UPDATE vendas SET ultimo_lancamento_em = ?, status = 'aberta' WHERE id = ?", (agora, venda_id))
            self.recalcular(venda_id)
        return item_id

    def cancelar_item(self, item_id: int) -> None:
        item = self.banco.um("SELECT * FROM itens_venda WHERE id = ?", (item_id,))
        if item is None or item["cancelado"]:
            raise ErroNegocio("Item não encontrado ou já cancelado.")
        self._aberta(item["venda_id"])
        with self.banco.transacao():
            self.banco.executar("UPDATE itens_venda SET cancelado = 1, cancelado_em = ? WHERE id = ?",
                                (fmt.agora(), item_id))
            self.recalcular(item["venda_id"])
            self.banco.log("item_cancelado", f"venda {item['venda_id']} item {item_id}", self.operador_id)

    def definir_observacao(self, item_id: int, texto: str | None) -> None:
        self.banco.executar("UPDATE itens_venda SET observacao = ? WHERE id = ?", ((texto or "").strip() or None, item_id))

    # ============================================================== totais
    def calcular(self, v: dict, itens: list[dict] | None = None) -> dict:
        itens = itens if itens is not None else self.itens(v["id"])
        subtotal = sum(i["total_cent"] for i in itens)
        if v["desconto_pct"] > 0:
            desconto = fmt.pct_de(subtotal, v["desconto_pct"])
        else:
            desconto = v["desconto_cent"]
        desconto = min(max(desconto, 0), subtotal)
        servico = 0
        if v["modalidade"] == "mesa" and self.banco.cfg_bool("cobra_servico_mesa", True):
            if v["servico_manual"]:
                servico = v["servico_cent"]
            else:
                base = sum(i["total_cent"] for i in itens if i["cobra_servico"])
                servico = fmt.pct_de(base, float(self.banco.cfg("servico_pct", "10") or 0))
        taxa = v["taxa_cent"]
        return {"subtotal": subtotal, "desconto": desconto, "servico": servico, "taxa": taxa,
                "total": subtotal - desconto + servico + taxa}

    def recalcular(self, venda_id: int) -> dict:
        v = self.obter(venda_id)
        c = self.calcular(v)
        self.banco.executar(
            "UPDATE vendas SET subtotal_cent = ?, desconto_cent = ?, servico_cent = ?, total_cent = ? WHERE id = ?",
            (c["subtotal"], c["desconto"], c["servico"], c["total"], venda_id))
        return c

    def definir_desconto(self, venda_id: int, pct: float | None = None, valor_cent: int | None = None) -> dict:
        v = self._aberta(venda_id)
        if pct is not None and valor_cent is not None:
            raise ErroNegocio("Informe o desconto em percentual OU em valor, não os dois.")
        if pct is not None:
            if not 0 <= pct <= 100:
                raise ErroNegocio("O percentual de desconto deve estar entre 0 e 100.")
            self.banco.executar("UPDATE vendas SET desconto_pct = ?, desconto_cent = 0 WHERE id = ?", (pct, venda_id))
        else:
            valor_cent = valor_cent or 0
            if valor_cent < 0:
                raise ErroNegocio("O desconto não pode ser negativo.")
            if valor_cent > v["subtotal_cent"]:
                raise ErroNegocio("O desconto não pode ser maior que o total dos produtos.")
            self.banco.executar("UPDATE vendas SET desconto_pct = 0, desconto_cent = ? WHERE id = ?", (valor_cent, venda_id))
        self.banco.log("desconto", f"venda {venda_id}: pct={pct} valor={valor_cent}", self.operador_id)
        return self.recalcular(venda_id)

    def definir_servico(self, venda_id: int, valor_cent: int | None) -> dict:
        """None volta ao cálculo automático. O cliente pode pagar menos (ou zero): serviço não é obrigatório."""
        self._aberta(venda_id)
        if valor_cent is None:
            self.banco.executar("UPDATE vendas SET servico_manual = 0, servico_cent = 0 WHERE id = ?", (venda_id,))
        else:
            if valor_cent < 0:
                raise ErroNegocio("O serviço não pode ser negativo.")
            self.banco.executar("UPDATE vendas SET servico_manual = 1, servico_cent = ? WHERE id = ?", (valor_cent, venda_id))
        return self.recalcular(venda_id)

    # ========================================================== pagamentos
    def adicionar_pagamento(self, venda_id: int, tipo_pagamento_id: int, valor_cent: int) -> int:
        v = self._aberta(venda_id)
        forma = self.banco.um("SELECT * FROM tipos_pagamento WHERE id = ? AND ativo = 1", (tipo_pagamento_id,))
        if forma is None or not forma["caixa"]:
            raise ErroNegocio("Esta forma de pagamento não está habilitada para o caixa.")
        if valor_cent <= 0:
            raise ErroNegocio("Informe um valor maior que zero.")
        if v["modalidade"] == "caderneta" and self.itens(venda_id):
            raise ErroNegocio("Venda em caderneta não recebe pagamento: o valor fica na conta do cliente.")
        return self.banco.inserir("pagamentos_venda", {
            "venda_id": venda_id, "tipo_pagamento_id": tipo_pagamento_id,
            "valor_cent": valor_cent, "criado_em": fmt.agora()})

    def remover_pagamento(self, pagamento_id: int) -> None:
        p = self.banco.um("SELECT venda_id FROM pagamentos_venda WHERE id = ?", (pagamento_id,))
        if p is None:
            raise ErroNegocio("Pagamento não encontrado.")
        self._aberta(p["venda_id"])
        self.banco.executar("DELETE FROM pagamentos_venda WHERE id = ?", (pagamento_id,))

    def liquidar(self, venda_id: int, total: int | None = None) -> dict:
        """Confronta pagamentos x total. Devolve pago, falta, troco, vale e o rateio do troco
        por pagamento. Levanta erro se o excesso não puder virar troco nem vale."""
        pags = self.pagamentos(venda_id)
        if total is None:
            total = self.obter(venda_id)["total_cent"]
        pago = sum(p["valor_cent"] for p in pags)
        out = {"total": total, "pago": pago, "falta": max(total - pago, 0), "troco": 0, "vale": 0, "rateio": {}}
        excesso = pago - total
        if excesso <= 0:
            return out
        cap_troco = sum(p["valor_cent"] for p in pags if p["permite_troco"])
        troco = min(excesso, cap_troco)
        vale = min(excesso - troco, sum(p["valor_cent"] for p in pags if p["emite_vale"]))
        if excesso - troco - vale > 0:
            raise ErroNegocio("O valor pago excede o total e a forma de pagamento não permite troco.")
        restante = troco
        for p in pags:
            if p["permite_troco"] and restante > 0:
                parte = min(restante, p["valor_cent"])
                out["rateio"][p["id"]] = parte
                restante -= parte
        out.update(troco=troco, vale=vale)
        return out

    def info_credito(self, venda_id: int) -> dict:
        """Recebimento de dívida na caderneta: dívida atual, valor pago e excedente."""
        v = self.obter(venda_id)
        saldo = self.banco.valor("SELECT saldo_cent FROM clientes WHERE id = ?", (v["cliente_id"],), 0)
        pago = sum(p["valor_cent"] for p in self.pagamentos(venda_id))
        divida = max(-saldo, 0)
        return {"divida": divida, "pago": pago, "excedente": max(pago - divida, 0) if divida else 0}

    # =========================================================== fechamento
    def proximo_cupom(self) -> int:
        return self.banco.valor("SELECT COALESCE(MAX(cupom), 0) + 1 FROM vendas")

    def fechar(self, venda_id: int, garcom_id: int | None = None, pessoas: int | None = None,
               excesso_como_credito: bool | None = None) -> dict:
        v = self._aberta(venda_id)
        turno = self.turnos.exigir_aberto()
        itens = self.itens(venda_id)
        eh_credito = v["modalidade"] == "caderneta" and not itens
        eh_debito = v["modalidade"] == "caderneta" and bool(itens)
        if not itens and not eh_credito:
            raise ErroNegocio("A venda não tem itens.")
        if v["modalidade"] == "caderneta" and not v["cliente_id"]:
            raise ErroNegocio("Selecione o cliente da caderneta.")
        if v["modalidade"] == "mesa" and self.banco.cfg_bool("controle_garcom") and not (garcom_id or v["garcom_id"]):
            raise ErroNegocio("Informe o garçom que atendeu a mesa.")

        with self.banco.transacao():
            calc = self.recalcular(venda_id)
            total = calc["total"]
            troco = vale = 0
            rateio: dict = {}
            if eh_credito:
                info = self.info_credito(venda_id)
                if info["pago"] <= 0:
                    raise ErroNegocio("Informe a forma de pagamento e o valor recebido.")
                creditar = info["pago"]
                if info["excedente"] > 0 and excesso_como_credito is not True:
                    if excesso_como_credito is None:
                        raise ErroNegocio("O valor excede a dívida do cliente: defina se o troco vira crédito.")
                    creditar = info["divida"]
                    liq = self.liquidar(venda_id, creditar)
                    troco, vale, rateio = liq["troco"], liq["vale"], liq["rateio"]
                total = creditar
            elif eh_debito:
                if self.pagamentos(venda_id):
                    raise ErroNegocio("Venda em caderneta não recebe pagamento. Remova os pagamentos lançados.")
                self._debitar_caderneta(v["cliente_id"], total)
            else:
                liq = self.liquidar(venda_id, total)
                if liq["falta"] > 0:
                    raise ErroNegocio(f"Faltam {fmt.fmt_brl(liq['falta'])} para completar o pagamento.")
                troco, vale, rateio = liq["troco"], liq["vale"], liq["rateio"]

            for pag_id, parte in rateio.items():
                self.banco.executar("UPDATE pagamentos_venda SET troco_cent = ? WHERE id = ?", (parte, pag_id))
            pago = sum(p["valor_cent"] for p in self.pagamentos(venda_id))
            agora = fmt.agora()
            self.banco.atualizar("vendas", venda_id, {
                "turno_id": turno["id"], "cupom": self.proximo_cupom(), "status": "fechada", "fechada_em": agora,
                "total_cent": total, "pago_cent": pago, "troco_cent": troco, "vale_cent": vale,
                "garcom_id": garcom_id or v["garcom_id"],
                "pessoas": 0 if eh_credito else (pessoas if pessoas is not None else (v["pessoas"] or 1)),
                "sincronizado": 0})
            if eh_credito:
                self._creditar_caderneta(v["cliente_id"], venda_id, total)
            elif itens:
                self.estoque.baixar_venda(venda_id)
            if eh_debito:
                self.banco.inserir("caderneta", {
                    "cliente_id": v["cliente_id"], "venda_id": venda_id, "tipo": "debito", "valor_cent": total,
                    "descricao": "Venda em caderneta", "criado_em": agora})
        return self.obter(venda_id)

    def _debitar_caderneta(self, cliente_id: int, total: int) -> None:
        c = self.banco.um("SELECT nome, saldo_cent, limite_cent, ativo FROM clientes WHERE id = ?", (cliente_id,))
        if c is None or not c["ativo"]:
            raise ErroNegocio("Cliente da caderneta inativo ou inexistente.")
        if total <= 0:
            raise ErroNegocio("O total da venda em caderneta deve ser maior que zero.")
        novo = c["saldo_cent"] - total
        if c["limite_cent"] > 0 and novo < -c["limite_cent"]:
            raise ErroNegocio(f"Limite de crédito excedido para {c['nome']}: limite {fmt.fmt_brl(c['limite_cent'])}, "
                              f"dívida após a venda {fmt.fmt_brl(-novo)}.")
        self.banco.executar("UPDATE clientes SET saldo_cent = ? WHERE id = ?", (novo, cliente_id))

    def _creditar_caderneta(self, cliente_id: int, venda_id: int, valor: int) -> None:
        if valor <= 0:
            return
        self.banco.executar("UPDATE clientes SET saldo_cent = saldo_cent + ? WHERE id = ?", (valor, cliente_id))
        self.banco.inserir("caderneta", {
            "cliente_id": cliente_id, "venda_id": venda_id, "tipo": "credito", "valor_cent": valor,
            "descricao": "Pagamento / crédito", "criado_em": fmt.agora()})

    # ============================================================ cancelar
    def cancelar_venda(self, venda_id: int, motivo: str = "") -> None:
        """Venda aberta: some se estiver vazia; senão vira cupom cancelado. Cupom fechado:
        só no turno ainda aberto; estorna estoque e caderneta."""
        v = self.obter(venda_id)
        agora = fmt.agora()
        with self.banco.transacao():
            if v["status"] in ABERTAS:
                if not self.itens(venda_id, cancelados=True) and not self.pagamentos(venda_id):
                    self.banco.executar("DELETE FROM vendas WHERE id = ?", (venda_id,))
                    return
                self.banco.atualizar("vendas", venda_id, {
                    "status": "cancelada", "cupom": self.proximo_cupom(), "fechada_em": agora,
                    "turno_id": self.turnos.exigir_aberto()["id"],
                    "cancelada_por": self.operador_id, "motivo_cancelamento": motivo, "sincronizado": 0})
                self.banco.executar("DELETE FROM pagamentos_venda WHERE venda_id = ?", (venda_id,))
            elif v["status"] == "fechada":
                turno = self.turnos.atual()
                if turno is None or v["turno_id"] != turno["id"]:
                    raise ErroNegocio("Só é possível cancelar cupons do turno atual. Este turno já foi fechado.")
                self.estoque.estornar_venda(venda_id)
                self._estornar_caderneta(v)
                self.banco.atualizar("vendas", venda_id, {
                    "status": "cancelada", "cancelada_por": self.operador_id, "motivo_cancelamento": motivo,
                    "sincronizado": 0})
            else:
                raise ErroNegocio("Este cupom já está cancelado.")
            self.banco.log("venda_cancelada", f"venda {venda_id} cupom {v['cupom']} {motivo}".strip(), self.operador_id)

    def _estornar_caderneta(self, v: dict) -> None:
        for lan in self.banco.todos("SELECT * FROM caderneta WHERE venda_id = ?", (v["id"],)):
            sinal = 1 if lan["tipo"] == "debito" else -1
            self.banco.executar("UPDATE clientes SET saldo_cent = saldo_cent + ? WHERE id = ?",
                                (sinal * lan["valor_cent"], lan["cliente_id"]))
        self.banco.executar("DELETE FROM caderneta WHERE venda_id = ?", (v["id"],))

    # ====================================================== mesas / contas
    def enviar_conta(self, venda_id: int) -> dict:
        """Marca a mesa como 'conta enviada' (bandeja) e devolve os totais para a pré-conta."""
        v = self._aberta(venda_id)
        if v["modalidade"] != "mesa":
            raise ErroNegocio("Somente mesas enviam conta.")
        if not self.itens(venda_id):
            raise ErroNegocio("A mesa não tem itens.")
        self.banco.executar("UPDATE vendas SET status = 'conta_enviada' WHERE id = ?", (venda_id,))
        return self.recalcular(venda_id)

    def _mover_itens(self, origem_id: int, destino_id: int) -> None:
        self.banco.executar("UPDATE itens_venda SET venda_id = ? WHERE venda_id = ?", (destino_id, origem_id))
        pessoas = self.banco.valor("SELECT pessoas FROM vendas WHERE id = ?", (origem_id,), 0)
        self.banco.executar("UPDATE vendas SET pessoas = pessoas + ?, ultimo_lancamento_em = ?, status = 'aberta' "
                            "WHERE id = ?", (pessoas, fmt.agora(), destino_id))
        self.banco.executar("DELETE FROM vendas WHERE id = ?", (origem_id,))

    def _mesa_aberta(self, posicao: int) -> dict:
        r = self.banco.um("SELECT * FROM vendas WHERE modalidade = 'mesa' AND posicao = ? AND status IN ('aberta','conta_enviada')",
                          (posicao,))
        if r is None:
            raise ErroNegocio(f"A mesa {posicao} não está aberta.")
        return dict(r)

    def transferir_mesa(self, origem: int, destino: int) -> int:
        """Mesa inteira para outra posição. Se o destino já estiver aberto, os itens se somam."""
        self.validar_mesa(destino)
        if origem == destino:
            raise ErroNegocio("Origem e destino são a mesma mesa.")
        with self.banco.transacao():
            o = self._mesa_aberta(origem)
            d = self.banco.um("SELECT id FROM vendas WHERE modalidade = 'mesa' AND posicao = ? "
                              "AND status IN ('aberta','conta_enviada')", (destino,))
            if d is None:
                self.banco.executar("UPDATE vendas SET posicao = ?, status = 'aberta' WHERE id = ?", (destino, o["id"]))
                destino_id = o["id"]
            else:
                destino_id = d["id"]
                self._mover_itens(o["id"], destino_id)
            self.recalcular(destino_id)
        return destino_id

    def transferir_varias(self, origens: list[int], destino: int) -> int:
        """Várias mesas para uma só (tecla T no caixa)."""
        self.validar_mesa(destino)
        origens = [o for o in dict.fromkeys(origens) if o != destino]
        if not origens:
            raise ErroNegocio("Informe ao menos uma mesa de origem.")
        with self.banco.transacao():
            for o in origens:
                self._mesa_aberta(o)
            destino_id, _ = self.abrir_mesa(destino)
            for o in origens:
                self._mover_itens(self._mesa_aberta(o)["id"], destino_id)
            self.recalcular(destino_id)
        return destino_id

    def transferir_item(self, item_id: int, destino: int, quantidade: float) -> None:
        """Parte dos produtos de uma mesa para outra."""
        quantidade = fmt.arred_qtd(quantidade)
        item = self.banco.um("SELECT * FROM itens_venda WHERE id = ? AND cancelado = 0", (item_id,))
        if item is None:
            raise ErroNegocio("Item não encontrado.")
        origem = self._aberta(item["venda_id"])
        if origem["modalidade"] != "mesa":
            raise ErroNegocio("Só é possível transferir itens entre mesas.")
        if origem["posicao"] == destino:
            raise ErroNegocio("Origem e destino são a mesma mesa.")
        if not 0 < quantidade <= item["quantidade"]:
            raise ErroNegocio(f"Quantidade inválida (máximo {fmt.fmt_qtd(item['quantidade'], 3)}).")
        with self.banco.transacao():
            destino_id, _ = self.abrir_mesa(destino)
            if quantidade == item["quantidade"]:
                self.banco.executar("UPDATE itens_venda SET venda_id = ? WHERE id = ?", (destino_id, item_id))
            else:
                resto = fmt.arred_qtd(item["quantidade"] - quantidade)
                self.banco.executar("UPDATE itens_venda SET quantidade = ?, total_cent = ? WHERE id = ?",
                                    (resto, fmt.mult_cent(item["preco_unit_cent"], resto), item_id))
                novo = dict(item)
                novo.pop("id")
                novo.update(venda_id=destino_id, quantidade=quantidade,
                            total_cent=fmt.mult_cent(item["preco_unit_cent"], quantidade))
                novo_id = self.banco.inserir("itens_venda", novo)
                for pt in self.banco.todos("SELECT produto_id, fracao FROM itens_venda_partes WHERE item_id = ?", (item_id,)):
                    self.banco.inserir("itens_venda_partes", {"item_id": novo_id, "produto_id": pt["produto_id"], "fracao": pt["fracao"]})
            self.banco.executar("UPDATE vendas SET ultimo_lancamento_em = ?, status = 'aberta' WHERE id = ?",
                                (fmt.agora(), destino_id))
            self.recalcular(origem["id"])
            self.recalcular(destino_id)
