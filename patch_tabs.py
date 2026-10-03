import re

with open('src/ui/main_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_stmt1 = 'from src.ui.estoque_ui import criar_tela_estoque\n'
import_stmt2 = 'from src.ui.caderneta_ui import criar_tela_caderneta\n'

if import_stmt1 not in content:
    content = content.replace('from src.ui.mesas_ui import criar_tela_mesas', 
                              'from src.ui.mesas_ui import criar_tela_mesas\n' + import_stmt1 + import_stmt2)

# Add the tabs
if 'ft.Tab(text="Estoque"' not in content:
    pattern_tabs = re.compile(r'(ft\.Tab\(text="Mesas \(Comandas\)", content=criar_tela_mesas\(page\)\))')
    replacement = r'\1,\n            ft.Tab(text="Lançamentos (Estoque)", content=criar_tela_estoque(page)),\n            ft.Tab(text="Caderneta (Fiado)", content=criar_tela_caderneta(page))'
    content = pattern_tabs.sub(replacement, content)

with open('src/ui/main_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patch Estoque/Caderneta aplicado com sucesso!')
