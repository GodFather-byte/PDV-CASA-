import flet as ft
from src.database.conexao import get_banco
from src.core.formatacao import fmt_num

def criar_tela_caderneta(page: ft.Page):
    banco = get_banco()
    
    lbl_titulo = ft.Text("CADERNETA (FIADO)", size=24, weight="bold", color="red")
    
    clientes_list = ft.ListView(expand=True, spacing=5)
    
    def carregar_clientes():
        clientes_list.controls.clear()
        clientes = banco.todos("SELECT * FROM clientes WHERE ativo = 1 ORDER BY nome")
        
        for c in clientes:
            saldo = c['saldo_cent'] or 0
            cor_saldo = "red" if saldo < 0 else "green"
            texto_saldo = f"Dívida: R$ {fmt_num(abs(saldo))}" if saldo < 0 else f"Crédito: R$ {fmt_num(saldo)}"
            
            def pagar_conta(e, cid=c['id']):
                # Simula pagamento de conta
                try:
                    valor_pago_cent = 5000 # R$ 50.00 fixo para teste
                    with banco.transacao():
                        banco.executar("UPDATE clientes SET saldo_cent = saldo_cent + ? WHERE id = ?", (valor_pago_cent, cid))
                    page.snack_bar = ft.SnackBar(ft.Text(f"Pagamento de R$ 50,00 registrado!"), bgcolor="green")
                    page.snack_bar.open = True
                    carregar_clientes()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
                    page.snack_bar.open = True
                page.update()

            clientes_list.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.ACCOUNT_CIRCLE),
                    title=ft.Text(c['nome'], weight="bold"),
                    subtitle=ft.Text(texto_saldo, color=cor_saldo),
                    trailing=ft.ElevatedButton("Receber Pagamento (Simular R$ 50)", on_click=pagar_conta)
                )
            )
        page.update()

    carregar_clientes()

    return ft.Container(
        content=ft.Column([
            lbl_titulo,
            ft.Text("Gerencie aqui as contas dos clientes que compram fiado. O limite pode ser configurado na aba de Cadastros."),
            ft.Divider(),
            clientes_list
        ]),
        padding=20, expand=True
    )
