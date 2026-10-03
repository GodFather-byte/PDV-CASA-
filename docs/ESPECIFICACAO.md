# Especificação: manuais × implementação

Fontes: **MANUAL ADM LOCAL** (administração do Virtual.Net/ViCommerce), **MANUAL CAIXA** (operação de
venda) e **MANUAL EVICOMMERCE** (versão web). Este documento liga cada seção dos manuais ao código,
registra as decisões tomadas onde o manual não definia a regra e lista o que **não** foi feito.

Convenção: `C` = controlador (regra, em `src/controllers/`), `UI` = tela (em `src/ui/`), `T` = teste.

## 1. Mapa dos manuais

### MANUAL ADM LOCAL

| Seção | Assunto | Implementação |
|------|---------|---------------|
| 1 | Entrada (usuário/senha, ADM/ADM, sem diferenciar maiúsculas, "Senha Incorreta", nível 0 vai ao caixa), menu com 7 botões e painel | C `acesso_controller` · UI `login`, `app` (atalhos M, C, L, R, U, O, S) |
| 2 | Botões de tarefas (Incluir, Excluir, Gravar, Cancelar, Filtrar, Pesquisar, Ordenar, Tela, Imprimir, navegação, Sair) | UI `cadastros_tk` |
| 3.1 a 3.3 | Unidades, grupos, subgrupos (impressora remota) | `entidades.py` · C `cadastro_controller` |
| 3.4 | Produtos: código de 13 dígitos, barras, serviço, decimal, estoque mínimo, dividir em 1 a 55, maior, montagem, promoções, fiscais | `entidades.py` · C `produto_controller` (preço vigente, busca) |
| 3.5 | Composição (ficha técnica) e custo | C `produto_controller` · UI `composicao_ui` |
| 3.6 a 3.9 | Cargos, operadores (senha até 10), fornecedores, clientes (+ "Gerar arquivos") | `entidades.py` · UI `cadastros_tk` |
| 3.10 | Tipos de pagamento (ordem, caixa, emite vale, troco, saldo inicial, TEF) | `entidades.py` |
| 3.11 e 3.12 | Plano de contas e sub planos (modelo já carregado) | `entidades.py` · `sementes.py` |
| 5.1 | Lançamento de contas | C `contas_controller` · UI `lancamentos_ui` |
| 5.2 | Estoque: compra, entrada, saída, descarte, contagem | C `estoque_controller` · UI `lancamentos_ui` |
| 6.01 e 6.02 | Venda no período (cupom a cupom, totalização na fita ou A4) e por grupo | C `relatorio_vendas` · UI `relatorios_ui` |
| 6.03 a 6.06 | Entradas/saídas do caixa, fechamentos, comandas, garçons | C `relatorio_vendas` |
| 6.07 | C.M.V. | C `relatorio_vendas.cmv` |
| 6.08 a 6.11 | Clientes inativos e comissões (produto, venda, cliente) | C `relatorio_gestao`, `relatorio_vendas` |
| 6.12 a 6.14 | Resultado financeiro, extrato de contas, movimento de estoque | C `relatorio_gestao` |
| "6.11" | Estoque atual (verde/amarelo/vermelho, filtros por data e valor, formulários de contagem e pedidos) | C `relatorio_gestao.estoque_atual` · UI `JanelaEstoqueAtual` |
| 7.01 a 7.03 | Limpeza do movimento, programa de comunicação, backup | C `utilitario_controller` · UI `utilitarios_ui` |
| 8.01 | Níveis de acesso 0 a 4 por módulo | C `acesso_controller` · UI `config_ui` |
| 8.02 a 8.04 | Loja, configurações, máquinas | C `config_controller` · UI `config_ui` |
| 9 | Saída (volta à tela de entrada) | UI `app.sair` |

### MANUAL CAIXA

| Assunto | Implementação |
|---------|---------------|
| Abertura do turno (nº do turno, fundo de caixa, "Confirma Valor Inicial?") | C `turno_controller.abrir` · UI `caixa_dialogos.abrir_turno` |
| Lançar item: código, quantidade, Enter; lista por nome; Consultar; observação (tecla O) | UI `caixa_ui` · C `caixa_controller.adicionar_item` |
| Cancelar item e venda inteira; senha de supervisor | UI `caixa_ui.menu_cancelar` · C `acesso_controller.validar_supervisor` |
| Pagamento (F12): formas, múltiplos pagamentos, desconto % e valor, serviço editável, troco, contra-vale | UI `caixa_pagamento` · C `caixa_controller.liquidar/fechar` |
| Mesas (F4), transferir inteira (F10), várias (T) e parte dos itens, pré-conta (F8), tempo de inatividade | C `caixa_controller` · UI `caixa_ui` |
| Repique (F9), sangria (F7), gaveta (F11), balança (F2), leitor óptico (F3) | UI `caixa_ui` · `hardware/dispositivos.py` (interfaces) |
| Caderneta (F5): escolher/incluir/consultar cliente, débito, crédito, excedente vira crédito | C `caderneta_controller`, `caixa_controller` · UI `clientes_ui` |
| Entrega (F6): taxa por bairro, troco para quanto, entregador (E), pendentes | C `entrega_controller` · UI `clientes_ui`, `caixa_ui` |
| Troca de turno: valor declarado antes do esperado, sobra/falta verde ou vermelho, imprimir e gerar arquivo | C `turno_controller.fechar` · UI `caixa_dialogos.PainelFechamento` |
| Leitura X e Redução Z | **Gerenciais, não fiscais** (ver seção 3) |

### MANUAL EVICOMMERCE (web)

Aproveitado no PDV local: estoque Inicial, Pedido (vira Compra ao confirmar a entrega) e Descarte de
acabados; contas mensais; transferência entre contas; relatórios Informativo, Horas, Cancelados,
Custo médio, Clientes e Financeiro; campos de produto `compõe`, `composto`, `manual`, `automático`.
O sistema web em si (cadastros e relatórios no navegador) é outra aplicação e fica em `backend/`.

## 2. Decisões onde o manual era ambíguo

Estas regras foram escolhidas por quem implementou; confirme com o dono da loja.

- **Valor esperado do turno** = valor inicial + recebimentos das formas que ficam na gaveta (dinheiro, cheque, ticket;
  já líquidos de troco) + entradas − sangrias. Cartão e Pix NÃO entram: são conferidos na maquininha, e o relatório
  mostra o total "fora da gaveta". Cada forma de pagamento tem a marca "Fica na gaveta" (`tipos_pagamento.na_gaveta`;
  cartão, Pix, transferência e TEF saem de fábrica). Repique e contra-vale emitido são informativos e não entram.
  (O exemplo do manual não incluía as sangrias no esperado; aqui elas reduzem o esperado porque o dinheiro saiu.)
- **Serviço** (10% configurável) só em mesa, calculado sobre os itens marcados "cobrar serviço", antes
  do desconto. O desconto incide só nos produtos. O operador pode digitar outro valor de serviço, até zero.
- **Estoque baixa ao fechar a venda**, não ao lançar o item; cancelar o cupom estorna. Estoque negativo é permitido.
- **Promoções** (período, dias da semana, horário) valem em conjunto; havendo mais de uma, vence a de menor
  preço. Faixas que viram a meia-noite funcionam (ex.: 22:00 às 02:00).
- **Meio a meio**: preço pelo maior (ou média proporcional); combo (`composto`) tem preço único. Cada parte
  baixa a fração correspondente do estoque.
- **Caderneta**: limite 0 significa sem limite; saldo negativo é dívida. Excedente do pagamento pode virar
  crédito ou troco.
- **Conta mensal** repete o mesmo valor por N meses (aluguel, internet). Já a compra lançada em contas a pagar
  em N meses DIVIDE o total (os centavos que sobram vão na 1ª parcela).
- **Cupom** é numerado ao fechar ou cancelar. Só dá para cancelar cupom do turno ainda aberto.
- **Limpeza do movimento** apaga até o dia anterior à data informada, faz backup antes, recusa apagar vendas não
  enviadas à nuvem quando a sincronização está configurada e preserva o saldo da caderneta.
- **Módulos de acesso**: o manual cita 31 módulos sem listá-los; foram definidos 40 (ver `sementes.ACESSOS`),
  todos com nível configurável de 1 a 4.
- **Senhas** são guardadas com PBKDF2 e comparadas sem diferenciar maiúsculas, como pede o manual.
- **Busca por nome** (produtos, clientes, contas, cadastros) ignora acento e caixa: "cafe" acha "Café" (função SQL `norm()`).
- **Quantidade por item** tem teto (configuração `qtd_maxima_item`, padrão 99.999; 0 desliga), para um código de
  barras digitado no campo Quantidade não virar uma venda de bilhões. `nan` e `inf` são recusados.
- **Transferir parte de um item** divide total e comissão sem perder nem criar centavo.
- **Licença mensal** (Ed25519, offline): aviso 7 dias antes, carência de 5 dias, nunca bloqueia com o turno aberto;
  só é exigida no executável ou com `licenca_exigir = S`. Detalhes em `src/core/licenca.py` e no README.

## 3. O que NÃO está implementado

| Item | Situação |
|------|----------|
| Impressora fiscal (ECF), NFC-e, SAT | Não emite documento fiscal. Cupom é "NÃO FISCAL". Leitura X e Redução Z são relatórios gerenciais. Campos fiscais do produto (NCM, alíquotas) são guardados mas não usados. |
| TEF (cartões) | Campos do cadastro existem; não há integração. |
| Balança Toledo/Filizola e gaveta | Há a interface; a leitura/abertura automática não foi implementada (depende do equipamento). O caixa pede o peso digitado e registra a abertura de gaveta. |
| Rede com vários caixas no mesmo banco | O banco SQLite é local a cada terminal. |
| Sincronização com a nuvem em loja | API (FastAPI) e cliente existem, com testes de contrato; falta validar em loja, HTTPS e token por loja. Cadastros descendo da nuvem: não existe. |
| Tabela de preços por empresa (multi-loja) | Uma única tabela de preços. |
| E-mail, logotipo no cupom, foto do subgrupo | Os campos são guardados; não são usados. |
| Colunas "Turno 1 a 3" e "Figura" do tipo de pagamento | O manual não explica o uso; omitidas. |
| Acesso "Transportadoras" do Evicommerce | Citado sem descrição; omitido. |
| Campos de nota fiscal de compra (BC ICMS, chave de acesso...) | Fora de escopo (dependem de consultor fiscal, segundo o próprio manual). |
