"""Comissão das garotas (boate).

No caixa, o código 50 (configurável) abre a janela da comissão: o número da garota é o da comanda dela (comanda 180 = garota
180) e o operador digita o valor. Aqui a comissão é registrada no número da garota. Não é venda: nada disso entra no
faturamento, no estoque nem na conferência do dinheiro até a comissão ser PAGA, quando sai dinheiro do caixa (uma sangria).

Situações: 'pendente' (a pagar), 'paga' e 'cancelada'. Nada é apagado: lançamento errado é cancelado, com quem e quando.
O cadastro de garotas (número e nome) é opcional: serve para mostrar o nome na hora de lançar e nos relatórios.
"""
from __future__ import annotations

from src.controllers.turno_controller import TurnoController
from src.core import formatacao as fmt
from src.core.erros import ErroNegocio

NUMERO_MAXIMO = 99999
LIMITE_CONFIRMAR_CENT = 50000     # a tela pede confirmação acima disso: 2500 digitado no lugar de 25,00


class ComissaoController:
    def __init__(self, banco):
        self.banco = banco

    # --------------------------------------------------------------- o código do caixa
    def codigo(self) -> str:
        """O código que, digitado no caixa, lança a comissão (configuração `codigo_comissao`; vazio desliga)."""
        return (self.banco.cfg("codigo_comissao", "50") or "").strip()

    def eh_codigo(self, texto) -> bool:
        """True se o que foi digitado no campo do código é o da comissão: 50, 050 e 0000000000050 são o mesmo."""
        cod, t = self.codigo(), ("" if texto is None else str(texto)).strip()
        if not cod or not t:
            return False
        if cod.isdigit() and t.isdigit():
            return int(cod) == int(t)
        return cod.lower() == t.lower()

    # --------------------------------------------------------------- cadastro de garotas
    @staticmethod
    def validar_numero(numero) -> int:
        try:
            n = int(str(numero).strip())
        except (TypeError, ValueError):
            raise ErroNegocio("Digite o número da garota (somente números).") from None
        if not 1 <= n <= NUMERO_MAXIMO:
            raise ErroNegocio(f"O número da garota vai de 1 a {NUMERO_MAXIMO}.")
        return n

    def garota(self, numero) -> dict | None:
        r = self.banco.um("SELECT * FROM garotas WHERE numero = ?", (int(numero),))
        return dict(r) if r else None

    def nome(self, numero) -> str:
        """Nome da garota cadastrada com esse número ('' se não houver cadastro)."""
        try:
            g = self.garota(numero)
        except (TypeError, ValueError):
            return ""
        return (g["nome"] if g else "") or ""

    def cadastro_vazio(self) -> bool:
        return self.banco.valor("SELECT 1 FROM garotas LIMIT 1") is None

    # --------------------------------------------------------------- lançar e consultar
    def lancar(self, garota, valor_cent: int, turno_id: int | None, operador_id: int | None, observacao: str = "") -> int:
        """Marca a comissão no número da garota. Devolve o id do lançamento."""
        n = self.validar_numero(garota)
        valor_cent = int(valor_cent)
        if valor_cent <= 0:
            raise ErroNegocio("Informe o valor da comissão (maior que zero).")
        if turno_id is None or TurnoController(self.banco).obter(turno_id)["status"] != "aberto":
            raise ErroNegocio("Abra o turno do caixa antes de lançar comissão.")
        cid = self.banco.inserir("comissoes_garotas", {
            "garota": n, "valor_cent": valor_cent, "turno_id": turno_id, "operador_id": operador_id,
            "observacao": (observacao or "").strip() or None, "criado_em": fmt.agora(), "status": "pendente"})
        self.banco.log("comissao_lancada", f"garota {n} {fmt.fmt_brl(valor_cent)}", operador_id)
        return cid

    def pendente(self, garota) -> int:
        """Quanto falta pagar a essa garota, em centavos."""
        return self.banco.valor(
            "SELECT COALESCE(SUM(valor_cent), 0) FROM comissoes_garotas WHERE garota = ? AND status = 'pendente'",
            (self.validar_numero(garota),), 0)

    def total_a_pagar(self) -> int:
        """Tudo o que está pendente, de todas as garotas e de todos os turnos, em centavos."""
        return self.banco.valor("SELECT COALESCE(SUM(valor_cent), 0) FROM comissoes_garotas WHERE status = 'pendente'", (), 0)

    def pendentes_por_garota(self) -> list[dict]:
        """Uma linha por garota com comissão a pagar: número, nome, nº de lançamentos, total e o mais antigo."""
        return [dict(r) for r in self.banco.todos(
            """SELECT c.garota, COALESCE(g.nome, '') AS nome, COUNT(*) AS lancamentos, SUM(c.valor_cent) AS total_cent,
                      MIN(c.criado_em) AS desde
               FROM comissoes_garotas c LEFT JOIN garotas g ON g.numero = c.garota
               WHERE c.status = 'pendente' GROUP BY c.garota ORDER BY c.garota""")]

    def lancamentos(self, garota, status: str | None = "pendente") -> list[dict]:
        sql = ("""SELECT c.*, o.nome AS operador, t.numero AS turno FROM comissoes_garotas c
                  LEFT JOIN operadores o ON o.id = c.operador_id LEFT JOIN turnos t ON t.id = c.turno_id
                  WHERE c.garota = ?""")
        params: list = [self.validar_numero(garota)]
        if status:
            sql += " AND c.status = ?"
            params.append(status)
        return [dict(r) for r in self.banco.todos(sql + " ORDER BY c.id", params)]

    def resumo_turno(self, turno_id: int) -> dict:
        """O que foi lançado no turno (sem os cancelados): quantidade, total e o total de cada garota."""
        linhas = [dict(r) for r in self.banco.todos(
            """SELECT c.garota, COALESCE(g.nome, '') AS nome, COUNT(*) AS lancamentos, SUM(c.valor_cent) AS total_cent
               FROM comissoes_garotas c LEFT JOIN garotas g ON g.numero = c.garota
               WHERE c.turno_id = ? AND c.status <> 'cancelada' GROUP BY c.garota ORDER BY c.garota""", (turno_id,))]
        return {"quantidade": sum(l["lancamentos"] for l in linhas), "total_cent": sum(l["total_cent"] for l in linhas),
                "por_garota": linhas}

    # --------------------------------------------------------------- cancelar e pagar
    def cancelar(self, comissao_id: int, operador_id: int | None, motivo: str = "") -> None:
        """Cancela um lançamento ainda pendente (digitado errado). Fica guardado, com quem cancelou e quando."""
        c = self.banco.um("SELECT garota, valor_cent FROM comissoes_garotas WHERE id = ?", (comissao_id,))
        n = self.banco.executar(
            "UPDATE comissoes_garotas SET status = 'cancelada', cancelada_em = ?, cancelada_por = ?, "
            "motivo_cancelamento = ? WHERE id = ? AND status = 'pendente'",
            (fmt.agora(), operador_id, (motivo or "").strip() or None, comissao_id)).rowcount
        if not n:
            raise ErroNegocio("Só é possível cancelar comissão pendente: esta já foi paga ou cancelada.")
        self.banco.log("comissao_cancelada", f"garota {c['garota']} {fmt.fmt_brl(c['valor_cent'])} {motivo}".strip(), operador_id)

    def pagar(self, garota, turno_id: int | None, operador_id: int | None, tirar_do_caixa: bool = True) -> dict:
        """Paga TUDO que está pendente para a garota. Com `tirar_do_caixa` registra a saída do dinheiro no turno (uma
        sangria 'Comissão garota 180 NOME'), então a conferência da gaveta já conta com ela. Devolve o resumo do pagamento."""
        n = self.validar_numero(garota)
        with self.banco.transacao():
            itens = self.lancamentos(n, "pendente")
            if not itens:
                raise ErroNegocio(f"A garota {n} não tem comissão pendente.")
            total = sum(i["valor_cent"] for i in itens)
            nome = self.nome(n)
            movimento = None
            if tirar_do_caixa:
                if turno_id is None:
                    raise ErroNegocio("Abra o turno do caixa para pagar com o dinheiro do caixa.")
                movimento = TurnoController(self.banco).movimentar(
                    turno_id, operador_id, "saida", total, f"Comissão garota {n}{' ' + nome if nome else ''}")
            agora = fmt.agora()
            self.banco.executar(
                "UPDATE comissoes_garotas SET status = 'paga', paga_em = ?, pago_por = ?, movimento_id = ? "
                "WHERE garota = ? AND status = 'pendente'", (agora, operador_id, movimento, n))
            self.banco.log("comissao_paga", f"garota {n} {fmt.fmt_brl(total)} ({len(itens)} lançamentos)"
                           + ("" if tirar_do_caixa else " fora do caixa"), operador_id)
        return {"garota": n, "nome": nome, "total_cent": total, "quantidade": len(itens), "movimento_id": movimento,
                "lancamentos": itens, "pago_em": agora, "tirou_do_caixa": bool(tirar_do_caixa)}
