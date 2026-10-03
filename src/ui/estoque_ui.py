import flet as ft
from src.controllers.estoque_controller import EstoqueController
from src.controllers.cadastro_controller import CadastroController

def criar_tela_estoque(page: ft.Page):
    est_ctrl = EstoqueController()
    cad_ctrl = CadastroController()
    
    # Estados
    produtos_cadastrados = [dict(p) for p in cad_ctrl.banco.todos("SELECT id, codigo, nome FROM produtos ORDER BY nome")]
    
    lbl_titulo = ft.Text("MOVIMENTAÇÕES DE ESTOQUE", size=24, weight="bold", color="orange")
    
    dd_tipo = ft.Dropdown(
        label="Tipo de Movimentação",
        options=[
            ft.dropdown.Option("inicial", "Inicial (Configurar saldo)"),
            ft.dropdown.Option("compra", "Compra (Nota Fiscal)"),
            ft.dropdown.Option("entrada", "Entrada (Devolução/Avulsa)"),
            ft.dropdown.Option("saida", "Saída (Transferência/Avulsa)"),
            ft.dropdown.Option("descarte", "Descarte (Perdas)"),
            ft.dropdown.Option("contagem", "Contagem (Inventário)")
        ],
        width=300
    )
    
    dd_produto = ft.Dropdown(
        label="Produto",
        options=[ft.dropdown.Option(str(p["id"]), p["nome"]) for p in produtos_cadastrados],
        width=400,
        searchable=True
    )
    
    txt_qtd = ft.TextField(label="Quantidade", width=150)
    txt_valor = ft.TextField(label="Valor Total (R$) p/ Compras", width=200, value="0.00")
    
    historico_list = ft.ListView(expand=True, spacing=5)
    
    def carregar_historico():
        historico_list.controls.clear()
        movs = est_ctrl.banco.todos("SELECT m.*, p.nome FROM movimentos_estoque m JOIN produtos p ON m.produto_id = p.id ORDER BY m.criado_em DESC LIMIT 20")
        for m in movs:
            historico_list.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.COMPARE_ARROWS),
                    title=ft.Text(f"{m['nome']} - {m['tipo'].upper()}"),
                    subtitle=ft.Text(f"Qtd: {m['quantidade']} | Saldo após: {m['qt_apos']}")
                )
            )
        page.update()

    def salvar_movimento(e):
        if not dd_tipo.value or not dd_produto.value or not txt_qtd.value:
            page.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos obrigatórios."), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return
            
        try:
            qtd = float(txt_qtd.value.replace(",", "."))
            valor_cent = int(float(txt_valor.value.replace(",", ".")) * 100)
            
            # Cria o lancamento mestre
            lanc_id = est_ctrl.criar_lancamento(
                tipo=dd_tipo.value,
                operador_id=1, # Ficticio para teste
                documento=f"Mov {dd_tipo.value}",
                observacao="Movimento manual via UI"
            )
            
            # Adiciona o item
            est_ctrl.adicionar_item(
                lanc_id=lanc_id,
                produto_id=int(dd_produto.value),
                quantidade=qtd,
                valor_cent=valor_cent,
                desconto_cent=0
            )
            
            page.snack_bar = ft.SnackBar(ft.Text("Movimentação registrada com sucesso!"), bgcolor="green")
            page.snack_bar.open = True
            carregar_historico()
            
            txt_qtd.value = ""
            txt_valor.value = "0.00"
            page.update()
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            
    btn_salvar = ft.ElevatedButton("Lançar Movimento", on_click=salvar_movimento, bgcolor="green", color="white")

    carregar_historico()

    return ft.Row([
        ft.Container(
            content=ft.Column([
                lbl_titulo,
                ft.Text("Registre entradas, compras e perdas aqui para manter o C.M.V. correto."),
                dd_tipo,
                dd_produto,
                ft.Row([txt_qtd, txt_valor]),
                btn_salvar
            ]),
            expand=1, padding=20
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("ÚLTIMOS MOVIMENTOS", weight="bold"),
                ft.Divider(),
                historico_list
            ]),
            expand=1, padding=20, bgcolor=ft.colors.BLACK26
        )
    ], expand=True)
