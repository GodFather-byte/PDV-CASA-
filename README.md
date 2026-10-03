# WillPDV

**Autor:** Willyan

Sistema de ponto de venda offline-first para bares, casas noturnas e operações de
alimentação. O objetivo é evoluir para um PDV confiável de ponta a ponta: vendas,
mesas e comandas, turnos, pagamentos, estoque, clientes, financeiro, relatórios e
sincronização idempotente com a nuvem.

> **Estado do projeto:** em desenvolvimento. O sistema local (cadastros, caixa, mesas,
> caderneta, entrega, estoque, contas, relatórios, utilitários e configurações dos
> manuais Willyan) está implementado em Python + SQLite + Tkinter e coberto
> por testes automatizados de regras e de telas. Ainda **não foi validado em loja**: não há
> emissão fiscal, TEF nem leitura real de balança/gaveta (ver
> [`docs/ESPECIFICACAO.md`](docs/ESPECIFICACAO.md)), e a sincronização com a nuvem (API + cliente) ainda não foi testada em loja.

## Começar

Requer Python 3.10 ou superior. Na raiz do repositório:

```powershell
python --version
python -m unittest discover -s tests -v
```

Para abrir o sistema (Windows: também há o atalho `iniciar_pdv.bat`):

```powershell
python -m src.app
```

Usuário inicial: **ADM**, senha **ADM** (nível 4; troque a senha e crie os operadores em
Manutenção de Cadastros > Operadores). Operadores de nível 0 entram direto no caixa. O
primeiro acesso ao caixa pede o número do turno e o valor do fundo de caixa.

O sistema local usa só a biblioteca padrão (Tkinter e SQLite). Quem usa a sincronização, a balança ou a
impressão RAW do Windows precisa de `pip install -r requirements.txt`. A pasta `src/ui/` ainda contém telas Flet antigas
(`main_ui.py`, `cadastros_ui.py`, `mesas_ui.py`...) que estão **congeladas e não fazem parte do
sistema novo**; o protótipo de console `src/main.py` também é legado.

## O que já existe

- **Caixa e vendas:** balcão, mesas e comandas, itens, preços promocionais, descontos,
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

## Mesas e comandas

No caixa, o campo **Mesa ou comanda** (tecla **F4**) aceita `5` para a mesa 5 e `C2` para a comanda 2. Também dá para
digitar `C2` direto no campo do código (ou bipar o cartão da comanda): se não existir produto com esse código/atalho, a
comanda 2 é aberta e os itens seguintes caem nela.

No **rodapé** do caixa ficam os ícones das posições abertas, cada um com o número e o total embaixo: o **Balcão** (primeiro
ícone), a **mesa** (mesinha com garrafa e copo), a **comanda** (cartão, ex.: `C2`), a **conta enviada** (conta sobre a
bandeja) e o **relógio** nas paradas além do tempo de inatividade. O ícone da venda que está na tela tem a borda grossa.
São mostradas duas linhas; havendo mais, a faixa rola (barra ou roda do mouse).

- **Esc volta ao "marcar comanda":** com a venda em andamento, Esc leva ao campo da posição, com o número selecionado:
  digite `7` ou `C7` e Enter. Com um produto escolhido (esperando a quantidade), o Esc só cancela o produto. Um segundo Esc
  volta ao balcão; as mesas e comandas abertas continuam gravadas.
- **Escolher um ícone:** clique nele, ou seta para baixo no campo da posição e então setas, **Enter** (chama), **T**
  (outras posições vêm para a escolhida) e **Esc** (volta ao campo). Digitar um número ou `C` com o foco nos ícones já
  começa a marcar a posição; `0` é o balcão.
- A comanda funciona como uma mesa com **numeração própria**: a mesa 2 e a comanda 2 existem ao mesmo tempo.
- Tudo o que vale para a mesa vale para a comanda: serviço, desconto, pré-conta (impressa como "CONTA DA COMANDA"),
  F10 (transfere tudo), T (várias para uma) e a transferência de parte dos itens, inclusive entre mesa e comanda
  (ex.: F10 e `C2` levam a mesa 5 para a comanda 2).
- Em **Configurações > Mesas e serviço**: *Número de comandas* (padrão 200; **0 desliga as comandas**), *Cobrar serviço
  nas comandas* e *Mostrar sempre os ícones das mesas e comandas abertas no rodapé do caixa* (desligado, eles só aparecem
  com Esc/F4 e somem ao escolher uma posição).
- Relatórios: "Mesas e comandas" mostra a posição como `5` ou `C2`; o filtro *Modalidade* separa `mesa` de `comanda`.
- A **nuvem** ainda recebe a comanda como venda de mesa (o contrato de sincronização não mudou).

## Arquitetura

- `src/controllers/`: regras de negócio do PDV local.
- `src/database/`: esquema e acesso ao SQLite local.
- `src/core/`: formatação monetária, segurança, erros e utilitários.
- `src/ui/`: interface Tkinter (`app.py` é a janela principal, `caixa_ui.py` o caixa); telas Flet antigas congeladas.
- `tests/`: regras de negócio, telas (com um robô que opera as janelas modais) e o teste de fumaça.
- `src/sync/`: transporte PDV ↔ nuvem.
- `backend/`: API de nuvem (FastAPI) que recebe os lotes de vendas e o painel do dono; não é usada pelo PDV local.
- `tools/`: ferramentas do fornecedor (licença); não vão no instalador.

## Banco local e dados

O banco padrão é `loja_offline.db`, na raiz do projeto (no executável, em `%LOCALAPPDATA%\WILL-PDV`). Para usar outro arquivo no
PowerShell:

```powershell
$env:PDV_DB = "$PWD\dados\loja_offline.db"
python -m src.app
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

## Sincronização com a nuvem

O PDV envia as vendas fechadas e canceladas a uma API (`backend/`, FastAPI), de forma idempotente por UUID:

1. No servidor (`pip install -r backend/requirements.txt`), na raiz do repositório:

   ```powershell
   $env:PDV_API_TOKEN = "um-segredo-longo-e-aleatorio"
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

   O painel do dono abre em `http://servidor:8000/` e pede o mesmo token.
2. No PDV, em Configurações > Nuvem, informe o endereço (`http://servidor:8000/v1/sincronizar`), o token e a chave
   da loja.
3. Deixe o envio rodando em outra janela: `python -m src.app --sync` (no executável: `WillPDV.exe --sync`).
   Ele registra em `logs/sync.log`, espera cada vez mais se a nuvem cair e só confirma o que a API aceitou.

O painel inicial do PDV mostra as vendas aguardando envio e as recusadas pela nuvem (em quarentena). O contrato está em
[`docs/COORDENACAO.md`](docs/COORDENACAO.md) e é verificado por `tests/test_nuvem.py`.

Antes de operar comercialmente ainda é necessário: HTTPS (proxy reverso ou túnel) e token por loja, teste em loja com a
rotina real do caixa, backup e restauração testados, hardware fiscal/periféricos e homologação no ambiente da loja.

## Licença mensal e executável

`python build_pdv.py` gera o executável (PyInstaller) em `dist/WillPDV/`. No executável os dados (banco, Backup,
impressao, logs) ficam em `%LOCALAPPDATA%\WILL-PDV` e a licença é sempre exigida; rodando do código-fonte ela só vale com
`licenca_exigir = S` nas configurações.

A licença é um código assinado (Ed25519) com a chave da loja e o último dia de validade. O PDV só guarda a chave
pública; a privada fica com o fornecedor, fora do repositório (`~/.pdv-casa/licenca_privada.key`):

```powershell
python -m tools.gerar_licenca emitir --loja CASAVERDE-01 --dias 30
```

O operador cola o código em "Código de licença..." na tela de entrada. O sistema avisa 7 dias antes de vencer, dá 5
dias de carência depois e nunca bloqueia com o turno aberto. Para criar o par de chaves (uma única vez) rode
`python -m tools.gerar_licenca novo-par` e cole a chave pública em `CHAVE_PUBLICA_HEX` (`src/core/licenca.py`); trocar a
chave invalida os códigos já emitidos.
