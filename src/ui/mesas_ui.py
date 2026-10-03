import flet as ft
from src.controllers.mesa_controller import MesaController
from src.core.formatacao import fmt_num

def criar_tela_mesas(page: ft.Page):
    mesa_ctrl = MesaController()
    
    # Header com resumo
    lbl_titulo = ft.Text("MAPA DE MESAS", size=24, weight="bold", color="cyan")
    
    grid_mesas = ft.GridView(
        expand=True,
        runs_count=5, # 5 colunas
        max_extent=150,
        child_aspect_ratio=1.0,
        spacing=10,
        run_spacing=10,
    )
    
    def carregar_mesas():
        grid_mesas.controls.clear()
        
        # Pega as mesas abertas do banco
        mesas_abertas_db = mesa_ctrl.listar_mesas_abertas()
        abertas_map = {m["numero"]: m for m in mesas_abertas_db}
        
        # Vamos renderizar 30 mesas por padrão (exemplo)
        for i in range(1, 31):
            mesa = abertas_map.get(i)
            is_aberta = bool(mesa)
            
            # Cores e textos
            cor_fundo = "blue" if is_aberta else "green"
            texto_status = "Ocupada" if is_aberta else "Livre"
            valor = f"R$ {fmt_num(mesa['total_cent'])}" if is_aberta else ""
            garcom = mesa['garcom_nome'] if is_aberta and mesa['garcom_nome'] else ""
            
            def on_mesa_click(e, numero=i, aberta=is_aberta):
                if aberta:
                    # Mesa aberta: Mostrar modal para adicionar itens ou fechar
                    mostrar_opcoes_mesa(numero)
                else:
                    # Mesa livre: Abrir mesa
                    try:
                        mesa_ctrl.abrir_mesa(numero)
                        page.snack_bar = ft.SnackBar(ft.Text(f"Mesa {numero} aberta!"), bgcolor="green")
                        page.snack_bar.open = True
                        carregar_mesas()
                    except Exception as ex:
                        page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
                        page.snack_bar.open = True
                    page.update()

            card = ft.Container(
                content=ft.Column([
                    ft.Text(f"Mesa {i}", size=20, weight="bold"),
                    ft.Text(texto_status, size=14),
                    ft.Text(valor, size=16, weight="bold", color="yellow" if is_aberta else "transparent"),
                    ft.Text(garcom, size=12, italic=True)
                ], alignment="center", horizontal_alignment="center"),
                bgcolor=cor_fundo,
                border_radius=10,
                padding=10,
                ink=True,
                on_click=on_mesa_click
            )
            grid_mesas.controls.append(card)
            
        page.update()

    def mostrar_opcoes_mesa(numero):
        # Aqui no futuro você integra com a tela do caixa pra lançar produtos
        # Por enquanto vamos dar a opção de Fechar a Mesa
        def fechar(e):
            try:
                # Fictício: Pega a mesa e fecha com Dinheiro
                # Na prática, abriria a aba do Caixa com o VendaID dessa mesa.
                mesa = mesa_ctrl.banco.um("SELECT * FROM mesas WHERE numero = ? AND status = 'aberta'", (numero,))
                if mesa:
                    mesa_ctrl.fechar_mesa(numero, mesa['total_cent'], "Dinheiro")
                    page.snack_bar = ft.SnackBar(ft.Text(f"Mesa {numero} fechada!"), bgcolor="green")
                    page.snack_bar.open = True
                    dlg.open = False
                    carregar_mesas()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
                page.snack_bar.open = True
            page.update()
            
        def transferir(e):
            # Exemplo de transferência simples para Mesa 2
            try:
                mesa_ctrl.transferir_mesa(numero, 2) # Hardcoded p/ teste
                page.snack_bar = ft.SnackBar(ft.Text(f"Transferido para Mesa 2!"), bgcolor="green")
                page.snack_bar.open = True
                dlg.open = False
                carregar_mesas()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
                page.snack_bar.open = True
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Opções da Mesa {numero}"),
            content=ft.Text("O que deseja fazer? (Para lançar itens, volte ao Caixa)"),
            actions=[
                ft.TextButton("Transferir (Teste p/ Mesa 2)", on_click=transferir),
                ft.TextButton("Fechar Conta (Dinheiro)", on_click=fechar),
                ft.TextButton("Cancelar", on_click=lambda e: fechar_modal(dlg))
            ]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()
        
    def fechar_modal(dlg):
        dlg.open = False
        page.update()

    # Carrega inicial
    carregar_mesas()

    return ft.Container(
        content=ft.Column([
            lbl_titulo,
            ft.Divider(),
            grid_mesas,
            ft.Row([
                ft.ElevatedButton("Atualizar Mapa", icon=ft.icons.REFRESH, on_click=lambda e: carregar_mesas())
            ])
        ]),
        padding=20, expand=True
    )
