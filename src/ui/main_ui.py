import flet as ft
# Importa nossos controladores que já estão no Github
from src.controllers.produto_controller import ProdutoController
from src.controllers.venda_controller import VendaController

def main(page: ft.Page):
    # --- 1. CONFIGURAÇÃO DA JANELA ---
    page.title = "PDV Boate - Offline System"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1200
    page.window_height = 800
    page.padding = 20

    # Inicializa a lógica
    produto_ctrl = ProdutoController()
    venda_ctrl = VendaController()
    
    # Estado da Aplicação (Variáveis que mudam)
    estado = {
        "venda_id": venda_ctrl.iniciar_venda(), # Cria a primeira venda no banco
        "total": 0.0,
        "itens": [] # Lista para mostrar na tela
    }

    # --- 2. COMPONENTES VISUAIS (WIDGETS) ---

    # Lista de produtos no carrinho (lado direito)
    lista_carrinho = ft.ListView(expand=True, spacing=5, auto_scroll=True)
    texto_total = ft.Text("R$ 0.00", size=40, weight="bold", color="green")

    # Dropdown para escolher pagamento
    pagamento_dropdown = ft.Dropdown(
        width=200,
        options=[
            ft.dropdown.Option("Dinheiro"),
            ft.dropdown.Option("PIX"),
            ft.dropdown.Option("Cartão Débito"),
            ft.dropdown.Option("Cartão Crédito"),
        ],
        label="Forma de Pagamento"
    )

    # --- 3. FUNÇÕES DE AÇÃO (O QUE O SISTEMA FAZ) ---

    def atualizar_tela():
        """Redesenha a lista de compras e o total"""
        lista_carrinho.controls.clear()
        for item in estado["itens"]:
            # item = {"nome": "Cerveja", "preco": 10.0}
            lista_carrinho.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(item["nome"], size=16),
                        ft.Text(f"R$ {item['preco']:.2f}", weight="bold")
                    ], alignment="space_between"),
                    padding=5,
                    border=ft.border.only(bottom=ft.border.BorderSide(1, "white10"))
                )
            )
        texto_total.value = f"R$ {estado['total']:.2f}"
        page.update()

    def adicionar_produto(e):
        """Chamado quando clica no botão da cerveja/drink"""
        dados = e.control.data # Pega dados escondidos no botão
        
        # 1. Salva no Banco de Dados (Backend)
        venda_ctrl.adicionar_item(estado["venda_id"], dados['id'], 1, dados['preco'])
        
        # 2. Atualiza a Memória Visual (Frontend)
        estado["itens"].append({"nome": dados['nome'], "preco": dados['preco']})
        estado["total"] += dados['preco']
        
        atualizar_tela()

    def confirmar_pagamento(e):
        """Fecha a conta e prepara pro próximo cliente"""
        forma = pagamento_dropdown.value
        if not forma:
            # Se não escolheu pagamento, mostra erro
            page.snack_bar = ft.SnackBar(ft.Text("Selecione a forma de pagamento!"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return

        # 1. Finaliza no Banco
        venda_ctrl.finalizar_venda(estado["venda_id"], estado["total"], forma)
        
        # 2. Fecha o Modal (Janela)
        modal_pagamento.open = False
        
        # 3. Reseta tudo para o próximo cliente
        estado["venda_id"] = venda_ctrl.iniciar_venda()
        estado["total"] = 0.0
        estado["itens"] = []
        pagamento_dropdown.value = None
        
        atualizar_tela()
        
        # 4. Feedback de Sucesso
        page.snack_bar = ft.SnackBar(ft.Text("Venda Finalizada com Sucesso! ✅"), bgcolor="green")
        page.snack_bar.open = True
        page.update()

    # --- 4. O MODAL (JANELA DE PAGAMENTO) ---
    modal_pagamento = ft.AlertDialog(
        title=ft.Text("Finalizar Venda"),
        content=ft.Column([
            ft.Text("Confirme o valor total:", size=16),
            texto_total, # Mostra o valor grandão
            pagamento_dropdown
        ], height=150),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.close_dialog()),
            ft.ElevatedButton("Confirmar Recebimento", on_click=confirmar_pagamento, bgcolor="green", color="white")
        ],
    )

    def abrir_pagamento(e):
        if estado["total"] == 0:
            return # Não abre se a conta for zero
        page.dialog = modal_pagamento
        modal_pagamento.open = True
        page.update()

    # --- 5. MONTAGEM DO GRID DE PRODUTOS ---
    grid_produtos = ft.GridView(
        expand=True, runs_count=3, max_extent=150, spacing=10, run_spacing=10
    )

    # Busca produtos reais do banco
    lista_db = produto_ctrl.listar_todos()
    
    # Se o banco estiver vazio (primeira vez), cria botões de teste
    if not lista_db:
        lista_db = [
            (1, "001", "Heineken", 15.0, 100),
            (2, "002", "Vodka Dose", 25.0, 100),
            (3, "003", "Água", 5.0, 100),
            (4, "004", "Red Bull", 20.0, 100),
            (5, "005", "Gin Tônica", 35.0, 100),
        ]

    for p in lista_db:
        # Cria um botão para cada produto
        btn = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.LOCAL_BAR, size=30, color="white54"),
                ft.Text(p[2], size=16, weight="bold", text_align="center"),
                ft.Text(f"R$ {p[3]:.2f}", color="cyan"),
            ], alignment="center", horizontal_alignment="center"),
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=8,
            padding=10,
            on_click=adicionar_produto,
            data={"id": p[0], "nome": p[2], "preco": p[3]}, # Guarda dados no botão
            ink=True
        )
        grid_produtos.controls.append(btn)

    # --- 6. LAYOUT FINAL ---
    page.add(
        ft.Row([
            # Coluna Esquerda: Produtos
            ft.Container(grid_produtos, expand=2, padding=10),
            
            # Coluna Direita: Caixa
            ft.Container(
                content=ft.Column([
                    ft.Text("Cupom Atual", size=20, weight="bold"),
                    ft.Divider(),
                    lista_carrinho, # Lista de itens
                    ft.Divider(),
                    ft.Row([ft.Text("Total:", size=20), texto_total], alignment="spaceBetween"),
                    ft.ElevatedButton("RECEBER (F5)", height=60, width=300, bgcolor="blue", color="white", on_click=abrir_pagamento)
                ]),
                expand=1, bgcolor=ft.colors.BLACK26, padding=20, border_radius=10
            )
        ], expand=True)
    )

ft.app(target=main)
