# WillPDV

**Autor:** Willyan

Sistema de ponto de venda offline-first para bares, casas noturnas e operações de
alimentação. O objetivo é evoluir para um PDV confiável de ponta a ponta: vendas,
mesas e comandas, turnos, pagamentos, estoque, clientes, financeiro, relatórios e
licença por servidor e atualizações pela nuvem.

> **Estado do projeto:** em desenvolvimento. O sistema local (cadastros, caixa, mesas,
> caderneta, entrega, estoque, contas, relatórios, utilitários e configurações dos
> manuais Willyan) está implementado em Python + SQLite + Tkinter e coberto
> por testes automatizados de regras e de telas. Ainda **não foi validado em loja**: não há
> emissão fiscal, TEF nem leitura real de balança, e a impressora térmica e a gaveta só foram testadas com
> impressora simulada (ver
> [`docs/ESPECIFICACAO.md`](docs/ESPECIFICACAO.md)), e a nuvem (atualizações) e a licença por servidor ainda não foram testadas em loja.

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

Usuário inicial: **ADM**, senha **ADM** (nível 4). Na primeira entrada o sistema obriga a trocar essa senha (vale para
qualquer operador cuja senha seja igual ao nome); depois crie os operadores em Manutenção de Cadastros > Operadores.
Cinco senhas erradas seguidas bloqueiam aquele usuário (ou a senha de supervisor) por 5 minutos. Operadores de nível 0
entram direto no caixa. O primeiro acesso ao caixa pede o número do turno e o valor do fundo de caixa.

O sistema local usa só a biblioteca padrão (Tkinter e SQLite). Quem usa a nuvem, a balança ou a
impressão RAW do Windows precisa de `pip install -r requirements.txt`.

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
- **Motivo do cancelamento** (Configurações > Caixa > *Exigir o motivo para cancelar item ou venda*, desligado de fábrica):
  ligado, o caixa pede o motivo ao cancelar um item ou a venda inteira e não aceita em branco. O motivo sai no fechamento
  e na Leitura X, em *Itens cancelados* e *Cupons cancelados*.
- **Consumação mínima** (Configurações > Mesas e serviço, desligada de fábrica): informe o valor mínimo por comanda. Na saída,
  a comanda com consumo abaixo do mínimo paga a diferença, que aparece no cupom e na pré-conta como *Compl. consumação mín.*
  Comanda sem nenhum item nunca é cobrada, e *vale a partir/até a comanda nº* deixa de fora as comandas das garotas. Mesa e
  balcão não são afetados. O desconto não burla o mínimo (vale o consumo já com desconto).
- **Sangria por horário** (Configurações > Caixa > *Horários de sangria*, ex.: `02:00, 04:30`): passou o horário e ninguém fez
  sangria depois dele neste turno, o caixa avisa na barra de estado ao fechar a próxima venda, junto do aviso por limite.
- **Auditoria por operador** (Relatórios > Caixa): por operador, cupons, vendido, ticket médio, desconto, cupons e itens
  cancelados e sangrias, para achar cancelamento ou desconto fora do normal.
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

## Proteção dos dados

- **Backup automático:** ao abrir o caixa (se a última cópia tem 12 h ou mais), a cada **troca de turno** e ao sair. Cada cópia é
  conferida depois de gravada; uma cópia danificada é descartada e o erro aparece. O painel inicial fica **vermelho** se o
  último backup tem 24 h ou mais, falhou ou nunca foi feito. Em Configurações > Utilitários, *Cópia extra do backup* grava a
  cópia também em pendrive, outro disco ou pasta de rede (o backup só no mesmo disco não protege de defeito no disco).
- **Restaurar backup** (Utilitários): escolhe a cópia; a restauração acontece na próxima abertura do programa e o estado de
  agora é guardado antes.
- **Integridade ao abrir:** o banco é conferido; se estiver danificado, o sistema oferece restaurar o último backup válido e
  guarda o banco ruim ao lado (`loja_offline.db.antes-AAAAMMDD-HHMMSS`), sem apagar nada.
- **Erros:** erro inesperado em qualquer tela ou thread vai para `logs/pdv.log` (com o traceback) e o operador vê uma mensagem
  clara. Utilitários > *Pacote de suporte* gera um zip só com os logs (nunca o banco) para enviar ao fornecedor.
- **Uma janela só:** abrir o PDV duas vezes no mesmo banco é recusado.
- **Comanda aberta na troca de turno:** continua aberta no turno seguinte; o dinheiro conta no turno em que for **pago**, então
  o caixa que passou o turno não dá falta e o que recebeu a comanda não dá sobra (teste em `tests/test_protecao.py`).

## Arquitetura

- `src/controllers/`: regras de negócio do PDV local.
- `src/database/`: esquema e acesso ao SQLite local.
- `src/hardware/`: impressora térmica ESC/POS (rede, serial, spooler, arquivo), logotipo BMP e interfaces de
  balança, gaveta e leitor.
- `src/core/`: formatação monetária, segurança, erros e utilitários.
- `src/ui/`: interface Tkinter (`app.py` é a janela principal, `caixa_ui.py` o caixa); telas Flet antigas congeladas.
- `tests/`: regras de negócio, telas (com um robô que opera as janelas modais) e o teste de fumaça.
- `src/sync/`: transporte PDV ↔ nuvem.
- `backend/`: API de nuvem (FastAPI) de avisos de versão; não é usada pelo PDV local.
- `pdv_licenca.py`: cliente do servidor de licença (criptografia e rede); as regras ficam em `src/core/servico_licenca.py`.

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

## Nuvem (só atualizações)

> Passo a passo para colocar a nuvem no ar e cadastrar boates: [`docs/NUVEM.md`](docs/NUVEM.md). A **licença** não é
> desta nuvem: é do servidor `/validar` e do bot do Telegram ([Licenciamento por servidor](#licenciamento-por-servidor-e-bot-do-telegram)).

Cada boate tem o seu PDV e as vendas ficam só nele (use o backup). A nuvem (`backend/`, FastAPI) **não recebe vendas e não
tem painel**: ela guarda a lista de lojas (cada uma com o seu token) e avisa sobre versão nova.

1. No servidor (`pip install -r backend/requirements.txt`), na raiz do repositório:

   ```powershell
   $env:PDV_API_TOKEN = "um-segredo-longo-e-aleatorio"      # token do administrador (lista de lojas)
   python -m backend.lojas criar BOATE-CENTRO "Boate Centro"  # uma vez por loja: mostra o token DESSA loja
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

   O token da loja aparece só na criação (a nuvem guarda apenas o hash); `python -m backend.lojas novo-token BOATE-CENTRO`
   troca um token vazado e `desativar`/`ativar` bloqueiam e liberam a loja.
2. No PDV, em Configurações > Nuvem, informe o endereço (`http://servidor:8000`), o token da loja e a chave da loja (a
   mesma usada no `criar`).
3. Deixe a verificação rodando em outra janela: `python -m src.app --sync` (no executável: `WillPDV.exe --sync`). Ela
   registra em `logs/sync.log`, espera cada vez mais se a nuvem cair e não faz nada se o endereço estiver vazio.

### Avisar as lojas sobre uma versão nova

A versão do PDV fica em `src/versao.py` (aparece no canto da tela principal). Para cada entrega:

1. Suba o número em `src/versao.py` (ex.: `1.1.0` → `1.2.0`) e gere o executável.
2. Publique na nuvem, com as notas que o dono da loja vai ler:

   ```powershell
   python -m backend.atualizacoes publicar 1.2.0 --notas "Corrige o troco em dinheiro." --url https://seu-site/WillPDV-1.2.0.zip
   python -m backend.atualizacoes publicar 1.2.1 --notas "Corrige perda de vendas na transferência." --critica
   python -m backend.atualizacoes listar
   ```

Cada caixa conectado consulta a nuvem ao abrir o menu e a cada 6 horas pela verificação, e mostra uma faixa no painel
("Nova versão 1.2.0 disponível"). Ao clicar, aparecem as notas de todas as versões que a loja ainda não tem e o botão
para baixar. `--critica` deixa a faixa vermelha e tira a opção "Não avisar desta versão": use para correções de dinheiro
ou de dados. O aviso some sozinho quando a loja instala a versão anunciada. O PDV não se atualiza sozinho de propósito:
uma instalação que falhasse no meio do expediente pararia o caixa.

Antes de operar comercialmente ainda é necessário: HTTPS (proxy reverso ou túnel), teste em loja com a
rotina real do caixa, backup e restauração testados, hardware fiscal/periféricos e homologação no ambiente da loja.

## Executável e instalador

`python build_pdv.py` gera o executável (PyInstaller) em `dist/WillPDV/`. No executável os dados (banco, Backup,
impressao, logs) ficam em `%LOCALAPPDATA%\WILL-PDV`. O executável já leva `pdv_licenca.py` e a biblioteca `cryptography`
(licenciamento por servidor, mais abaixo).

### Instalador (Inno Setup)

Na máquina do fornecedor que gera as versões (Windows, uma vez só): instale o Python 3.10+ (64 bits), rode
`pip install pyinstaller pyserial requests` e instale o [Inno Setup 6](https://jrsoftware.org/isdl.php) (6.3 ou mais
novo). A cada versão:

1. Suba o número em `src/versao.py`.
2. Na raiz do repositório: `python build_pdv.py`. Ele gera o executável e, achando o Inno Setup, o instalador
   `instalador\saida\WillPDV-Setup-<versão>.exe` (o script é `instalador\WillPDV.iss`; dá para abri-lo no Inno Setup e
   clicar em *Compile*). Ícone opcional: `instalador\willpdv.ico`.
3. Leve o `WillPDV-Setup-<versão>.exe` ao PC do caixa (pendrive ou link) e execute: Avançar, Avançar, Instalar. Ele
   instala em `Arquivos de Programas\WillPDV`, cria o atalho e, se marcado, abre o caixa ao ligar o computador.

Para atualizar, rode o instalador novo no mesmo PC (com o turno fechado): ele substitui o programa e mantém as vendas,
que ficam em `%LOCALAPPDATA%\WILL-PDV`. Desinstalar também não apaga esses dados; faça o backup antes de trocar de PC.

## Licenciamento por servidor e bot do Telegram

Esta é a licença **por computador**: cada caixa se identifica (`machine_id`), pergunta ao seu servidor se pode funcionar e
guarda a resposta assinada por 7 dias. Quem administra tudo (criar licença, bloquear, trocar de computador) é o seu **bot
do Telegram**, que conversa com o servidor. O PDV nunca fala com o Telegram: só com o servidor.

```text
   Você  ──Telegram──►  Bot  ──►  Servidor  ◄── POST /validar ──  PDV (cada caixa)
                                  (guarda as licenças e                (só tem a chave PÚBLICA)
                                   a chave PRIVADA)
```

> **O servidor `/validar` e o bot do Telegram não estão neste repositório.** Aqui está só o lado do PDV (arquivos
> `pdv_licenca.py`, `src/core/servico_licenca.py` e `src/ui/licenca_ui.py`). Os passos 1 a 3 descrevem o que o servidor e o
> bot precisam fazer para o PDV funcionar; os comandos exatos do bot são os do seu bot.

> **Este é o único sistema de licença do PDV.** A licença mensal antiga (código `PDVL1`, `tools/gerar_licenca.py` e a
> renovação por `/v1/licenca` na nuvem) foi removida. Enquanto `SERVER` e `PUBLIC_KEY_PEM` não forem preenchidos (passo 4),
> o PDV roda **sem nenhuma exigência de licença**.

### Passo 1: gerar o par de chaves (uma vez só)

O servidor assina com a chave **privada**; o PDV confere com a chave **pública**. Gere o par no seu computador:

```powershell
openssl genpkey -algorithm ED25519 -out licenca_servidor.key
openssl pkey -in licenca_servidor.key -pubout -out licenca_servidor_publica.pem
```

Sem o `openssl` no Windows, use o Python (precisa de `pip install cryptography`):

```powershell
python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as K; from cryptography.hazmat.primitives import serialization as s; k=K.generate(); open('licenca_servidor.key','wb').write(k.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption())); open('licenca_servidor_publica.pem','wb').write(k.public_key().public_bytes(s.Encoding.PEM, s.PublicFormat.SubjectPublicKeyInfo))"
```

- `licenca_servidor.key` é a **privada**. Vai **só** para o servidor (como variável de ambiente ou arquivo secreto). Nunca vai
  para o GitHub, para o PDV, para o bot nem para ninguém. O `.gitignore` já ignora `*.key`. Faça uma cópia segura (se
  perder, todos os caixas precisam de uma chave pública nova).
- `licenca_servidor_publica.pem` é a **pública**: é a que entra no PDV (passo 4). Não é segredo.

### Passo 2: o que o servidor precisa responder

`POST {SERVER}/validar` com `{"license_key": "...", "machine_id": "..."}`.

| Situação no servidor | Resposta |
|---|---|
| Licença em dia, máquina vinculada a ela (ou ainda sem máquina: vincula a primeira que pedir) | `200` `{"status": "ok", "payload": "...", "signature": "..."}` |
| Mensalidade em atraso (ainda liberada) | `200` com `"status": "atraso"` (o PDV mostra uma faixa de aviso, sem bloquear) |
| Você bloqueou a licença | `403` `{"status": "bloqueada"}` |
| Chave que não existe | `403` `{"status": "invalida"}` |
| Chave já vinculada a **outro** computador | `403` `{"status": "outra_maquina"}` |

O que o PDV exige do `200`:

- `payload` é um **texto** JSON, por exemplo `{"license_key": "A1B2-C3D4", "machine_id": "<o mesmo recebido>", "exp": 1790000000}`.
  `exp` é o vencimento em segundos Unix (7 dias à frente). Também são aceitos `expira_em`, `expires_at` ou `valido_ate` (data ISO 8601),
  ou `iat`/`emitido_em` (aí vale emissão + 7 dias).
- `signature` é a assinatura Ed25519 dos bytes UTF-8 **desse mesmo texto** `payload`, em base64 comum. O texto tem que
  seguir byte a byte como foi assinado (não reserialize o JSON depois de assinar).
- Se `machine_id` ou `license_key` vierem no payload, têm que ser os da requisição; senão o PDV recusa o token.
- Use **HTTPS** (o PDV recusa `http://`, exceto `localhost`, porque a chave da licença viaja no corpo do pedido).

### Passo 3: o que o bot precisa conseguir fazer

Se o seu bot já existe, só confira se ele cobre isto (cada item termina em uma mudança no banco do servidor):

| Ação | Para quê |
|---|---|
| Criar uma licença para uma boate (gera a `license_key`) | Cliente novo: você manda a chave para ele |
| Consultar uma licença (status, até quando pagou, `machine_id` vinculado) | Conferir o cliente |
| Marcar mensalidade em atraso / em dia | Faixa de aviso no caixa; depois do prazo, bloquear |
| Bloquear e desbloquear | `bloqueada` no caixa (o caixa só bloqueia quando não há venda ou comanda aberta) |
| **Liberar ou trocar o computador** (limpar ou alterar o `machine_id` vinculado) | Cliente trocou de PC: sem isso aparece `outra_maquina` |

Se ainda vai criar o bot no Telegram:

1. No Telegram, abra o **@BotFather**, mande `/newbot`, escolha nome e usuário (termina em `bot`). Ele devolve o **token do bot**.
2. Guarde o token só no servidor onde o bot roda (variável de ambiente), nunca no PDV nem no repositório.
3. Faça o bot responder **somente ao seu usuário** (confira o `id` numérico do remetente a cada comando). Qualquer pessoa
   que ache o bot não pode criar nem liberar licença.
4. Faça o bot usar a mesma chave privada do passo 1 só através do servidor (o bot não precisa conhecê-la se o servidor assina).

### Passo 4: configurar o PDV (você, antes de gerar a versão)

1. Abra `src/core/servico_licenca.py` e troque os dois valores marcados como PREENCHER:

   ```python
   SERVER = "https://licencas.seudominio.com.br"     # sem barra no final
   PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
   (as linhas do arquivo licenca_servidor_publica.pem)
   -----END PUBLIC KEY-----"""
   ```

   Enquanto os textos `COLE-AQUI` estiverem lá, o licenciamento por servidor fica **desligado** e o PDV funciona como antes.
2. Gere a nova versão: `pip install -r requirements.txt` e `python build_pdv.py` (veja [Instalador](#instalador-inno-setup)).
   O `.exe` já leva `pdv_licenca.py` e a biblioteca `cryptography` por dentro.
3. (Opcional) Em cada caixa, em **Configurações > Configurações > Nuvem**, preencha **Contato de suporte mostrado na tela de
   bloqueio** com o seu contato (por exemplo `@seu_bot`). Sem isso aparece "Fale com o suporte do fornecedor.".

### Passo 5: ativar uma boate (o dia a dia)

1. No bot, crie a licença da boate e copie a **`license_key`**.
2. No caixa novo, abra o PDV. Na primeira vez ele pede a chave: cole e confirme.
3. O caixa se vincula ao computador na primeira validação. Para conferir, abra **Utilitários > Licença**: aparecem o status,
   a licença com só os 4 últimos caracteres e o **ID da máquina** (botão Copiar). É esse ID que o bot guarda.
4. Pronto. Daí em diante o PDV confere ao abrir e a cada 4 horas, sempre em segundo plano, sem travar a tela.

### Casos comuns

| O que aconteceu | O que o operador vê | O que você faz |
|---|---|---|
| Internet caiu | Nada: segue com o último token salvo (vale até 7 dias) | Nada |
| Mais de 7 dias sem internet nem validação | Tela "Licença não liberada" (não foi possível confirmar) | Voltar a internet e clicar **Tentar novamente** |
| Mensalidade atrasou | Faixa amarela no painel, o caixa continua | Regularizar com o cliente e marcar em dia no bot |
| Bloqueio pelo bot | Tela de bloqueio, mas **só quando não há venda ou comanda aberta** | Desbloquear no bot; o operador clica **Tentar novamente** |
| Trocou de computador | `outra_maquina` | No bot, liberar/trocar o computador da licença; no PC novo, **Tentar novamente** |
| Chave digitada errada | `invalida` | **Informar outra chave** na própria tela de bloqueio |

O token fica em `%LOCALAPPDATA%\WILL-PDV\licenca.json` e a chave de licença na configuração do caixa. Nenhum dos dois vai
para o log do PDV.

### Testar antes de usar em loja

1. Rode o servidor (ou um servidor de teste) em `http://localhost:8000` e ponha `SERVER = "http://localhost:8000"` só na sua máquina de teste.
2. `python -m src.app`: ele pede a chave. Confira **Utilitários > Licença**.
3. Faça o servidor responder `403 bloqueada` e abra uma comanda: nada acontece até a comanda fechar; depois a tela de bloqueio aparece.
4. Desligue a internet e reabra o PDV: ele segue com o token salvo.
5. Antes de entregar a uma loja, gere o `.exe` (`python build_pdv.py --sem-instalador`) e repita 2 a 4 com ele.
