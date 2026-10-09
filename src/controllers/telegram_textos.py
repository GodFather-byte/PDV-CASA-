"""Textos que o dono recebe no Telegram: resumos sob demanda (os botões do bot) e avisos de eventos do caixa.

Só texto simples (sem formatação do Telegram, para nunca falhar por causa de um caractere). Dinheiro em reais, como no
resto do PDV. Não leva dados de clientes (nome, CPF, telefone): só totais, números de comanda e nomes de operadores.
"""
from __future__ import annotations

from src.controllers.relatorio_vendas import virada_dia
from src.controllers.turno_controller import TurnoController
from src.core import formatacao as fmt
from src.core.posicao import nome as nome_posicao

DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
LIMITE_LISTA = 12          # linhas por lista: o celular não é lugar de relatório de 200 linhas


def _brl(cent) -> str:
    return fmt.fmt_brl(cent)


def _dia_rotulo(dia: str) -> str:
    from datetime import datetime
    d = datetime.strptime(dia[:10], "%Y-%m-%d")
    return f"{DIAS[d.weekday()]} {d.strftime('%d/%m')}"


def _hora(iso: str | None) -> str:
    return (iso or "")[11:16]


def _qtd(q) -> str:
    """2,000 -> '2'; 1,500 -> '1,5'."""
    return fmt.fmt_qtd(q).rstrip("0").rstrip(",")


def dia_atual(banco) -> str:
    return fmt.dia_operacional(virada=virada_dia(banco))


def dia_anterior(banco) -> str:
    return fmt.somar_dias(dia_atual(banco), -1)


def _faixa(banco, dia: str) -> tuple[str, str]:
    return fmt.faixa_dia_operacional(dia, virada_dia(banco))


def _recortar(linhas: list[str], limite: int = LIMITE_LISTA) -> list[str]:
    if len(linhas) <= limite:
        return linhas
    return linhas[:limite] + [f"... e mais {len(linhas) - limite}"]


# ------------------------------------------------------------------ resumos
def resumo(banco, dia: str | None = None, fechado: bool = False) -> str:
    """Faturamento, vendas, formas de pagamento, cancelamentos, sangrias e diferença de caixa de um dia operacional.
    `fechado`: a noite já acabou (resumo automático da manhã); senão é 'até agora'."""
    dia = dia or dia_atual(banco)
    ini, fim = _faixa(banco, dia)
    base = ("FROM vendas v WHERE v.status = 'fechada' AND v.fechada_em >= ? AND v.fechada_em < ? AND v.subtotal_cent > 0 "
            "AND EXISTS (SELECT 1 FROM itens_venda i WHERE i.venda_id = v.id AND i.cancelado = 0)")
    r = banco.um(f"SELECT COUNT(*) AS n, COALESCE(SUM(v.total_cent),0) AS total, COALESCE(SUM(v.pessoas),0) AS pessoas {base}",
                 (ini, fim))
    formas = banco.todos(
        f"""SELECT t.tipo, SUM(p.valor_cent - p.troco_cent) AS valor FROM pagamentos_venda p
            JOIN vendas v ON v.id = p.venda_id JOIN tipos_pagamento t ON t.id = p.tipo_pagamento_id
            WHERE v.status = 'fechada' AND v.fechada_em >= ? AND v.fechada_em < ? GROUP BY t.id
            HAVING valor <> 0 ORDER BY t.ordem, t.tipo""", (ini, fim))
    canc = banco.um(
        """SELECT COUNT(*) AS n, COALESCE(SUM(subtotal_cent),0) AS total FROM vendas
           WHERE status = 'cancelada' AND fechada_em >= ? AND fechada_em < ? AND subtotal_cent > 0""", (ini, fim))
    itens_canc = banco.um(
        """SELECT COUNT(*) AS n, COALESCE(SUM(i.total_cent),0) AS total FROM itens_venda i
           WHERE i.cancelado = 1 AND i.cancelado_em >= ? AND i.cancelado_em < ?""", (ini, fim))
    sangrias = banco.valor("SELECT COALESCE(SUM(valor_cent),0) FROM movimentos_caixa WHERE tipo = 'saida' "
                           "AND criado_em >= ? AND criado_em < ?", (ini, fim), 0)
    turnos = banco.todos("SELECT numero, resultado_cent, o.nome AS operador FROM turnos t LEFT JOIN operadores o ON o.id = t.operador_id "
                         "WHERE t.status = 'fechado' AND t.fechado_em >= ? AND t.fechado_em < ? ORDER BY t.id", (ini, fim))

    titulo = "Resumo da noite" if fechado else "Resumo até agora"
    linhas = [f"📊 {titulo} — {_dia_rotulo(dia)}", ""]
    if not r["n"]:
        linhas.append("Nenhuma venda fechada ainda.")
    else:
        linhas += [f"💰 Faturamento: {_brl(r['total'])}",
                   f"🧾 Vendas: {r['n']}  ·  Ticket médio: {_brl(fmt.dividir_cent(r['total'], r['n']))}"]
        if r["pessoas"]:
            linhas.append(f"👥 Pessoas: {r['pessoas']}  ·  {_brl(fmt.dividir_cent(r['total'], r['pessoas']))} por pessoa")
        if formas:
            linhas += ["", "Recebido por forma:"] + [f" • {f['tipo']}: {_brl(f['valor'])}" for f in formas]
    avisos = []
    if canc["n"]:
        avisos.append(f"❌ Cupons cancelados: {canc['n']} ({_brl(canc['total'])})")
    if itens_canc["n"]:
        avisos.append(f"❌ Itens cancelados: {itens_canc['n']} ({_brl(itens_canc['total'])})")
    if sangrias:
        avisos.append(f"💸 Sangrias: {_brl(sangrias)}")
    if avisos:
        linhas += [""] + avisos
    for t in turnos:
        linhas.append(f"⚖️ Turno {t['numero']} ({t['operador'] or '?'}): {_diferenca(t['resultado_cent'])}")
    if fechado:
        sem = banco.valor("SELECT COUNT(*) FROM produtos WHERE controla_estoque = 1 AND ativo = 1 AND qt_atual <= 0", (), 0)
        if sem:
            linhas += ["", f"📦 Produtos sem estoque: {sem} (toque em Estoque para ver)"]
    return "\n".join(linhas)


def _diferenca(resultado_cent: int | None) -> str:
    if resultado_cent is None:
        return "sem conferência"
    if resultado_cent == 0:
        return "✅ caixa bateu certinho"
    return f"{'⚠️ sobrou' if resultado_cent > 0 else '🚨 faltou'} {_brl(abs(resultado_cent))}"


def caixa(banco) -> str:
    """Como está o caixa agora: quem abriu, quanto vendeu no turno e quanto deveria ter de dinheiro na gaveta."""
    turnos = TurnoController(banco)
    t = turnos.atual()
    if t is None:
        ultimo = banco.um("SELECT t.numero, t.fechado_em, t.resultado_cent, o.nome AS operador FROM turnos t "
                          "LEFT JOIN operadores o ON o.id = t.operador_id WHERE t.status = 'fechado' ORDER BY t.id DESC LIMIT 1")
        linhas = ["💵 Nenhum caixa aberto agora."]
        if ultimo:
            linhas.append(f"Último: turno {ultimo['numero']} ({ultimo['operador'] or '?'}), fechado "
                          f"{fmt.fmt_datahora(ultimo['fechado_em'])[:16]} — {_diferenca(ultimo['resultado_cent'])}")
        return "\n".join(linhas)
    res = turnos.resumo(t["id"])
    operador = banco.valor("SELECT nome FROM operadores WHERE id = ?", (t["operador_id"],), "?")
    linhas = [f"💵 Caixa aberto — turno {t['numero']} ({operador})", f"Desde {fmt.fmt_datahora(t['aberto_em'])[:16]}", "",
              f"💰 Vendido no turno: {_brl(res['venda'] + res['servico'] + res['taxa'] - res['desconto'])}",
              f"🧾 Vendas: {res['tc']}  ·  Ticket médio: {_brl(res['tm'])}",
              f"🪙 Dinheiro que deveria estar na gaveta: {_brl(res['esperado'])}"]
    if res["recebimentos"]:
        linhas += ["", "Recebido por forma:"] + [f" • {r['tipo']}: {_brl(r['valor'])}" for r in res["recebimentos"]]
    if res["saidas"] or res["entradas"]:
        linhas += [""] + ([f"💸 Sangrias: {_brl(res['saidas'])}"] if res["saidas"] else []) + \
                  ([f"➕ Suprimentos: {_brl(res['entradas'])}"] if res["entradas"] else [])
    return "\n".join(linhas)


def mais_vendidos(banco, dia: str | None = None, limite: int = 10) -> str:
    dia = dia or dia_atual(banco)
    ini, fim = _faixa(banco, dia)
    linhas = banco.todos(
        """SELECT pr.nome, SUM(i.quantidade) AS qt, SUM(i.total_cent) AS total FROM itens_venda i
           JOIN vendas v ON v.id = i.venda_id JOIN produtos pr ON pr.id = i.produto_id
           WHERE i.cancelado = 0 AND v.status = 'fechada' AND v.fechada_em >= ? AND v.fechada_em < ?
           GROUP BY pr.id ORDER BY total DESC, qt DESC LIMIT ?""", (ini, fim, limite))
    if not linhas:
        return f"🍺 Mais vendidos — {_dia_rotulo(dia)}\n\nNada vendido ainda."
    return "\n".join([f"🍺 Mais vendidos — {_dia_rotulo(dia)}", ""] +
                     [f"{n}. {r['nome']} — {_qtd(r['qt'])} un · {_brl(r['total'])}" for n, r in enumerate(linhas, 1)])


def estoque(banco) -> str:
    sem = [r["nome"] for r in banco.todos(
        "SELECT nome FROM produtos WHERE controla_estoque = 1 AND ativo = 1 AND qt_atual <= 0 ORDER BY nome")]
    ponto = banco.todos(
        "SELECT nome, qt_atual, estoque_minimo FROM produtos WHERE controla_estoque = 1 AND ativo = 1 "
        "AND qt_atual > 0 AND qt_atual <= estoque_minimo ORDER BY (qt_atual / CASE WHEN estoque_minimo > 0 THEN estoque_minimo ELSE 1 END), nome")
    total = banco.valor("SELECT COUNT(*) FROM produtos WHERE controla_estoque = 1 AND ativo = 1", (), 0)
    if not total:
        return "📦 Nenhum produto com controle de estoque ligado."
    linhas = [f"📦 Estoque — {total} produtos controlados", ""]
    if not sem and not ponto:
        return "\n".join(linhas + ["✅ Tudo em dia: nenhum produto zerado ou no ponto de pedido."])
    if sem:
        linhas += [f"🚨 Sem estoque ({len(sem)}):"] + _recortar([f" • {n}" for n in sem]) + [""]
    if ponto:
        linhas += [f"⚠️ Acabando — no ponto de pedido ({len(ponto)}):"] + _recortar(
            [f" • {r['nome']}: {_qtd(r['qt_atual'])} (mín. {_qtd(r['estoque_minimo'])})" for r in ponto])
    return "\n".join(linhas).rstrip()


def abertas(banco) -> str:
    from src.controllers.conferencia_turno import posicoes_abertas
    pos = posicoes_abertas(banco)
    if not pos:
        return "🪑 Nenhuma mesa ou comanda aberta com consumo."
    total = sum(p["total_cent"] for p in pos)
    linhas = [f"🪑 Em aberto agora: {len(pos)} (total {_brl(total)})", ""]
    linhas += _recortar([f" • {p['nome']}: {_brl(p['total_cent'])}" + (" (conta enviada)" if p["status"] == "conta_enviada" else "")
                         for p in sorted(pos, key=lambda p: -p["total_cent"])], 20)
    return "\n".join(linhas)


def cancelamentos(banco, dia: str | None = None) -> str:
    dia = dia or dia_atual(banco)
    ini, fim = _faixa(banco, dia)
    cupons = banco.todos(
        """SELECT v.cupom, v.modalidade, v.comanda, v.posicao, v.subtotal_cent AS total, v.motivo_cancelamento AS motivo,
                  o.nome AS por, v.fechada_em AS quando FROM vendas v LEFT JOIN operadores o ON o.id = v.cancelada_por
           WHERE v.status = 'cancelada' AND v.fechada_em >= ? AND v.fechada_em < ? AND v.subtotal_cent > 0
           ORDER BY v.fechada_em DESC""", (ini, fim))
    itens = banco.todos(
        """SELECT pr.nome, i.quantidade, i.total_cent AS total, i.cancelado_em AS quando, o.nome AS por
           FROM itens_venda i JOIN produtos pr ON pr.id = i.produto_id LEFT JOIN operadores o ON o.id = i.operador_id
           WHERE i.cancelado = 1 AND i.cancelado_em >= ? AND i.cancelado_em < ? ORDER BY i.cancelado_em DESC""", (ini, fim))
    if not cupons and not itens:
        return f"❌ Cancelamentos — {_dia_rotulo(dia)}\n\n✅ Nenhum cancelamento."
    linhas = [f"❌ Cancelamentos — {_dia_rotulo(dia)}", ""]
    if cupons:
        linhas.append(f"Cupons ({len(cupons)}, {_brl(sum(c['total'] for c in cupons))}):")
        linhas += _recortar([f" • {_hora(c['quando'])} cupom {c['cupom']} {_brl(c['total'])} — {c['por'] or '?'}"
                             + (f" — {c['motivo']}" if c["motivo"] else "") for c in cupons], 8)
    if itens:
        linhas += ["", f"Itens ({len(itens)}, {_brl(sum(i['total'] for i in itens))}):"]
        linhas += _recortar([f" • {_hora(i['quando'])} {_qtd(i['quantidade'])}x {i['nome']} {_brl(i['total'])}"
                             + (f" — {i['por']}" if i["por"] else "") for i in itens], 8)
    return "\n".join(linhas)


def ajuda() -> str:
    return ("Sou o bot da sua casa. Toque nos botões aqui embaixo:\n\n"
            "📊 Resumo — vendas da noite até agora\n📅 Ontem — resumo da noite passada\n"
            "💵 Caixa — turno aberto, vendido e dinheiro esperado\n🍺 Mais vendidos — top 10 da noite\n"
            "📦 Estoque — o que zerou ou está acabando\n🪑 Abertas — mesas e comandas em aberto\n"
            "❌ Cancelamentos — cupons e itens cancelados\n\n"
            "Os avisos (abertura/fechamento do caixa, cancelamentos, sangrias) chegam sozinhos.")


# -------------------------------------------------------- avisos de eventos
def _operador(banco, operador_id) -> str:
    return banco.valor("SELECT nome FROM operadores WHERE id = ?", (operador_id,), "?") if operador_id else "?"


def turno_aberto(banco, turno_id: int) -> str:
    t = banco.um("SELECT * FROM turnos WHERE id = ?", (turno_id,))
    return (f"🟢 Caixa aberto — turno {t['numero']}\nOperador: {_operador(banco, t['operador_id'])}\n"
            f"Fundo de caixa: {_brl(t['valor_inicial_cent'])}\n{fmt.fmt_datahora(t['aberto_em'])[:16]}")


def turno_fechado(banco, turno_id: int) -> str:
    """Fechamento: o que vendeu e se o caixa bateu. O operador não vê o 'esperado' na conferência cega; o dono vê."""
    t = banco.um("SELECT * FROM turnos WHERE id = ?", (turno_id,))
    res = TurnoController(banco).resumo(turno_id)
    vendido = res["venda"] + res["servico"] + res["taxa"] - res["desconto"]
    linhas = [f"🔴 Caixa fechado — turno {t['numero']}", f"Operador: {_operador(banco, t['operador_id'])}",
              f"{fmt.fmt_datahora(t['aberto_em'])[:16]} → {fmt.fmt_datahora(t['fechado_em'])[:16]}", "",
              f"💰 Vendido: {_brl(vendido)} em {res['tc']} vendas",
              f"🪙 Dinheiro esperado: {_brl(t['esperado_cent'])}",
              f"🪙 Dinheiro contado: {_brl(t['valor_final_cent'])}",
              f"⚖️ {_diferenca(t['resultado_cent'])}"]
    if res["saidas"]:
        linhas.append(f"💸 Sangrias no turno: {_brl(res['saidas'])}")
    if res["cupons_cancelados"]:
        linhas.append(f"❌ Cupons cancelados no turno: {len(res['cupons_cancelados'])}")
    return "\n".join(linhas)


def venda_cancelada(banco, venda_id: int) -> str:
    v = banco.um("SELECT v.*, o.nome AS por FROM vendas v LEFT JOIN operadores o ON o.id = v.cancelada_por WHERE v.id = ?", (venda_id,))
    local = {"mesa": nome_posicao(v["comanda"], v["posicao"]), "balcao": "balcão", "caderneta": "caderneta"}.get(v["modalidade"], "entrega")
    linhas = [f"❌ Cupom cancelado — {local}", f"Valor: {_brl(v['total_cent'] or v['subtotal_cent'])}  ·  cupom {v['cupom']}",
              f"Por: {v['por'] or '?'}  às {_hora(v['fechada_em'])}"]
    if v["motivo_cancelamento"]:
        linhas.append(f"Motivo: {v['motivo_cancelamento']}")
    else:
        linhas.append("Motivo: não informado")
    return "\n".join(linhas)


def item_cancelado(banco, item_id: int, motivo: str, operador_id) -> str:
    i = banco.um("SELECT i.*, pr.nome AS produto, v.modalidade, v.comanda, v.posicao FROM itens_venda i "
                 "JOIN produtos pr ON pr.id = i.produto_id JOIN vendas v ON v.id = i.venda_id WHERE i.id = ?", (item_id,))
    local = {"mesa": nome_posicao(i["comanda"], i["posicao"]), "balcao": "balcão", "caderneta": "caderneta"}.get(i["modalidade"], "entrega")
    linhas = [f"❌ Item cancelado — {local}", f"{_qtd(i['quantidade'])}x {i['produto']} ({_brl(i['total_cent'])})",
              f"Por: {_operador(banco, operador_id)}"]
    linhas.append(f"Motivo: {motivo}" if motivo else "Motivo: não informado")
    return "\n".join(linhas)


def movimento_caixa(banco, tipo: str, valor_cent: int, descricao: str, operador_id) -> str:
    cab = "💸 Sangria" if tipo == "saida" else "➕ Suprimento"
    linhas = [f"{cab}: {_brl(valor_cent)}", f"Por: {_operador(banco, operador_id)}"]
    if descricao:
        linhas.append(f"Obs.: {descricao}")
    return "\n".join(linhas)


def backup_falhou(banco, erro: str) -> str:
    return f"⚠️ O backup automático do PDV falhou.\n{erro[:200]}\nAbra Utilitários > Backup de dados e confira a pasta/disco."
