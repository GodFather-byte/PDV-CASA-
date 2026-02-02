import flet as ft
from src.controllers.produto_controller import ProdutoController
from src.controllers.venda_controller import VendaController

def main(page: ft.Page):
    # --- CONFIGURAÇÃO GERAL ---
    page.title = "PDV Boate - Sistema Completo"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1200
    page.window_height = 800
    page.padding = 10

    # Controladores
    produto_ctrl = ProdutoController()
    venda_ctrl = VendaController()

    # --- ESTADO (Memória da Tela) ---
    estado = {
        "venda_id": venda_ctrl.iniciar_venda(),
        "carrinho": [],
        "total_venda": 0.0
    }

    # =================================================================
    # ABA 1: FRENTE DE CAIXA (O código que já criamos, adaptado)
    # =================================================================
    
    # Componentes do Caixa
    lista_carrinho = ft.ListView(expand=True, spacing=5, auto_scroll=True)
    texto_total = ft.Text("R$ 0.00", size=40, weight="bold", color="green")
    grid_produtos = ft.GridView(expand=True, runs_count=3, max_extent=150, spacing=10, run_spacing=10)

    def atualizar_carrinho_visual():
        lista_carrinho.controls.clear()
        for item in estado["carrinho"]:
            lista_carrinho.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"{item['nome']}", size=14),
                        ft.Text(f"R$ {item['preco']:.2f}", weight="bold")
                    ], alignment="space_between"),
                    padding=5, border=ft.border.only(bottom=ft.border.BorderSide(1, "white10"))
                )
            )
        texto_total.value = f"Total: R$ {estado['total_venda']:.2f}"
        page.update()

    def adicionar_item_venda(e):
        dados = e.control.data
        venda_ctrl.adicionar_item(estado["venda_id"], dados['id'], 1, dados['preco'])
        estado["carrinho"].append({"nome": dados['nome'], "preco": dados['preco']})
        estado["total_venda"] += dados['preco']
        atualizar_carrinho_visual()
        # Feedback visual rápido
        page.snack_bar = ft.SnackBar(ft.Text(f"+ {dados['nome']} adicionado!"), duration=500)
        page.snack_bar.open = True
        page.update()

    def carregar_grid_produtos():
        """Lê do banco e desenha os botões na tela de vendas"""
        grid_produtos.controls.clear()
        produtos = produto_ctrl.listar_todos()
        for p in produtos:
            btn = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.LIQUOR, size=30, color="white54"),
                    ft.Text(p[2], size=14, weight="bold", text_align="center", no_wrap=True), # Nome
                    ft.Text(f"R$ {p[3]:.2f}", color="cyan"), # Preço
                ], alignment="center", horizontal_alignment="center"),
                bgcolor=ft.colors.SURFACE_VARIANT, border_radius=8, padding=10,
                on_click=adicionar_item_venda,
                data={"id": p[0], "nome": p[2], "preco": p[3]},
                ink=True
            )
            grid_produtos.controls.append(btn)
        page.update()

    def finalizar_venda(e):
        # Lógica simplificada para focar na estrutura
        if estado["total_venda"] == 0: return
        venda_ctrl.finalizar_venda(estado["venda_id"], estado["total_venda"], "Dinheiro")
        
        # Reset
        estado["venda_id"] = venda_ctrl.iniciar_venda()
        estado["carrinho"] = []
        estado["total_venda"] = 0.0
        atualizar_carrinho_visual()
        page.snack_bar = ft.SnackBar(ft.Text("Venda Finalizada! 💰"), bgcolor="green")
        page.snack_bar.open = True
        page.update()

    # Layout da Aba Vendas
    layout_vendas = ft.Row([
        ft.Container(grid_produtos, expand=2, padding=10), # Esquerda
        ft.Container( # Direita
            content=ft.Column([
                ft.Text("Caixa Aberto", size=20, weight="bold"),
                ft.Divider(),
                lista_carrinho,
                ft.Divider(),
                texto_total,
                ft.ElevatedButton("RECEBER (F5)", height=60, width=300, bgcolor="blue", color="white", on_click=finalizar_venda)
            ]),
            expand=1, bgcolor=ft.colors.BLACK26, padding=10, border_radius=10
        )
    ], expand=True)

    # =================================================================
    # ABA 2: GESTÃO DE ESTOQUE (ADMINISTRAÇÃO)
    # =================================================================

    # Campos do Formulário
    txt_nome = ft.TextField(label="Nome do Produto", width=300)
    txt_preco = ft.TextField(label="Preço (0.00)", width=150, keyboard_type=ft.KeyboardType.NUMBER)
    txt_cod = ft.TextField(label="Cód. Barras", width=150)
    txt_estoque = ft.TextField(label="Qtd Inicial", width=100, value="0")

    tabela_produtos = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Produto")),
            ft.DataColumn(ft.Text("Preço")),
            ft.DataColumn(ft.Text("Estoque")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[]
    )

    def carregar_tabela_admin():
        tabela_produtos.rows.clear()
        produtos = produto_ctrl.listar_todos()
        for p in produtos:
            tabela_produtos.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(p[0]))),
                    ft.DataCell(ft.Text(p[2])),
                    ft.DataCell(ft.Text(f"R$ {p[3]:.2f}")),
                    ft.DataCell(ft.Text(str(p[4]))),
                    ft.DataCell(ft.IconButton(
                        icon=ft.icons.DELETE, 
                        icon_color="red",
                        tooltip="Excluir (Simulação)",
                        on_click=lambda e: print(f"Deletar {p[0]}") # Futuro: Implementar delete real
                    )),
                ])
            )
        page.update()

    def salvar_produto(e):
        try:
            nome = txt_nome.value
            preco = float(txt_preco.value.replace(",", "."))
            cod = txt_cod.value
            qtd = int(txt_estoque.value)
            
            sucesso, msg = produto_ctrl.cadastrar_produto(nome, preco, cod, qtd)
            
            if sucesso:
                # Limpa campos e atualiza telas
                txt_nome.value = ""
                txt_preco.value = ""
                txt_cod.value = ""
                carregar_tabela_admin() # Atualiza lista da admin
                carregar_grid_produtos() # Atualiza botões do caixa
                page.snack_bar = ft.SnackBar(ft.Text("Produto Salvo!"), bgcolor="green")
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {msg}"), bgcolor="red")
            
            page.snack_bar.open = True
            page.update()

        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Preço ou Estoque inválidos!"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # Layout da Aba Estoque
    layout_admin = ft.Column([
        ft.Text("Cadastro de Produtos", size=25, weight="bold"),
        ft.Row([txt_cod, txt_nome, txt_preco, txt_estoque]),
        ft.ElevatedButton("Salvar Produto", icon=ft.icons.SAVE, on_click=salvar_produto, bgcolor="green", color="white"),
        ft.Divider(),
        ft.Text("Produtos Cadastrados", size=20),
        ft.Container(content=tabela_produtos, height=400, border=ft.border.all(1, "white10"), border_radius=10, padding=10)
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    # =================================================================
    # SISTEMA DE ABAS (Juntando tudo)
    # =================================================================
    
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="Frente de Caixa",
                icon=ft.icons.POINT_OF_SALE,
                content=ft.Container(layout_vendas, padding=10)
            ),
            ft.Tab(
                text="Gerenciar Estoque",
                icon=ft.icons.INVENTORY,
                content=ft.Container(layout_admin, padding=20)
            ),
        ],
        expand=True,
    )

    # Inicialização
    page.add(tabs)
    carregar_grid_produtos()
    carregar_tabela_admin()

if __name__ == "__main__":
    ft.app(target=main)
    
