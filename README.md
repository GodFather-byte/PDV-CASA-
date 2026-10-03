# PDV Casa

Sistema de ponto de venda offline-first para bares, casas noturnas e operações de
alimentação. O objetivo é evoluir para um PDV confiável de ponta a ponta: vendas,
mesas e comandas, turnos, pagamentos, estoque, clientes, financeiro, relatórios e
sincronização idempotente com a nuvem.

> **Estado do projeto:** em desenvolvimento. Os controladores de caixa, estoque,
> cadastros, turnos e contas têm testes automatizados. A sincronização possui um
> montador de lotes, mas o transporte ainda é simulado. As telas e a integração
> real com o servidor ainda não representam um produto pronto para operação
> comercial.

## Começar

Requer Python 3.10 ou superior. Na raiz do repositório:

```powershell
python --version
python -m unittest discover -s tests -v
```

O protótipo de terminal pode ser aberto com:

```powershell
python -m src.main
```

Essa entrada usa os adaptadores legados de venda e serve para demonstração. Para
uma operação real, use o fluxo de `CaixaController`, que inclui turno, fechamento,
pagamentos e baixa de estoque transacional. A interface nova está sendo construída
em Tkinter; login, tema, visualizador e cadastro genérico já têm módulos iniciais,
mas ainda não há uma entrada gráfica completa (`src.app`) que conecte as telas ao
fluxo novo.
As interfaces Flet antigas estão congeladas e servem apenas como protótipo.

## O que já existe

- **Caixa e vendas:** balcão, mesas, itens, preços promocionais, descontos,
  serviço, pagamentos, troco/vale e cancelamento.
- **Estoque:** compras e outros lançamentos, pedidos, contagem, composição de
  produtos e histórico de movimentos; a venda fechada baixa o estoque e o
  cancelamento estorna os movimentos.
- **Cadastros e operação:** produtos, clientes, operadores, formas de pagamento,
  configurações, turnos, contas, caderneta e entregas.
- **Relatórios e impressão:** há controladores para relatórios de vendas/gestão e
  para texto de cupom não fiscal, saída em tela/arquivo/Windows, Leitura X e
  Redução Z gerenciais. Não há emissão fiscal nem homologação de periféricos.
- **Dados para nuvem:** `SyncController` monta lotes identificados por UUID e
  registra apenas confirmações explícitas do servidor.
- **Qualidade:** a suíte cobre regras de caixa, estoque, cadastro, formatação,
  segurança e banco local. Rode os testes antes de integrar alterações.

## Arquitetura

- `src/controllers/`: regras de negócio do PDV local.
- `src/database/`: esquema e acesso ao SQLite local.
- `src/core/`: formatação monetária, segurança, erros e utilitários.
- `src/ui/`: interface Tkinter nova em desenvolvimento; telas Flet antigas congeladas.
- `src/sync/`: transporte PDV ↔ nuvem.
- `backend/`: protótipo separado de persistência/modelos para a nuvem; ainda não
  implementa a API receptora de sincronização e não é usado pelo PDV local.

## Banco local e dados

O banco padrão é `loja_offline.db`, na raiz do projeto. Para usar outro arquivo no
PowerShell:

```powershell
$env:PDV_DB = "$PWD\dados\loja_offline.db"
python -m src.main
```

Ao detectar o banco do protótipo antigo, o sistema arquiva uma cópia
`*.legado-*.bak` e cria o esquema atual. **O backup não é uma migração:** os
registros antigos não são importados para o banco novo. Faça e confira uma cópia
antes de apontar o PDV para dados importantes.

Convenções obrigatórias entre as camadas:

- valores monetários são inteiros em centavos (`350` = R$ 3,50), nunca `float`;
- quantidades usam até quatro casas decimais;
- timestamps locais são armazenados em ISO (`YYYY-MM-DD HH:MM:SS`);
- UUID identifica a venda e permite reenvio idempotente.

## Sincronização e produção

`SyncController` prepara os dados e confirma os UUIDs aceitos; o transporte em
`src/sync/sincronizador.py` ainda usa uma simulação. Ele **não está pronto para
enviar vendas a uma API real**. Não trate a mensagem de sucesso do protótipo como
confirmação remota nem use a sincronização simulada em operação com vendas reais.

Antes de operar comercialmente, ainda é necessário validar e completar: interface
Tkinter integrada ao fluxo novo, transporte HTTP autenticado com confirmação por UUID,
tratamento de falhas e retries, instalador/dependências, backup e restauração
testados, hardware fiscal/periféricos e homologação no ambiente da loja.

## Implementação em nuvem

`backend/` contém atualmente configuração SQLAlchemy, modelos de cadastro e um
arquivo de dependências, mas não um app FastAPI/rota para receber vendas. A
implementação da API e a integração com o contrato em
[`docs/COORDENACAO.md`](docs/COORDENACAO.md) ainda estão pendentes.
