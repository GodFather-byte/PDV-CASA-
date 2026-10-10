"""Esquema SQLite do PDV (a versão atual está em VERSAO_ESQUEMA; as migrações, em MIGRACOES).

Convencoes: dinheiro em INTEIRO de centavos (colunas *_cent); quantidades REAL;
datas em texto ISO local. Booleanos sao INTEGER 0/1.
"""


VERSAO_ESQUEMA = 12

# Definição única da tabela de máquinas (reutilizada na migração v2). Sem CHECK em
# modo_impressao: a validação fica em config_controller, e isso permite novos modos
# (como 'termica') sem precisar recriar a tabela a cada modo novo.
MAQUINAS_DDL = """CREATE TABLE IF NOT EXISTS maquinas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    terminal INTEGER NOT NULL UNIQUE DEFAULT 1,
    nome_computador TEXT, descricao TEXT,
    modo_impressao TEXT NOT NULL DEFAULT 'tela',
    colunas_fita INTEGER NOT NULL DEFAULT 40,
    impressora_remota_pasta TEXT,
    balanca TEXT NOT NULL DEFAULT 'Nenhuma',
    balanca_porta TEXT,
    gaveta INTEGER NOT NULL DEFAULT 0,
    leitor_optico INTEGER NOT NULL DEFAULT 0,
    impressora_termica_conexao TEXT NOT NULL DEFAULT 'rede',
    impressora_termica_endereco TEXT,
    impressora_termica_codepage TEXT NOT NULL DEFAULT 'cp850',
    impressora_termica_cortar INTEGER NOT NULL DEFAULT 1,
    impressora_termica_gaveta INTEGER NOT NULL DEFAULT 0,
    impressora_termica_pino INTEGER NOT NULL DEFAULT 0,
    impressora_remota_conexao TEXT NOT NULL DEFAULT 'pasta',
    impressora_remota_endereco TEXT,
    impressora_termica_logotipo INTEGER NOT NULL DEFAULT 0
)"""

TABELAS = [
    # ------------------------------------------------------------ infraestrutura
    """CREATE TABLE IF NOT EXISTS config (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS loja (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        razao_social TEXT, nome_fantasia TEXT, slogan TEXT, cnpj TEXT, ie TEXT,
        endereco TEXT, complemento TEXT, bairro TEXT, cidade TEXT, uf TEXT, cep TEXT,
        telefone TEXT, email TEXT, logotipo TEXT
    )""",
    MAQUINAS_DDL,
    """CREATE TABLE IF NOT EXISTS acessos (
        modulo TEXT PRIMARY KEY,
        descricao TEXT NOT NULL,
        grupo TEXT NOT NULL,
        nivel INTEGER NOT NULL CHECK (nivel BETWEEN 1 AND 4)
    )""",
    """CREATE TABLE IF NOT EXISTS log_eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quando TEXT NOT NULL,
        operador_id INTEGER,
        evento TEXT NOT NULL,
        detalhe TEXT
    )""",
    # ------------------------------------------------------------------ cadastros
    """CREATE TABLE IF NOT EXISTS unidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        abreviatura TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS grupos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS subgrupos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        grupo_id INTEGER NOT NULL REFERENCES grupos(id),
        impressora_remota INTEGER NOT NULL DEFAULT 0,
        figura TEXT,
        UNIQUE (grupo_id, nome)
    )""",
    """CREATE TABLE IF NOT EXISTS aliquotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL UNIQUE,
        aliquota REAL NOT NULL DEFAULT 0,
        formato TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nome TEXT NOT NULL UNIQUE,
        subgrupo_id INTEGER NOT NULL REFERENCES subgrupos(id),
        unidade_id INTEGER NOT NULL REFERENCES unidades(id),
        aliquota_id INTEGER REFERENCES aliquotas(id),
        preco_cent INTEGER NOT NULL DEFAULT 0,
        cobrar_servico INTEGER NOT NULL DEFAULT 1,
        venda INTEGER NOT NULL DEFAULT 1,
        aceita_decimal INTEGER NOT NULL DEFAULT 0,
        atalho TEXT,
        cbarra TEXT,
        controla_estoque INTEGER NOT NULL DEFAULT 0,
        estoque_minimo REAL NOT NULL DEFAULT 0,
        qt_atual REAL NOT NULL DEFAULT 0,
        qt_inicial REAL NOT NULL DEFAULT 0,
        ult_preco_cent INTEGER NOT NULL DEFAULT 0,
        ult_atualizacao TEXT,
        partes INTEGER NOT NULL DEFAULT 1 CHECK (partes BETWEEN 1 AND 55),
        maior INTEGER NOT NULL DEFAULT 1,
        montagem INTEGER NOT NULL DEFAULT 0,
        para_ser_montado INTEGER NOT NULL DEFAULT 0,
        manual INTEGER NOT NULL DEFAULT 0,
        compoe INTEGER NOT NULL DEFAULT 1,
        composto INTEGER NOT NULL DEFAULT 0,
        usa_observacao INTEGER NOT NULL DEFAULT 0,
        comissao_pct REAL NOT NULL DEFAULT 0,
        promo_de TEXT, promo_ate TEXT, promo_preco_cent INTEGER NOT NULL DEFAULT 0,
        sem_inicial INTEGER, sem_final INTEGER, sem_preco_cent INTEGER NOT NULL DEFAULT 0,
        hora_ini TEXT, hora_fim TEXT, hora_preco_cent INTEGER NOT NULL DEFAULT 0,
        validade_dias INTEGER NOT NULL DEFAULT 0,
        balanca INTEGER NOT NULL DEFAULT 0,
        automatico INTEGER NOT NULL DEFAULT 0,
        texto_sugestao TEXT,
        ncm TEXT, desc_aliq_icms TEXT, situacao_tributaria TEXT,
        aliquota_ipi REAL NOT NULL DEFAULT 0, reducao_base REAL NOT NULL DEFAULT 0,
        ativo INTEGER NOT NULL DEFAULT 1
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_produtos_cbarra ON produtos(cbarra) WHERE cbarra IS NOT NULL AND cbarra <> ''",
    "CREATE INDEX IF NOT EXISTS ix_produtos_subgrupo ON produtos(subgrupo_id)",
    """CREATE TABLE IF NOT EXISTS observacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo INTEGER NOT NULL UNIQUE,
        texto TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS composicoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
        insumo_id INTEGER NOT NULL REFERENCES produtos(id),
        quantidade REAL NOT NULL CHECK (quantidade > 0),
        UNIQUE (produto_id, insumo_id)
    )""",
    """CREATE TABLE IF NOT EXISTS cargos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS operadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
        senha TEXT NOT NULL,
        nivel INTEGER NOT NULL DEFAULT 0 CHECK (nivel BETWEEN 0 AND 4),
        cargo_id INTEGER REFERENCES cargos(id),
        garcom INTEGER NOT NULL DEFAULT 0,
        entregador INTEGER NOT NULL DEFAULT 0,
        vendedor INTEGER NOT NULL DEFAULT 0,
        recebe_comissao INTEGER NOT NULL DEFAULT 0,
        comissao_pct REAL NOT NULL DEFAULT 0,
        ativo INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS fornecedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        contato TEXT, ddd TEXT, telefone TEXT, celular TEXT, cnpj TEXT, ie TEXT,
        endereco TEXT, complemento TEXT, bairro TEXT, cidade TEXT, uf TEXT, cep TEXT,
        email TEXT, obs TEXT,
        ativo INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS bairros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        taxa_cent INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_consulta TEXT NOT NULL UNIQUE,
        nome TEXT NOT NULL,
        endereco TEXT, complemento TEXT, cep TEXT, codigo TEXT,
        bairro_id INTEGER REFERENCES bairros(id),
        cidade TEXT, telefone TEXT, rg TEXT, cpf TEXT, email TEXT, obs TEXT,
        limite_cent INTEGER NOT NULL DEFAULT 0,
        saldo_cent INTEGER NOT NULL DEFAULT 0,
        ativo INTEGER NOT NULL DEFAULT 1
    )""",
    "CREATE INDEX IF NOT EXISTS ix_clientes_nome ON clientes(nome)",
    """CREATE TABLE IF NOT EXISTS tipos_pagamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL UNIQUE,
        ordem INTEGER NOT NULL DEFAULT 0,
        caixa INTEGER NOT NULL DEFAULT 1,
        emite_vale INTEGER NOT NULL DEFAULT 0,
        permite_troco INTEGER NOT NULL DEFAULT 0,
        na_gaveta INTEGER NOT NULL DEFAULT 1,
        saldo_inicial_cent INTEGER NOT NULL DEFAULT 0,
        taxa_pct REAL NOT NULL DEFAULT 0,
        desc_cartao_pct REAL NOT NULL DEFAULT 0,
        vias INTEGER NOT NULL DEFAULT 1,
        tipo_tef INTEGER NOT NULL DEFAULT 0,
        aciona_tef INTEGER NOT NULL DEFAULT 0,
        cheque_tef INTEGER NOT NULL DEFAULT 0,
        mais_info INTEGER NOT NULL DEFAULT 0,
        ativo INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS planos_contas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        codigo TEXT NOT NULL UNIQUE,
        debito INTEGER NOT NULL DEFAULT 1,
        resultado INTEGER NOT NULL DEFAULT 1,
        ordem INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS subplanos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        plano_id INTEGER NOT NULL REFERENCES planos_contas(id),
        UNIQUE (plano_id, nome)
    )""",
    # -------------------------------------------------------------------- contas
    """CREATE TABLE IF NOT EXISTS contas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subplano_id INTEGER NOT NULL REFERENCES subplanos(id),
        descricao TEXT NOT NULL,
        tipo_pagamento_id INTEGER NOT NULL REFERENCES tipos_pagamento(id),
        valor_cent INTEGER NOT NULL,
        documento TEXT, mercadoria INTEGER NOT NULL DEFAULT 0, nota TEXT,
        previsao INTEGER NOT NULL DEFAULT 0,
        dt_entrada TEXT NOT NULL, dt_vencimento TEXT NOT NULL, dt_quitacao TEXT,
        fornecedor_id INTEGER REFERENCES fornecedores(id),
        transferir_para_id INTEGER REFERENCES tipos_pagamento(id),
        lancamento_estoque_id INTEGER,
        parcela TEXT,
        operador_id INTEGER REFERENCES operadores(id),
        criado_em TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS ix_contas_venc ON contas(dt_vencimento)",
    # ------------------------------------------------------------------- estoque
    """CREATE TABLE IF NOT EXISTS lancamentos_estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL CHECK (tipo IN
            ('inicial','pedido','compra','entrada','saida','descarte','contagem','desc_acabados')),
        data TEXT NOT NULL,
        descricao TEXT, documento TEXT, nota_fiscal TEXT,
        fornecedor_id INTEGER REFERENCES fornecedores(id),
        valor_cent INTEGER NOT NULL DEFAULT 0,
        desconto_cent INTEGER NOT NULL DEFAULT 0,
        operador_id INTEGER REFERENCES operadores(id),
        criado_em TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS itens_estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lancamento_id INTEGER NOT NULL REFERENCES lancamentos_estoque(id) ON DELETE CASCADE,
        produto_id INTEGER NOT NULL REFERENCES produtos(id),
        quantidade REAL NOT NULL,
        preco_unit_cent INTEGER NOT NULL DEFAULT 0,
        desconto_cent INTEGER NOT NULL DEFAULT 0,
        valor_cent INTEGER NOT NULL DEFAULT 0,
        qt_anterior REAL NOT NULL DEFAULT 0,
        diferenca REAL NOT NULL DEFAULT 0,
        aplicado INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS movimentos_estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL REFERENCES produtos(id),
        tipo TEXT NOT NULL,
        quantidade REAL NOT NULL,
        qt_apos REAL NOT NULL,
        ref_tipo TEXT, ref_id INTEGER,
        criado_em TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_movest_prod ON movimentos_estoque(produto_id, criado_em)",
    # ------------------------------------------------------------- caixa / vendas
    """CREATE TABLE IF NOT EXISTS turnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER NOT NULL,
        terminal INTEGER NOT NULL DEFAULT 1,
        operador_id INTEGER REFERENCES operadores(id),
        aberto_em TEXT NOT NULL,
        valor_inicial_cent INTEGER NOT NULL DEFAULT 0,
        cupom_inicial INTEGER NOT NULL DEFAULT 0,
        fechado_em TEXT,
        valor_final_cent INTEGER,
        cupom_final INTEGER,
        esperado_cent INTEGER,
        resultado_cent INTEGER,
        fechado_por INTEGER REFERENCES operadores(id),
        status TEXT NOT NULL DEFAULT 'aberto' CHECK (status IN ('aberto','fechado'))
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_turno_aberto ON turnos(terminal) WHERE status = 'aberto'",
    """CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT NOT NULL UNIQUE,
        cupom INTEGER,
        turno_id INTEGER REFERENCES turnos(id),
        terminal INTEGER NOT NULL DEFAULT 1,
        operador_id INTEGER REFERENCES operadores(id),
        modalidade TEXT NOT NULL DEFAULT 'balcao'
            CHECK (modalidade IN ('balcao','mesa','caderneta','entrega')),
        posicao INTEGER NOT NULL DEFAULT 0,
        comanda INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'aberta'
            CHECK (status IN ('aberta','conta_enviada','fechada','cancelada')),
        aberta_em TEXT NOT NULL,
        ultimo_lancamento_em TEXT,
        fechada_em TEXT,
        pessoas INTEGER NOT NULL DEFAULT 0,
        garcom_id INTEGER REFERENCES operadores(id),
        vendedor_id INTEGER REFERENCES operadores(id),
        entregador_id INTEGER REFERENCES operadores(id),
        cliente_id INTEGER REFERENCES clientes(id),
        subtotal_cent INTEGER NOT NULL DEFAULT 0,
        desconto_cent INTEGER NOT NULL DEFAULT 0,
        desconto_pct REAL NOT NULL DEFAULT 0,
        servico_cent INTEGER NOT NULL DEFAULT 0,
        servico_manual INTEGER NOT NULL DEFAULT 0,
        taxa_cent INTEGER NOT NULL DEFAULT 0,
        total_cent INTEGER NOT NULL DEFAULT 0,
        pago_cent INTEGER NOT NULL DEFAULT 0,
        troco_cent INTEGER NOT NULL DEFAULT 0,
        vale_cent INTEGER NOT NULL DEFAULT 0,
        troco_para_cent INTEGER NOT NULL DEFAULT 0,
        mensagem TEXT,
        saida_entrega_em TEXT,
        cancelada_por INTEGER REFERENCES operadores(id),
        motivo_cancelamento TEXT,
        sincronizado INTEGER NOT NULL DEFAULT 0
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_vendas_cupom ON vendas(cupom) WHERE cupom IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_vendas_status ON vendas(status, modalidade)",
    "CREATE INDEX IF NOT EXISTS ix_vendas_fechada ON vendas(fechada_em)",
    "CREATE INDEX IF NOT EXISTS ix_vendas_sync ON vendas(sincronizado)",
    """CREATE TABLE IF NOT EXISTS itens_venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
        produto_id INTEGER NOT NULL REFERENCES produtos(id),
        quantidade REAL NOT NULL,
        preco_unit_cent INTEGER NOT NULL,
        total_cent INTEGER NOT NULL,
        cobra_servico INTEGER NOT NULL DEFAULT 1,
        observacao TEXT,
        comissao_cent INTEGER NOT NULL DEFAULT 0,
        partes INTEGER NOT NULL DEFAULT 1,
        cancelado INTEGER NOT NULL DEFAULT 0,
        cancelado_em TEXT,
        operador_id INTEGER REFERENCES operadores(id),
        criado_em TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_itens_venda ON itens_venda(venda_id)",
    """CREATE TABLE IF NOT EXISTS itens_venda_partes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL REFERENCES itens_venda(id) ON DELETE CASCADE,
        produto_id INTEGER NOT NULL REFERENCES produtos(id),
        fracao REAL NOT NULL
    )""",
    # turno_id (v9): turno em que o dinheiro entrou. O adiantamento de uma mesa conta nesse turno, mesmo que a conta
    # feche no seguinte. Fica NULL só no pagamento antigo de uma mesa ainda aberta, que conta no turno da venda.
    """CREATE TABLE IF NOT EXISTS pagamentos_venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
        tipo_pagamento_id INTEGER NOT NULL REFERENCES tipos_pagamento(id),
        valor_cent INTEGER NOT NULL,
        troco_cent INTEGER NOT NULL DEFAULT 0,
        criado_em TEXT NOT NULL,
        turno_id INTEGER REFERENCES turnos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_pagto_venda ON pagamentos_venda(venda_id)",
    """CREATE TABLE IF NOT EXISTS movimentos_caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turno_id INTEGER NOT NULL REFERENCES turnos(id),
        tipo TEXT NOT NULL CHECK (tipo IN ('entrada','saida')),
        valor_cent INTEGER NOT NULL CHECK (valor_cent > 0),
        descricao TEXT,
        operador_id INTEGER REFERENCES operadores(id),
        criado_em TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS repiques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        turno_id INTEGER NOT NULL REFERENCES turnos(id),
        venda_id INTEGER REFERENCES vendas(id),
        posicao INTEGER NOT NULL DEFAULT 0,
        valor_cent INTEGER NOT NULL CHECK (valor_cent > 0),
        operador_id INTEGER REFERENCES operadores(id),
        criado_em TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS caderneta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL REFERENCES clientes(id),
        venda_id INTEGER REFERENCES vendas(id),
        tipo TEXT NOT NULL CHECK (tipo IN ('debito','credito')),
        valor_cent INTEGER NOT NULL CHECK (valor_cent > 0),
        descricao TEXT,
        criado_em TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_caderneta_cli ON caderneta(cliente_id)",
    # Fila de impressão (v5): o que vai para a impressora térmica/remota é gravado aqui e enviado por uma thread,
    # então a impressora fora do ar não trava o caixa e nenhum cupom se perde. `dados` são os bytes ESC/POS prontos.
    """CREATE TABLE IF NOT EXISTS fila_impressao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        criado_em TEXT NOT NULL,
        destino TEXT NOT NULL DEFAULT 'caixa' CHECK (destino IN ('caixa','remota')),
        tipo TEXT,
        nome TEXT NOT NULL,
        dados BLOB NOT NULL,
        status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente','enviado','erro','cancelado')),
        tentativas INTEGER NOT NULL DEFAULT 0,
        proxima_tentativa TEXT,
        ultimo_erro TEXT,
        enviado_em TEXT,
        venda_id INTEGER
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fila_status ON fila_impressao(status, destino, id)",
    # Telegram do dono (v11): `telegram_chats` são as conversas autorizadas (quem digitou o código de pareamento no bot);
    # `telegram_fila` são os avisos esperando envio (gravados na hora, enviados por uma thread: a internet fora do ar não
    # trava o caixa e o aviso sai quando voltar). `entregue_a` guarda os chats que já receberam (para não repetir).
    """CREATE TABLE IF NOT EXISTS telegram_chats (
        chat_id INTEGER PRIMARY KEY,
        nome TEXT,
        criado_em TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS telegram_fila (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        criado_em TEXT NOT NULL,
        tipo TEXT,
        texto TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente','enviado','erro')),
        tentativas INTEGER NOT NULL DEFAULT 0,
        entregue_a TEXT NOT NULL DEFAULT '',
        ultimo_erro TEXT,
        enviado_em TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS ix_telegram_fila ON telegram_fila(status, id)",
    # Comissão das garotas (v7): o código 50 do caixa marca a comissão no número da garota (o mesmo da comanda dela).
    # Não é venda: não entra em faturamento nem estoque. Fica 'pendente' até ser paga (sai dinheiro do caixa) ou cancelada.
    """CREATE TABLE IF NOT EXISTS garotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER NOT NULL UNIQUE CHECK (numero BETWEEN 1 AND 99999),
        nome TEXT NOT NULL,
        observacao TEXT,
        ativo INTEGER NOT NULL DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS comissoes_garotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        garota INTEGER NOT NULL CHECK (garota BETWEEN 1 AND 99999),
        valor_cent INTEGER NOT NULL CHECK (valor_cent > 0),
        turno_id INTEGER REFERENCES turnos(id),
        operador_id INTEGER REFERENCES operadores(id),
        observacao TEXT,
        criado_em TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente','paga','cancelada')),
        paga_em TEXT,
        pago_por INTEGER REFERENCES operadores(id),
        pago_turno_id INTEGER REFERENCES turnos(id),
        movimento_id INTEGER REFERENCES movimentos_caixa(id),
        cancelada_em TEXT,
        cancelada_por INTEGER REFERENCES operadores(id),
        motivo_cancelamento TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS ix_comissoes_garota ON comissoes_garotas(garota, status)",
    "CREATE INDEX IF NOT EXISTS ix_comissoes_criado ON comissoes_garotas(criado_em)",
    "CREATE INDEX IF NOT EXISTS ix_comissoes_turno ON comissoes_garotas(turno_id)",
    # Acerto da garota (v12): cada pagamento a ela guarda a comissão paga, os shows lançados pelo operador (quantidade e valor de
    # cada um) e o total entregue. Shows nunca são contados sozinhos: só existem quando o operador digita no fechamento dela.
    """CREATE TABLE IF NOT EXISTS acertos_garotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        garota INTEGER NOT NULL CHECK (garota BETWEEN 1 AND 99999),
        turno_id INTEGER REFERENCES turnos(id),
        operador_id INTEGER REFERENCES operadores(id),
        criado_em TEXT NOT NULL,
        comissao_cent INTEGER NOT NULL DEFAULT 0,
        shows_qtd INTEGER NOT NULL DEFAULT 0,
        show_valor_cent INTEGER NOT NULL DEFAULT 0,
        shows_cent INTEGER NOT NULL DEFAULT 0,
        total_cent INTEGER NOT NULL,
        movimento_id INTEGER REFERENCES movimentos_caixa(id),
        tirou_do_caixa INTEGER NOT NULL DEFAULT 0
    )""",
    "CREATE INDEX IF NOT EXISTS ix_acertos_garota ON acertos_garotas(garota, criado_em)",
    "CREATE INDEX IF NOT EXISTS ix_acertos_turno ON acertos_garotas(turno_id)",
    # Índices dos relatórios e do fechamento (v3). São criados também em bancos antigos, na próxima abertura.
    "CREATE INDEX IF NOT EXISTS ix_vendas_status_fechada ON vendas(status, fechada_em)",
    "CREATE INDEX IF NOT EXISTS ix_vendas_cliente ON vendas(cliente_id, status, fechada_em)",
    "CREATE INDEX IF NOT EXISTS ix_vendas_turno ON vendas(turno_id)",
    "CREATE INDEX IF NOT EXISTS ix_itens_produto ON itens_venda(produto_id)",
    "CREATE INDEX IF NOT EXISTS ix_partes_item ON itens_venda_partes(item_id)",
    "CREATE INDEX IF NOT EXISTS ix_pagto_tipo ON pagamentos_venda(tipo_pagamento_id)",
    "CREATE INDEX IF NOT EXISTS ix_movcaixa_turno ON movimentos_caixa(turno_id)",
    "CREATE INDEX IF NOT EXISTS ix_repiques_turno ON repiques(turno_id)",
    "CREATE INDEX IF NOT EXISTS ix_caderneta_venda ON caderneta(venda_id)",
    "CREATE INDEX IF NOT EXISTS ix_movest_ref ON movimentos_estoque(ref_tipo, ref_id)",
    "CREATE INDEX IF NOT EXISTS ix_itens_estoque_lanc ON itens_estoque(lancamento_id)",
    "CREATE INDEX IF NOT EXISTS ix_itens_estoque_prod ON itens_estoque(produto_id)",
    "CREATE INDEX IF NOT EXISTS ix_lanc_estoque_data ON lancamentos_estoque(data)",
    "CREATE INDEX IF NOT EXISTS ix_contas_quit ON contas(dt_quitacao)",
]

# Índices que dependem de colunas criadas por migrações: rodam DEPOIS delas (ver BancoDados._criar_esquema),
# senão um banco antigo falharia ao criar o índice de uma coluna que ainda não existe.
INDICES_POS_MIGRACAO = [
    # Uma mesa OU uma comanda aberta por número: a comanda 2 e a mesa 2 podem existir ao mesmo tempo (v4).
    """CREATE UNIQUE INDEX IF NOT EXISTS ix_posicao_aberta ON vendas(comanda, posicao)
        WHERE modalidade = 'mesa' AND status IN ('aberta','conta_enviada')""",
    "CREATE INDEX IF NOT EXISTS ix_pagto_turno ON pagamentos_venda(turno_id)",     # v9
]


# Migrações por versão de destino, aplicadas em ordem quando o banco está atrasado
# (ver BancoDados._migrar). Bancos novos já nascem na VERSAO_ESQUEMA e não as executam. Cada passo é um
# comando SQL ou ("coluna", tabela, nome, definição), que só adiciona a coluna se ela ainda não existir.
MIGRACOES = {
    # v2: adiciona campos da impressora térmica e remove o CHECK de modo_impressao.
    # Recria a tabela maquinas preservando os dados existentes.
    2: [
        "ALTER TABLE maquinas RENAME TO _maquinas_old",
        MAQUINAS_DDL,
        "INSERT INTO maquinas (id, terminal, nome_computador, descricao, modo_impressao,"
        " colunas_fita, impressora_remota_pasta, balanca, balanca_porta, gaveta, leitor_optico)"
        " SELECT id, terminal, nome_computador, descricao, modo_impressao, colunas_fita,"
        " impressora_remota_pasta, balanca, balanca_porta, gaveta, leitor_optico FROM _maquinas_old",
        "DROP TABLE _maquinas_old",
    ],
    # v3: marca quais formas de pagamento ficam fisicamente na gaveta (o valor esperado do turno passa a
    # contar só elas). Mantém o comportamento antigo (tudo conta) para formas personalizadas e tira da
    # gaveta as eletrônicas: cartão, Pix, transferência e as que acionam TEF.
    3: [
        ("coluna", "tipos_pagamento", "na_gaveta", "INTEGER NOT NULL DEFAULT 1"),
        "UPDATE tipos_pagamento SET na_gaveta = 0 WHERE aciona_tef = 1 OR tipo_tef > 0"
        " OR lower(tipo) LIKE '%cart_o%' OR lower(tipo) LIKE '%pix%' OR lower(tipo) LIKE '%transfer%'",
    ],
    # v4: comandas. Uma comanda é uma venda de modalidade 'mesa' com comanda = 1 (aparece junto das mesas,
    # com serviço, pré-conta e transferência iguais). O índice antigo, único só por posicao, impedia a comanda
    # 2 de coexistir com a mesa 2; o novo (comanda, posicao) é criado em INDICES_POS_MIGRACAO.
    4: [
        ("coluna", "vendas", "comanda", "INTEGER NOT NULL DEFAULT 0"),
        "DROP INDEX IF EXISTS ix_mesa_aberta",
    ],
    # v5: logotipo da loja no cupom térmico. A tabela fila_impressao é criada por TABELAS (IF NOT EXISTS).
    5: [
        ("coluna", "maquinas", "impressora_termica_logotipo", "INTEGER NOT NULL DEFAULT 0"),
    ],
    # v6: comanda por número (até 10 mil). Quem nunca mexeu no limite (ainda 200, o antigo padrão) passa a 10000;
    # a chave posicao_padrao nasce em CONFIG_PADRAO, na abertura seguinte.
    6: [
        "UPDATE config SET valor = '10000' WHERE chave = 'num_comandas' AND valor = '200'",
    ],
    # v7: as tabelas garotas e comissoes_garotas nascem em TABELAS (IF NOT EXISTS); as chaves novas de configuração
    # (codigo_comissao, exigir_senha_comissao) nascem em CONFIG_PADRAO. Nada a migrar.
    7: [],
    # v8: a comissão paga guarda o turno em que foi paga (pago_turno_id). Os bancos que já estavam na v7 criaram a tabela sem essa
    # coluna, então ela é acrescentada; as pagas antigas recebem o turno da sangria do pagamento, quando houve.
    8: [
        ("coluna", "comissoes_garotas", "pago_turno_id", "INTEGER REFERENCES turnos(id)"),
        "UPDATE comissoes_garotas SET pago_turno_id = (SELECT m.turno_id FROM movimentos_caixa m "
        "WHERE m.id = comissoes_garotas.movimento_id) WHERE status = 'paga' AND pago_turno_id IS NULL AND movimento_id IS NOT NULL",
    ],
    # v9: cada pagamento guarda o turno em que foi recebido. Os antigos herdam o turno da venda (o de fechamento ou
    # cancelamento), que era onde já contavam; o de uma mesa ainda aberta fica NULL e continua contando onde ela fechar.
    9: [
        ("coluna", "pagamentos_venda", "turno_id", "INTEGER REFERENCES turnos(id)"),
        "UPDATE pagamentos_venda SET turno_id = (SELECT v.turno_id FROM vendas v WHERE v.id = pagamentos_venda.venda_id)"
        " WHERE turno_id IS NULL",
    ],
    # v10: some a tabela `mesas` do protótipo Flet (apagado). As mesas e comandas são vendas de modalidade 'mesa'.
    10: [
        "DROP TABLE IF EXISTS mesas",
    ],
    # v11: Telegram do dono. As tabelas telegram_chats e telegram_fila nascem em TABELAS (IF NOT EXISTS); as chaves novas de
    # configuração (telegram_*) nascem em CONFIG_PADRAO e o módulo cfg_telegram em ACESSOS, na abertura seguinte. Nada a migrar.
    11: [],
    # v12: acerto da garota com shows. A tabela acertos_garotas nasce em TABELAS (IF NOT EXISTS); as chaves novas de
    # configuração (show_valores, comissao_pede_shows) nascem em CONFIG_PADRAO. Nada a migrar.
    12: [],
}
