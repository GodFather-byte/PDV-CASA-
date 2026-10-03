"""Dados iniciais: operador ADM, plano de contas modelo, formas de pagamento,
níveis de acesso e configuração padrão. Tudo pode ser editado depois pelo sistema."""
from __future__ import annotations

import socket

from src.core import formatacao as fmt
from src.core import seguranca

# (módulo, descrição, grupo, nível mínimo). O nível 0 (caixa) não aparece: é o padrão de todos.
ACESSOS = [
    ("cad_unidades", "Cadastro de Unidades", "Cadastros", 2),
    ("cad_grupos", "Cadastro de Grupos", "Cadastros", 2),
    ("cad_subgrupos", "Cadastro de Subgrupos", "Cadastros", 2),
    ("cad_produtos", "Cadastro de Produtos", "Cadastros", 2),
    ("cad_observacoes", "Observações de Produtos", "Cadastros", 2),
    ("cad_composicao", "Composição (ficha técnica)", "Cadastros", 3),
    ("cad_cargos", "Cadastro de Cargos", "Cadastros", 3),
    ("cad_operadores", "Cadastro de Operadores", "Cadastros", 4),
    ("cad_fornecedores", "Cadastro de Fornecedores", "Cadastros", 2),
    ("cad_clientes", "Cadastro de Clientes", "Cadastros", 1),
    ("cad_bairros", "Bairros e taxas de entrega", "Cadastros", 2),
    ("cad_tipos_pagamento", "Tipos de Pagamento", "Cadastros", 3),
    ("cad_plano_contas", "Plano de Contas", "Cadastros", 3),
    ("cad_subplanos", "Sub Planos", "Cadastros", 3),
    ("cad_aliquotas", "Alíquotas", "Cadastros", 3),
    ("caixa_cancelamento", "Cancelar itens/vendas no caixa", "Caixa", 2),
    ("caixa_sangria", "Sangria / entradas e saídas do caixa", "Caixa", 2),
    ("caixa_gaveta", "Abrir gaveta", "Caixa", 1),
    ("caixa_desconto", "Conceder desconto", "Caixa", 1),
    ("lanc_contas", "Lançamento de Contas", "Lançamentos", 2),
    ("lanc_estoque", "Lançamento de Estoque", "Lançamentos", 2),
    ("lanc_contagem", "Contagem / inventário de estoque", "Lançamentos", 3),
    ("rel_vendas", "Relatório Venda no Período", "Relatórios", 2),
    ("rel_vendas_grupo", "Relatório Venda por Grupo", "Relatórios", 2),
    ("rel_caixa", "Entradas/Saídas financeiras e Fechamentos", "Relatórios", 2),
    ("rel_comandas", "Relatório de Comandas", "Relatórios", 2),
    ("rel_garcons", "Relatório de Garçons", "Relatórios", 2),
    ("rel_cmv", "Relatório C.M.V.", "Relatórios", 3),
    ("rel_clientes", "Clientes inativos e Clientes", "Relatórios", 2),
    ("rel_comissoes", "Relatórios de Comissões", "Relatórios", 3),
    ("rel_financeiro", "Resultado financeiro e Extrato de contas", "Relatórios", 3),
    ("rel_estoque", "Estoque atual e Movimento de estoque", "Relatórios", 2),
    ("rel_informativos", "Informativo, Horas, Cancelados, Custo médio", "Relatórios", 2),
    ("util_limpeza", "Limpeza do movimento", "Utilitários", 4),
    ("util_comunicacao", "Programa de comunicação", "Utilitários", 2),
    ("util_backup", "Backup de dados", "Utilitários", 2),
    ("util_fila_impressao", "Fila de impressão", "Utilitários", 2),
    ("cfg_acessos", "Configurar níveis de acesso", "Configurações", 4),
    ("cfg_loja", "Dados da Loja", "Configurações", 3),
    ("cfg_configuracoes", "Configurações operacionais", "Configurações", 4),
    ("cfg_maquinas", "Máquinas", "Configurações", 4),
]

CONFIG_PADRAO = {
    "num_mesas": "50", "cobra_servico_mesa": "S", "servico_pct": "10",
    "num_comandas": "10000", "cobra_servico_comanda": "S", "painel_mesas_fixo": "S", "posicao_padrao": "comanda",
    "controle_garcom": "N", "comissao_garcom_pct": "0",
    "tempo_inatividade_min": "30", "num_turnos": "3", "pergunta_pessoas": "N",
    "exigir_senha_gaveta": "S", "exigir_senha_sangria": "S",
    "exigir_senha_cancelamento": "S", "exigir_senha_desconto": "N",
    "imprimir_cupom": "S", "terminal": "1",
    "chave_loja": "", "licenca_ativa": "1",
    "api_url": "", "api_token": "", "sync_intervalo_seg": "60",
    "programa_comunicacao": "", "pasta_backup": "",
    "email_loja": "", "email_destino": "", "smtp_servidor": "",
}

CARGOS = ["Administrador", "Gerente", "Caixa", "Garçom", "Entregador", "Vendedor"]

UNIDADES = [("Unidade", "UN"), ("Quilo", "KG"), ("Litro", "LT"), ("Dose", "DS"),
            ("Pacote", "PCT"), ("Metro", "MT")]

ALIQUOTAS = [("ISENTO", 0, "II"), ("SUBSTITUIÇÃO TRIBUTÁRIA", 0, "FF"),
             ("7%", 7, "0700"), ("12%", 12, "1200"), ("18%", 18, "1800")]

# (tipo, ordem, permite_troco, emite_vale, na_gaveta). Dinheiro sempre na primeira posição.
# Cartão e Pix não ficam na gaveta: o operador confere na maquininha, não contando dinheiro.
TIPOS_PAGAMENTO = [("Dinheiro", 1, 1, 0, 1), ("Cheque", 2, 0, 0, 1), ("Ticket", 3, 0, 1, 1),
                   ("Contra Vale", 4, 0, 1, 1), ("Cartão Débito", 5, 0, 0, 0),
                   ("Cartão Crédito", 6, 0, 0, 0), ("Pix", 7, 0, 0, 0)]

# (nome, código, débito(1=saída), afeta_resultado, [subplanos])
PLANOS = [
    ("Vendas (+)", "1.01", 0, 1, ["Vendas"]),
    ("Outros Créditos (+)", "1.02", 0, 1, ["Outros Créditos"]),
    ("Mercadorias (-)", "2.01", 1, 1, ["Compra de Mercadorias"]),
    ("Material de Apoio (-)", "2.02", 1, 1, ["Material de Limpeza", "Material de Escritório", "Embalagens"]),
    ("Imóvel (-)", "2.03", 1, 1, ["Aluguel", "Condomínio", "IPTU", "Energia Elétrica", "Água"]),
    ("Serviços de Terceiros (-)", "2.04", 1, 1, ["Contabilidade", "Segurança", "Serviços Gerais"]),
    ("Telecomunicações (-)", "2.05", 1, 1, ["Telefonia Celular", "Internet 3G", "Telefone Fixo"]),
    ("Impostos/Taxas (-)", "2.06", 1, 1, ["Simples Nacional", "Taxas Municipais"]),
    ("Royalts e Propaganda (-)", "2.07", 1, 1, ["Propaganda", "Royalts"]),
    ("Folhas e Benefícios (-)", "2.08", 1, 1, ["Salários", "Encargos", "Vale Transporte", "Alimentação"]),
    ("Manutenção (-)", "2.09", 1, 1, ["Manutenção de Equipamentos", "Manutenção Predial"]),
    ("Outras despesas (-)", "2.10", 1, 1, ["Outras despesas"]),
    ("Pró Labore (-)", "2.11", 1, 1, ["Pró Labore"]),
    ("Provisão de Folha (-)", "3.01", 1, 1, ["Provisão de Folha"]),
    ("Depreciação de Patrimônio (-)", "3.02", 1, 1, ["Depreciação de Patrimônio"]),
    ("Aquisições (-)", "4.01", 1, 0, ["Aquisições"]),
    ("Créditos Financeiros (+)", "4.02", 0, 0, ["Créditos Financeiros"]),
    ("Débitos Financeiros (-)", "4.03", 1, 0, ["Débitos Financeiros"]),
    ("Transferência a Crédito (+)", "4.04", 0, 0, ["Transferência a Crédito"]),
    ("Transferência a Débito (-)", "4.05", 1, 0, ["Transferência a Débito"]),
]


def aplicar(banco) -> None:
    """Idempotente: só insere o que ainda não existe."""
    with banco.transacao():
        for chave, valor in CONFIG_PADRAO.items():
            banco.executar("INSERT OR IGNORE INTO config(chave, valor) VALUES (?, ?)", (chave, valor))
        for modulo, descricao, grupo, nivel in ACESSOS:
            banco.executar(
                "INSERT OR IGNORE INTO acessos(modulo, descricao, grupo, nivel) VALUES (?,?,?,?)",
                (modulo, descricao, grupo, nivel))
        banco.executar("INSERT OR IGNORE INTO loja(id, razao_social, nome_fantasia) VALUES (1, '', '')")
        banco.executar(
            "INSERT OR IGNORE INTO maquinas(terminal, nome_computador, descricao) VALUES (1, ?, ?)",
            (socket.gethostname(), "Caixa 1"))

        if banco.valor("SELECT valor FROM config WHERE chave = 'semeado'"):
            return  # cadastros-modelo só na primeira vez (o usuário pode apagá-los depois)

        for nome in CARGOS:
            banco.executar("INSERT OR IGNORE INTO cargos(nome) VALUES (?)", (nome,))
        for nome, abrev in UNIDADES:
            banco.executar("INSERT OR IGNORE INTO unidades(nome, abreviatura) VALUES (?, ?)", (nome, abrev))
        for desc, aliq, formato in ALIQUOTAS:
            banco.executar("INSERT OR IGNORE INTO aliquotas(descricao, aliquota, formato) VALUES (?,?,?)",
                           (desc, aliq, formato))
        for tipo, ordem, troco, vale, gaveta in TIPOS_PAGAMENTO:
            banco.executar(
                "INSERT OR IGNORE INTO tipos_pagamento(tipo, ordem, permite_troco, emite_vale, na_gaveta) VALUES (?,?,?,?,?)",
                (tipo, ordem, troco, vale, gaveta))
        for ordem, (nome, codigo, debito, resultado, subs) in enumerate(PLANOS, start=1):
            banco.executar(
                "INSERT OR IGNORE INTO planos_contas(nome, codigo, debito, resultado, ordem) VALUES (?,?,?,?,?)",
                (nome, codigo, debito, resultado, ordem))
            plano_id = banco.valor("SELECT id FROM planos_contas WHERE nome = ?", (nome,))
            for sub in subs:
                banco.executar("INSERT OR IGNORE INTO subplanos(nome, plano_id) VALUES (?, ?)", (sub, plano_id))

        banco.executar("INSERT OR IGNORE INTO grupos(nome) VALUES ('DIVERSOS')")
        grupo_id = banco.valor("SELECT id FROM grupos WHERE nome = 'DIVERSOS'")
        banco.executar("INSERT OR IGNORE INTO subgrupos(nome, grupo_id) VALUES ('DIVERSOS', ?)", (grupo_id,))

        cargo_adm = banco.valor("SELECT id FROM cargos WHERE nome = 'Administrador'")
        if not banco.valor("SELECT COUNT(*) FROM operadores"):
            banco.executar(
                "INSERT INTO operadores(nome, senha, nivel, cargo_id) VALUES ('ADM', ?, 4, ?)",
                (seguranca.gerar_hash("ADM"), cargo_adm))
        banco.executar("INSERT OR REPLACE INTO config(chave, valor) VALUES ('semeado', ?)", (fmt.agora(),))
