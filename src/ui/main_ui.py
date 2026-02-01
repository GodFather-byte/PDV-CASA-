import flet as ft
from src.controllers.produto_controller import ProdutoController
from src.controllers.venda_controller import VendaController

def main(page: ft.Page):
    # 1. Configuração da Janela (Estilo Boate)
    page.title = "PDV Boate - Sistema Offline"
    page.theme_mode = ft.ThemeMode.DARK # Modo escuro obrigatório pra boate
    page.padding = 20
    page.window_width = 1000
    page.window_height = 800

    # Inicializa os controladores
    produto_ctrl = ProdutoController()
    venda_ctrl = VendaController()
    
    # Variável para controlar a venda atual
    venda_atual_id = venda_ctrl.iniciar_venda()
    carrinho_lista = []

    # --- ELEMENTOS DA TELA ---

    # Lista visual do carrinho (O cupom na tela)
    lista_carrinho = ft.ListView(expand=True, spacing=10)
    total_texto = ft.Text("Total: R$ 0.00", size=30, weight="bold", color="green")

    def atualizar_carrinho():
        lista_carrinho.controls.clear()
        total = 0
        for item in carrinho_lista:
            # item = (nome, preco)
            lista_carrinho.controls.append(
                ft.Text(f"{item[0]} - R$ {item[1]:.2f}", size=18)
            )
            total += item[1]
        total_texto.value = f"Total: R$ {total:.2f}"
        page.update()

    def adicionar_produto(e):
        # O botão guarda o ID e Preço no 'data'
        dados = e.control.data # Ex: {"id": 1, "nome": "Cerveja", "preco": 10.0}
        
        # Adiciona no Backend
        venda_ctrl.adicionar_item(venda_atual_id, dados['id'], 1, dados['preco'])
        
        # Adiciona na Tela
        carrinho_lista.append((dados['nome'], dados['preco']))
        atualizar_carrinho()

    # --- LAYOUT DOS PRODUTOS (Grade de Botões) ---
    grid_produtos = ft.GridView(
        expand=True,
        max_extent=150, # Tamanho do botão
        child_aspect_ratio=1.0, # Quadrado
        spacing=10,
        run_spacing=10,
    )

    # Carrega produtos do banco e cria botões
    produtos = produto_ctrl.listar_todos() 
    # Se não tiver produtos, cria uns falsos pra você ver o layout
    if not produtos:
        produtos = [
            (1, "789", "Heineken", 15.00, 100),
            (2, "790", "Água", 5.00, 100),
            (3, "791", "Combo Vodka", 150.00, 50),
            (4, "792", "Red Bull", 20.00, 80),
        ]

    for p in produtos:
        # p = (id, codigo, nome, preco, estoque) - Ajuste conforme seu banco
        botao = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.LIQUOR, size=40, color="white"),
                ft.Text(p[2], size=16, weight="bold"),
                ft.Text(f"R$ {p[3]:.2f}", color="yellow"),
            ], alignment="center", horizontal_alignment="center"),
            bgcolor=ft.colors.BLUE_GREY_800,
            border_radius=10,
            padding=10,
            on_click=adicionar_produto,
            data={"id": p[0], "nome": p[2], "preco": p[3]}, # Guarda os dados no botão
            ink=True, # Efeito de clique visual
        )
        grid_produtos.controls.append(botao)

    # --- MONTAGEM FINAL DA TELA ---
    
    # Coluna da Esquerda (Produtos)
    coluna_produtos = ft.Container(
        content=grid_produtos,
        expand=2, # Ocupa 2/3 da tela
        padding=10,
        border=ft.border.all(1, ft.colors.WHITE24),
        border_radius=10
    )

    # Coluna da Direita (Caixa/Pagamento)
    coluna_caixa = ft.Container(
        content=ft.Column([
            ft.Text("Cupom Fiscal", size=20, weight="bold"),
            ft.Divider(),
            lista_carrinho,
            ft.Divider(),
            total_texto,
            ft.ElevatedButton("Finalizar Venda (F5)", bgcolor="green", color="white", height=50, width=200)
        ]),
        expand=1, # Ocupa 1/3 da tela
        padding=10,
        bgcolor=ft.colors.BLACK54,
        border_radius=10
    )

    # Adiciona tudo na página (Linha dividindo as duas colunas)
    page.add(
        ft.Row([coluna_produtos, coluna_caixa], expand=True)
    )

# Roda o app como Desktop
ft.app(target=main)
