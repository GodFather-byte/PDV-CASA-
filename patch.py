import re

with open('src/ui/main_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import
import_stmt = 'from src.ui.cadastros_ui import criar_tela_cadastros\n'
if import_stmt not in content:
    content = content.replace('from src.controllers.venda_controller import VendaController', 
                              'from src.controllers.venda_controller import VendaController\n' + import_stmt)

# Remove old Admin block
pattern_admin = re.compile(r'# =================================================================\s*# ABA ADMIN.*?\n\s+layout_admin = ft\.Row\(\[\n.*?\n.*?\n\s+\]\)\n', re.DOTALL)
content = pattern_admin.sub('', content)

# Replace the Tab definition
pattern_tab = re.compile(r'ft\.Tab\(text=.Admin \(Cadastros\)., content=ft\.Container\(layout_admin, padding=20\)\)')
content = pattern_tab.sub('ft.Tab(text="Admin (Cadastros)", content=criar_tela_cadastros(page))', content)

with open('src/ui/main_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patch aplicado com sucesso!')
