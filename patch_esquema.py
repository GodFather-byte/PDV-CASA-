with open('src/database/esquema.py', 'r', encoding='utf-8') as f:
    content = f.read()

mesas_table = '''    """CREATE TABLE IF NOT EXISTS mesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER NOT NULL UNIQUE,
        status TEXT DEFAULT 'fechada',
        venda_id INTEGER,
        garcom_id INTEGER,
        total_cent INTEGER DEFAULT 0,
        servico_cent INTEGER DEFAULT 0
    )""",
'''

if 'CREATE TABLE IF NOT EXISTS mesas' not in content:
    content = content.replace('TABELAS = [', 'TABELAS = [\n' + mesas_table)
    with open('src/database/esquema.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Tabela mesas injetada com sucesso.')
else:
    print('Tabela mesas ja existe.')
