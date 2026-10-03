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
> emissão fiscal, TEF nem leitura real de balança, e a impressora térmica e a gaveta só foram testadas com
> impressora simulada (ver
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
- **Relatórios e impressão:** relatórios de vendas/gestão e cupom não fiscal com saída em tela, arquivo,
  impressora do Windows ou **impressora térmica ESC/POS** (fila com reenvio automático, gaveta, vias e
  logotipo; ver [Impressão térmica](#impressão-térmica)), Leitura X e Redução Z gerenciais. Não há emissão
  fiscal nem homologação de periféricos.
- **Dados para nuvem:** `SyncController` monta lotes identificados por UUID e
  registra apenas confirmações explícitas do servidor.
- **Qualidade:** a suíte cobre regras de caixa, estoque, cadastro, formatação,
  segurança e banco local. Rode os testes antes de integrar alterações.

## Mesas e comandas

No caixa, o campo **Comanda** (tecla **F4**) recebe só o número: digite `123` e Enter para abrir a comanda 123 (vai até
10 mil), e depois os **códigos dos produtos** no campo ao lado (ex.: `2` para a Skol). A **mesa** leva um `M`: `M5` é a
mesa 5. `C123` também vale. O `0` é o balcão. O número sem letra nunca é lido no campo do código, porque lá ele é o código do
produto; para trocar de comanda sem sair de lá, digite `C123` ou `M5` (ou bipe o cartão): se não existir produto com esse
código/atalho, a posição é aberta e os itens seguintes caem nela.

Quem prefere a notação de restaurante (o número sem letra é a mesa e a comanda leva `C`) muda em **Configurações > Mesas e
serviço > Número digitado sem letra no caixa é**. As telas, as listas e os relatórios sempre mostram a posição do mesmo jeito
que se digita.

No **rodapé** do caixa ficam os ícones das posições abertas, cada um com o número e o total embaixo: o **Balcão** (primeiro
ícone), a **mesa** (mesinha com garrafa e copo), a **comanda** (cartão, ex.: `123`), a **conta enviada** (conta sobre a
bandeja) e o **relógio** nas paradas além do tempo de inatividade. A **garota** com comissão a pagar aparece com uma **estrela**
(ver [Comissão das garotas](#comissão-das-garotas)). O ícone da venda que está na tela tem a borda grossa.
São mostradas duas linhas; havendo mais, a faixa rola (barra ou roda do mouse).

- **Esc volta ao "marcar comanda":** com a venda em andamento, Esc leva ao campo da posição, com o número selecionado:
  digite `7` (comanda 7) ou `M7` (mesa 7) e Enter. Com um produto escolhido (esperando a quantidade), o Esc só cancela o produto. Um segundo Esc
  volta ao balcão; as mesas e comandas abertas continuam gravadas.
- **Escolher um ícone:** clique nele, ou seta para baixo no campo da posição e então setas, **Enter** (chama), **T**
  (outras posições vêm para a escolhida) e **Esc** (volta ao campo). Digitar um número, `C` ou `M` com o foco nos ícones já
  começa a marcar a posição; `0` é o balcão.
- A comanda funciona como uma mesa com **numeração própria**: a comanda 2 e a mesa 2 (`M2`) existem ao mesmo tempo.
- Tudo o que vale para a mesa vale para a comanda: serviço, desconto, pré-conta (impressa como "CONTA DA COMANDA"),
  F10 (transfere tudo), T (várias para uma) e a transferência de parte dos itens, inclusive entre mesa e comanda
  (ex.: F10 e `2` levam a mesa 5 para a comanda 2; `M5` leva uma comanda para a mesa 5).
- Em **Configurações > Mesas e serviço**: *Número digitado sem letra* (comanda ou mesa), *Número de comandas* (padrão 10000; **0 desliga as comandas**), *Cobrar serviço
  nas comandas* e *Mostrar sempre os ícones das mesas e comandas abertas no rodapé do caixa* (desligado, eles só aparecem
  com Esc/F4 e somem ao escolher uma posição).
- Relatórios: "Mesas e comandas" mostra a posição como `123` (comanda) ou `M5` (mesa); o filtro *Modalidade* separa `mesa` de `comanda`.
- A **nuvem** ainda recebe a comanda como venda de mesa (o contrato de sincronização não mudou).

## Comissão das garotas

Na boate as garotas ganham comissão pelas bebidas. O número de cada garota (156, 180...) é o mesmo da comanda dela, e o
**código 50** do caixa é o das comissões. Tudo acontece **na própria tela do caixa**, a mesma do balcão, sem abrir janela:

1. No campo **Comanda**, digite o número da garota (ex.: `180`) e Enter.
2. No campo do código, digite `50` e Enter. A linha de entrada vira **Garota nº** (já com o 180; a Descrição mostra o nome,
   se ela estiver cadastrada) e **Valor (R$)**, e o cursor já vai para o valor.
3. Digite o **valor da comissão** (ex.: `25` ou `25,00`) e Enter. Ficou marcado no número dela e **a via da garota sai na
   impressora**.

Fora de comanda (no balcão, por exemplo) o cursor começa em *Garota nº*: digite o número e Enter para ir ao valor. A seta
para cima volta do valor ao número (para lançar em outra garota) e **Esc cancela** a comissão. O 50 nunca vira produto nem
entra na venda: a comanda da garota continua vazia e some sozinha, e a comissão fica guardada.

- **A via da garota:** a cada comissão lançada sai uma via (não fiscal) para ela acompanhar: o *valor desta comissão*, a lista
  de tudo o que ela tem a receber (os lançamentos pendentes, os 15 mais recentes) e o *total a receber*, com hora e operador.
  Sem impressora configurada (modo "tela") a via só fica gravada na pasta `impressao/` e a barra de estado avisa; falha na
  impressora nunca desfaz o lançamento. Em Configurações > Caixa: *Imprimir a via da garota a cada comissão lançada*.
- **As garotas ficam à vista no rodapé:** junto com o balcão, as mesas e as comandas, a garota com comissão a pagar aparece
  como um ícone (estrela, com o valor a pagar embaixo); clicar abre a comanda dela. Se ela também tem consumo aberto, o ícone
  da comanda ganha um selo com a estrela. Em Configurações > Mesas e serviço: *Mostrar no rodapé do caixa as garotas com
  comissão a pagar*.
- **A comanda mostra o que foi marcado nela:** ao abrir a comanda da garota (ex.: `180`), as comissões marcadas aparecem
  na lista, em verde (código 50, `COMISSÃO (a pagar)`, valor, hora e operador), e a faixa verde de cima mostra o total a pagar.
  As pagas neste turno ficam em cinza, para saber se já foi paga; as canceladas somem. É só leitura e não é venda: o
  Total continua sendo o dos itens. Comanda de cliente e mesa não mostram nada disso (mas uma comissão lançada por engano no
  número de um cliente aparece nela, o que ajuda a achar o erro).
- **Pagar e cancelar sem sair da tela:** **F12** na comanda da garota paga tudo o que está pendente: o dinheiro sai da gaveta
  (uma sangria "Comissão garota 180 NOME", então a conferência do caixa já conta), a gaveta abre e sai um **recibo** com a
  linha de assinatura; desmarcando a opção, paga fora do caixa (só dá baixa). Se a comanda também tem consumo, o F12 pergunta o
  que pagar. **Delete** numa linha de comissão cancela aquele lançamento (pede confirmação e, se o operador não tem nível, a
  senha de supervisor, como no cancelamento de item); comissão já paga não se cancela.
- **Contra erro de digitação:** havendo garotas cadastradas, um número que não está no cadastro (ou de garota inativa) pede
  confirmação, e valor acima de R$ 500,00 também.
- **Comissões** (botão na barra do caixa): a lista geral, com o que há a pagar a cada garota e os lançamentos dela, para pagar
  ou cancelar de uma vez. É um atalho: o dia a dia se faz na tela do caixa.
- **Troca de turno:** avisa se há comissão a pagar (pague antes de contar a gaveta). O fechamento e a Leitura X trazem a seção
  *Comissões das garotas*: o lançado no turno, por garota, e o total que ainda falta pagar. O pagamento aparece nas sangrias.
- **Relatório:** Relatórios > Caixa > *Comissão das garotas*, por garota (total, pago e a pagar) ou lançamento a lançamento, com
  filtro de período, turno, garota e situação.
- **Cadastro:** Manutenção de Cadastros > *Garotas* (número, nome, ativa). É opcional: serve para mostrar o nome e conferir o número.
- **Configurações > Caixa:** o *código* que lança a comissão (50; vazio desliga; não pode ser o de um produto), *Exigir senha
  de supervisor para lançar comissão* (desligado de fábrica) e *Marcar, pagar e cancelar a comissão na própria tela do caixa*
  (ligado; desligado, o 50 abre a janela *Comissão da garota* e o pagamento e o cancelamento ficam só no botão *Comissões*).
  Pagar segue a regra da sangria e cancelar a do cancelamento.
- A comissão **não é venda**: não entra no faturamento, no estoque nem na nuvem. Só vira movimento do caixa quando é paga.

## Fechamento do turno

Além dos totais e da conferência do dinheiro, o fechamento (e a Leitura X) traz a **conferência do turno**, para auditar a
noite:

- **Posições em aberto:** mesas e comandas com consumo que ficaram abertas, com o total de cada uma e a soma. Ao trocar o
  turno, o caixa avisa quais são (elas continuam abertas no turno seguinte).
- **Cupons cancelados** (cupom, onde era, valor, motivo e quem cancelou) e **itens cancelados** (hora, onde, produto,
  quantidade, valor e quem cancelou).
- **Transferências** entre mesas e comandas (inteira, várias para uma ou parte dos itens): de onde para onde, valor e quem fez.

No painel do fechamento aparecem as contagens e o botão **Conferência do turno** mostra o detalhe na tela; na fita
impressa as seções só saem quando há ocorrências (a linha das posições abertas sai sempre, com "nenhuma" se não houver).

### Fechamento para passar o caixa

Ao **trocar o turno** o fechamento sai **sozinho na impressora**, pronto para o caixa que sai entregar ao gerente ou ao
caixa que entra. Ele mostra tudo da noite e termina com o que o gerente precisa para receber o caixa:

- os totais, os recebimentos, o **valor esperado**, o **valor final** que o operador declarou e o resultado em letra grande:
  **SOBROU R$ x**, **FALTOU R$ x** ou **CAIXA CONFERIDO**;
- a lista das **sangrias e suprimentos** do turno (hora, valor, motivo e quem fez), com os pagamentos de comissão;
- a conferência do turno e a seção das comissões das garotas;
- no fim, o espaço da **justificativa da diferença** (só se sobrou ou faltou) e as linhas de assinatura do **caixa responsável**
  (quem fechou o turno, com o nome) e do **gerente / quem recebe o caixa**.

Em Configurações > Caixa: *Imprimir o fechamento ao trocar o turno* (ligado) e *Vias do fechamento* (1 a 3; ex.: uma fica no
caixa e outra com o gerente). Sem impressora configurada (modo "tela") nada sai sozinho: o painel do fechamento tem o botão
*Imprimir Fechamento*, que serve também para reimprimir. Falha ao imprimir avisa e o turno fecha do mesmo jeito. A Leitura X
(parcial, no meio do turno) lista as sangrias, mas não leva resultado nem assinatura.

## Controles de caixa de boate

Pesquisando como funciona o caixa de uma boate (comanda de consumo, conferência na saída, sangrias, cancelamentos), entraram
dois controles. Outras ideias, que mudam regras ou o banco, estão em `docs/ESPECIFICACAO.md` (seção 3).

- **Consulta Comanda** (botão da barra do caixa): na saída, digite a comanda (ou `M5`) e veja se está **PAGA** (cupom, valor e
  hora), **ABERTA - A PAGAR** (valor e itens) ou sem registro. Vale a venda mais recente daquele número, porque o cartão da
  comanda é reutilizado a noite toda. Não mexe na venda que está na tela; no número de uma garota mostra também a comissão a pagar.
- **Alerta de sangria** (Configurações > Caixa > *Avisar para fazer sangria quando o dinheiro da gaveta passar de*, em R$; 0
  desliga): ao fechar uma venda, se o dinheiro esperado na gaveta passou do limite, a barra de estado fica laranja pedindo a
  sangria (F7). Só avisa que passou: não mostra quanto há, para o operador seguir contando a gaveta sem ver o esperado.
- **Sem programação nova:** *taxa de comanda perdida* e *consumação mínima na entrada* se fazem cadastrando um produto
  (ex.: `TAXA COMANDA PERDIDA`) e lançando-o na comanda.

## Impressão térmica

O caixa imprime em impressora térmica ESC/POS (Epson TM, Bematech, Elgin, Tanca e compatíveis; 58 mm ou 80 mm). Cupom,
pré-conta, pedido de entrega, comprovante de sangria, fechamento do turno, recibo e via da comissão das garotas e Leituras X/Z saem por ela. Todos são
**não fiscais**.

**Configurar** (Configurações > Máquinas):

1. *Impressão de cupons e relatórios* = **Impressora térmica (ESC/POS)** e *Colunas da fita* = 48 (80 mm) ou 32 (58 mm).
2. **Escolha a impressora na lista do computador:** clique em *Escolher impressora do computador* (ou em *Escolher da
   lista...* ao lado do endereço). O PDV mostra as impressoras instaladas neste Windows, com a porta, o driver e a
   situação, e as portas COM. As que parecem de cupom (Epson TM, Bematech, Elgin, POS-80...) vêm primeiro; PDF e fax
   ficam por último. Use *Imprimir página de teste* na linha escolhida e então *Usar esta*: a conexão e o nome são
   preenchidos sozinhos. Não apareceu a sua? Instale o driver dela no Windows, ligue o cabo e clique em *Atualizar*.
   Sem a lista, preencha *Conexão* e *endereço* à mão:

   | Conexão | Endereço | Observação |
   |---|---|---|
   | Rede (TCP/IP) | `192.168.0.50` ou `192.168.0.50:9100` | Não instala nada; a porta padrão é 9100. |
   | Serial (COM) | `COM3` ou `COM3:19200` | Velocidade padrão 9600; exige `pip install pyserial`. |
   | Impressora do Windows | o nome que o Windows mostra, como `CAIXA` | Usa o spooler do Windows, sem instalar nada. Se a impressora estiver desligada, o Windows guarda o trabalho. |
   | Arquivo/dispositivo | `C:\saida.prn` ou `\\.\COM3` | Grava os bytes; serve para conferir sem impressora. |
3. *Página de código* (CP850 é o padrão; troque se os acentos saírem errados), *cortar o papel*, *gaveta ligada à
   impressora* e *pino da gaveta* (0 ou 1).
4. Confira em Utilitários > **Fila de impressão** > *Imprimir página de teste*.

**Como imprime**

- **Fila:** o documento é gravado no banco na hora e uma thread o envia. Impressora desligada ou fora da rede não
  trava o caixa: o documento espera e sai sozinho quando ela volta (novas tentativas após 5, 10, 20, 40 e 60 s,
  e depois a cada minuto; passada cerca de uma hora vira *erro* e aguarda o operador). A ordem de cada destino (caixa e
  cozinha/bar) é preservada. Os já impressos ou cancelados saem da lista depois de 7 dias; pendentes e com erro nunca
  são apagados sozinhos.
- **Indicador:** o alto do caixa mostra *Impressora: ok*, *Impressora fora? N na fila* ou *N com erro (reenviar)*. Clicar
  nele abre a **fila**, onde se reenvia, cancela e limpa (também em Impressora > Fila de impressão, no caixa, e em
  Utilitários).
- **Gaveta:** abre pelo pulso da própria impressora (com *Gaveta ligada à impressora* marcada) quando alguma forma de
  pagamento da venda tem a marca *Fica na gaveta* (dinheiro, cheque e ticket, de fábrica) ou quando há troco, e também
  na sangria e na tecla **F11**. Cartão e Pix não abrem a gaveta.
- **Vias:** o cupom sai com o maior *Nº de vias* (1 a 3) entre as formas de pagamento usadas (Manutenção de Cadastros >
  Tipos de Pagamento), com corte entre as vias; a gaveta abre uma vez só. O fechamento do turno usa *Vias do fechamento*
  (Configurações > Caixa).
- **Logotipo:** informe o caminho de um BMP em Configurações > Loja e ligue *Imprimir o logotipo da loja no cupom*
  (Configurações > Máquinas). Vale BMP sem compressão de 1, 4, 8, 24 ou 32 bits; imagem mais larga que o papel é
  reduzida. Só o cupom, a pré-conta e o pedido de entrega levam o logotipo. Arquivo ausente ou inválido não impede a
  venda: o cupom sai sem logotipo e o motivo fica no log (`logotipo_invalido`).
- **2ª via:** Impressora > Reimprimir último cupom (ou por número) reimprime o cupom marcado como 2ª via.
- **Cozinha/bar:** a *impressora remota*, em rede ou do Windows (também escolhida na lista), usa a mesma fila. A opção
  *Pasta de arquivos* só grava os pedidos.

**Limites:** não há ECF, NFC-e, SAT nem TEF. A lista de impressoras foi conferida num Windows real (achou uma Epson TM-T
USB), mas a impressão em papel ainda não foi validada: os testes usam impressora TCP simulada, spooler simulado e arquivos. A página de código, o corte, a gaveta e a velocidade serial variam por modelo; use a página de teste.
A fila só sabe se a impressora aceitou os bytes: falta de papel e tampa aberta não são detectadas (o documento conta
como impresso; reimprima pela 2ª via).

## Arquitetura

- `src/controllers/`: regras de negócio do PDV local.
- `src/database/`: esquema e acesso ao SQLite local.
- `src/hardware/`: impressora térmica ESC/POS (rede, serial, spooler, arquivo), logotipo BMP e interfaces de
  balança, gaveta e leitor.
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
