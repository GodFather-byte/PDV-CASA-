import re

with open('src/controllers/config_controller.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add to CAMPOS_CONFIG
if 'mensagem_rodape' not in content:
    content = content.replace('("num_mesas",', '("mensagem_rodape", "Mensagem de rodape do cupom", "texto", "Impressao"),\n    ("num_mesas",')

with open('src/controllers/config_controller.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('src/controllers/impressao_controller.py', 'r', encoding='utf-8') as f:
    imp = f.read()

# Replace hardcoded message with config
if 'mensagem_rodape' not in imp:
    imp = imp.replace('linhas += ["=" * w, "Obrigado e volte sempre!".center(w)]', 'rodape = self.banco.cfg("mensagem_rodape") or "Obrigado e volte sempre!"\n        linhas += ["=" * w, rodape.center(w)]')
    
with open('src/controllers/impressao_controller.py', 'w', encoding='utf-8') as f:
    f.write(imp)

print('Mensagem de rodape configurada.')

