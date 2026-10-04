"""Utilitários (manual ADM seção 7): limpeza do movimento, programa de comunicação e backup."""
from __future__ import annotations

from src.core import formatacao as fmt
from src.ui import tema


def executar(master, ctx, chave: str) -> None:
    if chave == "backup":
        ok, caminho = tema.tratar(master, ctx.utilitarios.backup)
        if ok:
            tema.mensagem(master, f"Backup gerado com sucesso:\n{caminho}", "Backup de dados")
    elif chave == "restaurar":
        restaurar(master, ctx)
    elif chave == "suporte":
        ok, caminho = tema.tratar(master, ctx.utilitarios.pacote_suporte)
        if ok:
            tema.mensagem(master, f"Pacote de suporte gerado:\n{caminho}\n\nEnvie este arquivo ao fornecedor. Ele leva só os "
                                  "registros de erro (log), nunca as vendas.", "Pacote de suporte")
    elif chave == "comunicacao":
        tema.tratar(master, ctx.utilitarios.abrir_programa_comunicacao)
    elif chave == "limpeza":
        limpeza(master, ctx)
    elif chave == "fila_impressao":
        from src.ui.fila_impressao_ui import JanelaFilaImpressao
        JanelaFilaImpressao(master, ctx)


def limpeza(master, ctx) -> None:
    padrao = fmt.fmt_data(fmt.hoje()[:8] + "01")
    texto = tema.pedir_texto(
        master, "Limpeza do movimento",
        "Apaga as vendas e movimentos ANTERIORES à data informada.\n"
        "ATENÇÃO: o período apagado termina no dia anterior à data lançada.\n"
        "Recomenda-se manter o último mês (faça os relatórios antes). Um backup é feito automaticamente.\n\n"
        "Apagar tudo anterior a (dd/mm/aaaa):", padrao, largura=16)
    if texto is None:
        return
    try:
        data = fmt.para_data_iso(texto)
    except ValueError as e:
        tema.aviso(master, str(e))
        return
    if data is None:
        return
    conf = tema.pedir_texto(master, "Confirmar limpeza",
                            f"Serão apagadas as vendas anteriores a {fmt.fmt_data(data)}.\nEsta operação não pode ser desfeita "
                            "(exceto restaurando o backup).\n\nDigite APAGAR para confirmar:", largura=16)
    if (conf or "").strip().upper() != "APAGAR":
        return
    ok, res = tema.tratar(master, ctx.utilitarios.limpar_movimento, data)
    if ok:
        tema.mensagem(master, f"Limpeza concluída.\n\nVendas apagadas: {res['vendas']}\nTurnos apagados: {res['turnos']}\n"
                              f"Movimentos de estoque: {res['movimentos_estoque']}\nComissões pagas ou canceladas: {res.get('comissoes', 0)}\n"
                              f"Backup anterior à limpeza:\n{res['backup']}",
                      "Limpeza do movimento")


def restaurar(master, ctx) -> None:
    backups = ctx.utilitarios.listar_backups()
    if not backups:
        tema.aviso(master, "Não há backups nas pastas configuradas.")
        return
    itens = [(str(p), (p.name.removeprefix("loja_offline-").removesuffix(".db"), str(p.parent))) for p in backups[:60]]
    escolhido = tema.escolher(master, "Restaurar backup", itens, "Escolha o backup (mais novos primeiro):", largura=620,
                              colunas=[("data", "Data e hora", 170, "w"), ("pasta", "Pasta", 420, "w")], altura=12)
    if escolhido is None:
        return
    if not tema.confirmar(master, "O sistema volta ao estado deste backup: tudo o que foi lançado DEPOIS dele se perde.\n"
                                  "Uma cópia do estado de agora é guardada antes.\n\nA restauração acontece quando o programa "
                                  "for aberto de novo.\nMarcar a restauração?", "Restaurar backup", padrao_sim=False):
        return
    ok, _ = tema.tratar(master, ctx.utilitarios.pedir_restauracao, escolhido)
    if ok:
        tema.mensagem(master, "Restauração marcada. FECHE o programa e abra de novo para concluir.", "Restaurar backup")
