"""Utilitários (manual ADM seção 7): limpeza do movimento, programa de comunicação e backup."""
from __future__ import annotations

from src.core import formatacao as fmt
from src.ui import tema


def executar(master, ctx, chave: str) -> None:
    if chave == "backup":
        ok, caminho = tema.tratar(master, ctx.utilitarios.backup)
        if ok:
            tema.mensagem(master, f"Backup gerado com sucesso:\n{caminho}", "Backup de dados")
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
                              f"Movimentos de estoque: {res['movimentos_estoque']}\nBackup anterior à limpeza:\n{res['backup']}",
                      "Limpeza do movimento")
