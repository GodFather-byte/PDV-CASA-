import re

with open('src/ui/main_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_stmt = 'from src.ui.mesas_ui import criar_tela_mesas\n'
if import_stmt not in content:
    content = content.replace('from src.ui.cadastros_ui import criar_tela_cadastros', 
                              'from src.ui.cadastros_ui import criar_tela_cadastros\n' + import_stmt)

# Add the Mesas tab
if 'ft.Tab(text="Mesas (Comandas)"' not in content:
    pattern_tabs = re.compile(r'(ft\.Tab\(text="Admin \(Cadastros\)", content=criar_tela_cadastros\(page\)\))')
    replacement = r'\1,\n            ft.Tab(text="Mesas (Comandas)", content=criar_tela_mesas(page))'
    content = pattern_tabs.sub(replacement, content)

with open('src/ui/main_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patch de Mesas aplicado com sucesso!')
