"""Turno de caixa: abertura com fundo de caixa, sangrias/entradas, repique e a
troca de turno (fechamento) com sobra ou falta (manual do Caixa)."""
from __future__ import annotations

from src.controllers import conferencia_turno
from src.core import formatacao as fmt
from src.core import licenca
from src.core.erros import ErroNegocio


class TurnoController:
    def __init__(self, banco, terminal: int | None = None):
        self.banco = banco
        self.terminal = terminal or banco.cfg_int("terminal", 1)

    # ------------------------------------------------------------- consulta
    def atual(self) -> dict | None:
        r = self.banco.um("SELECT * FROM turnos WHERE terminal = ? AND status = 'aberto'", (self.terminal,))
        return dict(r) if r else None

    def exigir_aberto(self) -> dict:
        t = self.atual()
        if t is None:
            raise ErroNegocio("Não há turno aberto neste caixa. Abra o turno informando o fundo de caixa.")
        return t

    def obter(self, turno_id: int) -> dict:
        r = self.banco.um("SELECT * FROM turnos WHERE id = ?", (turno_id,))
        if r is None:
            raise ErroNegocio("Turno não encontrado.")
        return dict(r)

    def numero_sugerido(self) -> int:
        """Próximo número de turno; depois do último volta ao primeiro (manual do Caixa)."""
        total = max(self.banco.cfg_int("num_turnos", 3), 1)
        ultimo = self.banco.valor(
            "SELECT numero FROM turnos WHERE terminal = ? ORDER BY id DESC LIMIT 1", (self.terminal,), 0)
        return ultimo % total + 1 if ultimo else 1

    # ------------------------------------------------------------- abertura
    def abrir(self, operador_id: int, numero: int, valor_inicial_cent: int) -> int:
        est = licenca.estado(self.banco)
        if est.bloqueia:
            raise ErroNegocio(f"{est.mensagem} Renove a licença na tela de entrada antes de abrir um turno.")
        if self.atual():
            raise ErroNegocio("Já existe um turno aberto neste caixa.")
        if numero < 1:
            raise ErroNegocio("Informe o número do turno (1 em diante).")
        if valor_inicial_cent < 0:
            raise ErroNegocio("O valor inicial (fundo de caixa) não pode ser negativo.")
        with self.banco.transacao():
            proximo_cupom = self.banco.valor("SELECT COALESCE(MAX(cupom), 0) + 1 FROM vendas")
            tid = self.banco.inserir("turnos", {
                "numero": numero, "terminal": self.terminal, "operador_id": operador_id,
                "aberto_em": fmt.agora(), "valor_inicial_cent": valor_inicial_cent,
                "cupom_inicial": proximo_cupom, "status": "aberto"})
            self.banco.log("turno_aberto", f"turno {numero}, fundo {fmt.fmt_brl(valor_inicial_cent)}", operador_id)
            if licenca.exigida(self.banco):
                licenca.registrar_uso(self.banco)
        return tid

    # ---------------------------------------------- sangria e repique
    def movimentar(self, turno_id: int, operador_id: int, tipo: str, valor_cent: int, descricao: str = "") -> int:
        """Entrada ('suprimento') ou saída ('sangria') de dinheiro do caixa."""
        if tipo not in ("entrada", "saida"):
            raise ErroNegocio("Tipo de movimento inválido.")
        if valor_cent <= 0:
            raise ErroNegocio("Informe um valor maior que zero.")
        self._exigir_turno_aberto(turno_id)
        mid = self.banco.inserir("movimentos_caixa", {
            "turno_id": turno_id, "tipo": tipo, "valor_cent": valor_cent,
            "descricao": (descricao or "").strip(), "operador_id": operador_id, "criado_em": fmt.agora()})
        self.banco.log("sangria" if tipo == "saida" else "suprimento",
                       f"{fmt.fmt_brl(valor_cent)} {descricao}".strip(), operador_id)
        return mid

    def movimentos(self, turno_id: int) -> list[dict]:
        return [dict(r) for r in self.banco.todos(
            "SELECT m.*, o.nome AS operador FROM movimentos_caixa m LEFT JOIN operadores o ON o.id = m.operador_id "
            "WHERE m.turno_id = ? ORDER BY m.id", (turno_id,))]

    def repique(self, turno_id: int, operador_id: int, posicao: int, valor_cent: int, comanda: bool = False) -> int:
        """Caixinha deixada pelo cliente após pagar (não é o serviço). `posicao` é a mesa ou, com comanda=True, a comanda."""
        if valor_cent <= 0:
            raise ErroNegocio("Informe o valor do repique.")
        self._exigir_turno_aberto(turno_id)
        venda = self.banco.valor(
            "SELECT id FROM vendas WHERE modalidade = 'mesa' AND comanda = ? AND posicao = ? ORDER BY id DESC LIMIT 1",
            (int(comanda), posicao))
        return self.banco.inserir("repiques", {
            "turno_id": turno_id, "venda_id": venda, "posicao": posicao, "valor_cent": valor_cent,
            "operador_id": operador_id, "criado_em": fmt.agora()})

    def _exigir_turno_aberto(self, turno_id: int) -> None:
        if self.obter(turno_id)["status"] != "aberto":
            raise ErroNegocio("Este turno já foi fechado.")

    # --------------------------------------------------------------- resumo
    def resumo(self, turno_id: int) -> dict:
        """Todos os números da tela de troca de turno. Valores em centavos."""
        b = self.banco
        t = self.obter(turno_id)
        fechadas = "turno_id = ? AND status = 'fechada'"
        com_itens = f"{fechadas} AND EXISTS (SELECT 1 FROM itens_venda i WHERE i.venda_id = vendas.id AND i.cancelado = 0)"

        def soma(coluna, filtro=com_itens):
            return b.valor(f"SELECT COALESCE(SUM({coluna}), 0) FROM vendas WHERE {filtro}", (turno_id,), 0)

        recebimentos = [dict(r) for r in b.todos(
            """SELECT t.id AS tipo_id, t.tipo, t.na_gaveta, SUM(p.valor_cent - p.troco_cent) AS valor
               FROM pagamentos_venda p JOIN vendas v ON v.id = p.venda_id
               JOIN tipos_pagamento t ON t.id = p.tipo_pagamento_id
               WHERE v.turno_id = ? AND v.status = 'fechada'
               GROUP BY t.id ORDER BY t.ordem, t.tipo""", (turno_id,))]
        total_recebido = sum(r["valor"] for r in recebimentos)
        na_gaveta = sum(r["valor"] for r in recebimentos if r["na_gaveta"])
        tc = b.valor(f"SELECT COUNT(*) FROM vendas WHERE {com_itens}", (turno_id,), 0)
        venda_total = soma("total_cent")
        pessoas = soma("pessoas")
        entradas = b.valor("SELECT COALESCE(SUM(valor_cent),0) FROM movimentos_caixa WHERE turno_id = ? AND tipo='entrada'", (turno_id,), 0)
        saidas = b.valor("SELECT COALESCE(SUM(valor_cent),0) FROM movimentos_caixa WHERE turno_id = ? AND tipo='saida'", (turno_id,), 0)
        entregas_total = b.valor(
            f"SELECT COALESCE(SUM(total_cent),0) FROM vendas WHERE {com_itens} AND modalidade = 'entrega'", (turno_id,), 0)
        cupons = b.um(f"SELECT MIN(cupom) AS ini, MAX(cupom) AS fim FROM vendas WHERE {fechadas}", (turno_id,))
        r = {
            "turno": t,
            "recebimentos": recebimentos,
            "total_recebido": total_recebido,
            "troco": soma("troco_cent", fechadas),
            "vale_emitido": soma("vale_cent", fechadas),
            "venda": soma("subtotal_cent"),
            "desconto": soma("desconto_cent"),
            "servico": soma("servico_cent"),
            "taxa": soma("taxa_cent"),
            "repique": b.valor("SELECT COALESCE(SUM(valor_cent),0) FROM repiques WHERE turno_id = ?", (turno_id,), 0),
            "entregas_pendentes": b.valor(
                "SELECT COUNT(*) FROM vendas WHERE modalidade = 'entrega' AND status IN ('aberta','conta_enviada')", (), 0),
            "venda_caderneta": b.valor(
                f"SELECT COALESCE(SUM(total_cent),0) FROM vendas WHERE {com_itens} AND modalidade = 'caderneta'", (turno_id,), 0),
            "pagtos_caderneta": b.valor(
                """SELECT COALESCE(SUM(p.valor_cent - p.troco_cent),0) FROM pagamentos_venda p
                   JOIN vendas v ON v.id = p.venda_id WHERE v.turno_id = ? AND v.status = 'fechada'
                   AND v.modalidade = 'caderneta'""", (turno_id,), 0),
            "entradas": entradas, "saidas": saidas,
            "tc": tc,
            "tm": fmt.dividir_cent(venda_total, tc),
            "pessoas": pessoas,
            "valor_por_pessoa": fmt.dividir_cent(venda_total, pessoas),
            "posicoes": b.valor(f"SELECT COUNT(DISTINCT comanda * 100000 + posicao) FROM vendas WHERE {com_itens} AND modalidade = 'mesa'", (turno_id,), 0),
            "entregas": b.valor(f"SELECT COUNT(*) FROM vendas WHERE {com_itens} AND modalidade = 'entrega'", (turno_id,), 0),
            "perc_entrega": round(entregas_total * 100 / venda_total, 2) if venda_total else 0.0,
            "cupom_inicial": t["cupom_inicial"],
            "cupom_final": cupons["fim"] or 0,
            "valor_inicial": t["valor_inicial_cent"],
        }
        # Valor esperado na gaveta: fundo + recebido nas formas que ficam na gaveta (dinheiro, cheque, ticket;
        # já líquido de troco) + suprimentos - sangrias. Cartão e Pix não entram: são conferidos na maquininha.
        r["esperado"] = t["valor_inicial_cent"] + na_gaveta + entradas - saidas
        r["fora_da_gaveta"] = total_recebido - na_gaveta
        r.update(conferencia_turno.conferencia(b, t))      # posições abertas, cancelamentos e transferências do turno
        return r

    def posicoes_abertas(self) -> list[dict]:
        """Mesas e comandas com consumo ainda abertas: o caixa avisa ao trocar o turno."""
        return conferencia_turno.posicoes_abertas(self.banco)

    def fechar(self, turno_id: int, operador_id: int, valor_final_cent: int) -> dict:
        """Troca de turno. O operador declara o que entrega ANTES de ver o esperado
        (o sistema não permite 'acertar' o caixa depois)."""
        if valor_final_cent < 0:
            raise ErroNegocio("O valor final não pode ser negativo.")
        self._exigir_turno_aberto(turno_id)
        em_andamento = self.banco.valor(
            "SELECT COUNT(*) FROM vendas WHERE modalidade IN ('balcao','caderneta') AND status = 'aberta' "
            "AND EXISTS (SELECT 1 FROM itens_venda i WHERE i.venda_id = vendas.id AND i.cancelado = 0)", (), 0)
        if em_andamento:
            raise ErroNegocio("Há uma venda em andamento no caixa. Conclua ou cancele antes de trocar o turno.")
        with self.banco.transacao():
            res = self.resumo(turno_id)
            resultado = valor_final_cent - res["esperado"]
            self.banco.atualizar("turnos", turno_id, {
                "fechado_em": fmt.agora(), "valor_final_cent": valor_final_cent,
                "cupom_final": res["cupom_final"], "esperado_cent": res["esperado"],
                "resultado_cent": resultado, "fechado_por": operador_id, "status": "fechado"})
            self.banco.log("turno_fechado", f"turno {res['turno']['numero']} resultado {fmt.fmt_brl(resultado)}", operador_id)
            if licenca.exigida(self.banco):
                licenca.registrar_uso(self.banco)
        res = self.resumo(turno_id)
        res["valor_final"] = valor_final_cent
        res["resultado"] = resultado
        return res
