import flet as ft
from src.controllers.entidades import ENTIDADES
from src.controllers.cadastro_controller import CadastroController

def criar_tela_cadastros(page: ft.Page):
    """Cria a interface dinâmica de cadastros baseada nas ENTIDADES."""
    cad_ctrl = CadastroController()

    # Dropdown para escolher qual entidade gerenciar (Ex: Produtos, Operadores, Clientes)
    combo_entidades = ft.Dropdown(
        label="Selecione o Cadastro",
        options=[ft.dropdown.Option(key=k, text=v.titulo) for k, v in ENTIDADES.items()],
        width=400,
        autofocus=True
    )

    # Container onde o formulário dinâmico será renderizado
    form_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    lista_registros = ft.ListView(expand=True, spacing=5, auto_scroll=True)

    def carregar_registros(chave_entidade):
        lista_registros.controls.clear()
        entidade = ENTIDADES[chave_entidade]
        registros = cad_ctrl.banco.todos(f"SELECT * FROM {entidade.tabela}")

        for reg in registros:
            reg_dict = dict(reg)
            # Tenta pegar o nome ou texto principal para exibir
            nome_exibicao = reg_dict.get("nome") or reg_dict.get("descricao") or reg_dict.get("tipo") or reg_dict.get("id")

            def deletar(e, reg_id=reg_dict["id"]):
                try:
                    cad_ctrl.excluir(chave_entidade, reg_id)
                    carregar_registros(chave_entidade)
                    page.snack_bar = ft.SnackBar(ft.Text("Excluído com sucesso!"), bgcolor="green")
                    page.snack_bar.open = True
                    page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()

            lista_registros.controls.append(
                ft.ListTile(
                    title=ft.Text(str(nome_exibicao)),
                    subtitle=ft.Text(f"ID: {reg_dict['id']}"),
                    trailing=ft.IconButton(ft.icons.DELETE, icon_color="red", on_click=deletar)
                )
            )
        page.update()

    def montar_formulario(e):
        chave = combo_entidades.value
        if not chave: return

        entidade = ENTIDADES[chave]
        form_container.controls.clear()

        campos_ui = {}
        for campo in entidade.campos:
            if campo.nome == "id": continue

            if campo.tipo == "sn": # Sim/Não
                ctrl = ft.Switch(label=campo.rotulo, value=bool(campo.padrao))
            elif campo.tipo == "escolha":
                ctrl = ft.Dropdown(
                    label=campo.rotulo,
                    options=[ft.dropdown.Option(key=str(k), text=str(v)) for k, v in (campo.opcoes or [])]
                )
            elif campo.tipo == "senha":
                ctrl = ft.TextField(label=campo.rotulo, password=True, can_reveal_password=True)
            else:
                ctrl = ft.TextField(label=campo.rotulo)

            campos_ui[campo.nome] = ctrl
            form_container.controls.append(ctrl)

        def salvar_form(e):
            valores = {}
            for k, ctrl in campos_ui.items():
                if isinstance(ctrl, ft.Switch):
                    valores[k] = 1 if ctrl.value else 0
                else:
                    valores[k] = ctrl.value

            try:
                cad_ctrl.salvar(chave, valores)
                page.snack_bar = ft.SnackBar(ft.Text("Salvo com sucesso!"), bgcolor="green")
                page.snack_bar.open = True
                carregar_registros(chave)

                # Limpa o form
                for ctrl in campos_ui.values():
                    if isinstance(ctrl, ft.Switch): ctrl.value = False
                    elif isinstance(ctrl, ft.TextField): ctrl.value = ""
                    elif isinstance(ctrl, ft.Dropdown): ctrl.value = None
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
                page.snack_bar.open = True
                page.update()

        btn_salvar = ft.ElevatedButton("Salvar", on_click=salvar_form, bgcolor="blue", color="white")
        form_container.controls.append(btn_salvar)

        carregar_registros(chave)
        page.update()

    combo_entidades.on_change = montar_formulario

    return ft.Row([
        ft.Container(
            content=ft.Column([
                ft.Text("CADASTROS E CONFIGURAÇÕES", size=20, weight="bold"),
                combo_entidades,
                ft.Divider(),
                form_container
            ]),
            expand=1, padding=20
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("REGISTROS SALVOS", size=20, weight="bold"),
                ft.Divider(),
                lista_registros
            ]),
            expand=1, padding=20, bgcolor=ft.colors.BLACK26
        )
    ], expand=True)
