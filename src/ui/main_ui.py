import flet as ft
from src.controllers.produto_controller import ProdutoController
from src.controllers.venda_controller import VendaController

def main(page: ft.Page):
    page.title = "PDV Profissional - Boate"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1200
    page.window_height = 800
    page.padding = 15

    # Controladores
    produto_ctrl = ProdutoController()
    venda_ctrl = VendaController()

    # Estado
    estado = {
        "venda_id": venda_ctrl.iniciar_venda(),
        "total_venda": 0.0,
        "carrinho": [],
        "produto_atual": None # Guarda o produto que está na "pré-visualização"
    }

    # =================================================================
    # ELEMENTOS VISUAIS (WIDGETS)
    # =================================================================

    # 1. ÁREA DE BUSCA (TOPO)
    txt_codigo = ft.TextField(
        label="Código do Produto (F1)", 
        text_size=20, 
        width=200, 
        autofocus=True,
        border_color="blue"
    )
    
    txt_quantidade = ft.TextField(
        label="Qtd", 
        value="1", 
        text_size=20, 
        width=100,
        text_align="center",
        disabled=True # Começa travado até achar um produto
    )

    # 2. ÁREA DE PRÉ-VISUALIZAÇÃO (Onde aparece "SKOL" grande antes de vender)
    lbl_nome_produto = ft.Text("Aguardando código...", size=30, weight="bold", color="white24")
    lbl_preco_unitario = ft.Text("R$ 0,00", size=20, color="white24")
    
    # Cartão que destaca o produto encontrado
    card_preview = ft.Container(
        content=ft.Column([
            ft.Text("PRÉ-VISUALIZAÇÃO", size=12, color="grey"),
            lbl_nome_produto,
            lbl_preco_unitario
        ], alignment="center", horizontal_alignment="center"),
        padding=20,
        bgcolor=ft.colors.BLACK45,
        border=ft.border.all(1, "white10"),
        border_radius=10,
        width=400
    )

    # 3. LISTA DE COMPRAS (O Cupom)
    lista_carrinho = ft.ListView(expand=True, spacing=5, auto_scroll=True)
    lbl_total_final = ft.Text("R$ 0.00", size=45, weight="bold", color="green")

    # =================================================================
    # LÓGICA DO SISTEMA
    # =================================================================

    def atualizar_lista_visual():
        lista_carrinho.controls.clear()
        for item in estado["carrinho"]:
            lista_carrinho.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"{item['qtd']}x {item['nome']}", size=16),
                        ft.Text(f"R$ {item['total']:.2f}", weight="bold")
                    ], alignment="space_between"),
                    padding=5,
                    border=ft.border.only(bottom=ft.border.BorderSide(1, "white10"))
                )
            )
        lbl_total_final.value = f"Total: R$ {estado['total_venda']:.2f}"
        page.update()

    def resetar_busca():
        """Limpa os campos para o próximo item"""
        estado["produto_atual"] = None
        txt_codigo.value = ""
        txt_quantidade.value = "1"
        txt_quantidade.disabled = True
        
        lbl_nome_produto.value = "Aguardando código..."
        lbl_nome_produto.color = "white24"
        lbl_preco_unitario.value = "R$ 0,00"
        
        txt_codigo.focus() # Volta o foco para o código
        page.update()

    def confirmar_venda_item(e):
        """Passo 2: Adiciona ao carrinho quando aperta ENTER na Quantidade"""
        p = estado["produto_atual"]
        if not p:
            return

        try:
            qtd = int(txt_quantidade.value)
            if qtd < 1: qtd = 1
        except:
            qtd = 1

        valor_total_item = p[3] * qtd # Preço * Qtd

        # Backend (Salva no Banco)
        venda_ctrl.adicionar_item(estado["venda_id"], p[0], qtd, p[3])

        # Frontend (Atualiza Tela)
        estado["carrinho"].append({
            "nome": p[2], 
            "qtd": qtd, 
            "total": valor_total_item
        })
        estado["total_venda"] += valor_total_item
        
        atualizar_lista_visual()
        
        # Feedback sonoro/visual
        page.snack_bar = ft.SnackBar(ft.Text(f"✅ {qtd}x {p[2]} Lançado!"), bgcolor="green", duration=500)
        page.snack_bar.open = True
        
        resetar_busca()

    def buscar_produto(e):
        """Passo 1: Busca o produto quando aperta ENTER no Código"""
        cod = txt_codigo.value.strip()
        if not cod: return

        produto = produto_ctrl.buscar_por_codigo(cod)
        # produto = (id, codigo, nome, preco, estoque)

        if produto:
            # Achou! Mostra na tela
            estado["produto_atual"] = produto
            
            lbl_nome_produto.value = produto[2] # Nome
            lbl_nome_produto.color = "white"
            lbl_preco_unitario.value = f"Unitário: R$ {produto[3]:.2f}"
            
            # Destrava quantidade e joga o foco lá
            txt_quantidade.disabled = False
            txt_quantidade.focus()
            page.update()
        else:
            # Não achou
            page.snack_bar = ft.SnackBar(ft.Text("❌ Produto não encontrado!"), bgcolor="red")
            page.snack_bar.open = True
            txt_codigo.value = ""
            txt_codigo.focus()
            page.update()

    # Linka os ENTERs
    txt_codigo.on_submit = buscar_produto
    txt_quantidade.on_submit = confirmar_venda_item

    # =================================================================
    # ABA ADMIN (Para cadastrar produtos de teste)
    # =================================================================
    txt_adm_nome = ft.TextField(label="Nome (Ex: Skol)")
    txt_adm_cod = ft.TextField(label="Código (Ex: 2)", width=100)
    txt_adm_preco = ft.TextField(label="Preço (Ex: 8.00)", width=100)

    def salvar_produto(e):
        try:
            produto_ctrl.cadastrar_produto(
                txt_adm_nome.value, 
                float(txt_adm_preco.value.replace(",", ".")), 
                txt_adm_cod.value, 
                100
            )
            page.snack_bar = ft.SnackBar(ft.Text("Salvo!"), bgcolor="green")
            page.snack_bar.open = True
            page.update()
        except: pass

    layout_admin = ft.Row([
        txt_adm_cod, txt_adm_nome, txt_adm_preco,
        ft.ElevatedButton("Cadastrar", on_click=salvar_produto)
    ])

    # =================================================================
    # LAYOUT FINAL
    # =================================================================
    
    coluna_esquerda = ft.Container(
        content=ft.Column([
            ft.Text("CAIXA OPERACIONAL", size=20, weight="bold", color="cyan"),
            ft.Divider(),
            ft.Row([txt_codigo, txt_quantidade], alignment="center"),
            ft.Container(height=20), # Espaço
            card_preview, # AQUI APARECE A SKOL
            ft.Container(height=20),
            ft.ElevatedButton("CONFIRMAR ITEM (Enter)", width=400, height=50, bgcolor="blue", color="white", on_click=confirmar_venda_item)
        ], horizontal_alignment="center"),
        expand=1, padding=20, bgcolor=ft.colors.BLACK26
    )

    coluna_direita = ft.Container(
        content=ft.Column([
            ft.Text("CUPOM ATUAL", weight="bold"),
            ft.Divider(),
            lista_carrinho,
            ft.Divider(),
            lbl_total_final,
            ft.ElevatedButton("FECHAR CONTA (F5)", bgcolor="red", color="white", height=60, width=300)
        ]),
        expand=1, padding=20, bgcolor=ft.colors.BLACK38, border_radius=10
    )

    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Caixa", content=ft.Row([coluna_esquerda, coluna_direita], expand=True)),
            ft.Tab(text="Admin (Cadastros)", content=ft.Container(layout_admin, padding=20))
        ]
    )

    page.add(tabs)

if __name__ == "__main__":
    ft.app(target=main)
    
