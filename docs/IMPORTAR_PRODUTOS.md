# Importar produtos em massa (planilha)

Cadastros > Produtos > **Importar planilha**. Serve para cadastrar de uma vez a lista de produtos de uma casa nova, atualizar
preços em massa ou levar o cardápio de outro sistema. O PDV **não traz produtos prontos**: cada casa importa os seus.

## Passo a passo
1. **Baixar planilha modelo** (ou **Exportar produtos atuais**, para editar preços e importar de volta). Os arquivos são CSV com ";",
   que o Excel brasileiro abre direto; também dá para importar um `.xlsx`.
2. Preencha. Só **Produto** e **Preço** são obrigatórios; os títulos aceitam variações ("Bebida", "Valor", "Código"...).
3. **Escolher a planilha**. O PDV mostra a **prévia**: o que vai ser criado (verde), atualizado (azul) ou recusado (vermelho, com o
   motivo na última coluna). **Nada é gravado até você clicar em Importar** (botão verde logo acima da lista, à direita). Se algo falhar no meio, nada fica pela metade.

## Colunas
| Coluna | Para quê |
| --- | --- |
| Código | número do produto. Em branco: o PDV numera em sequência (1, 2, 3...), pulando os que já existem |
| Produto | nome (até 50 letras; vira MAIÚSCULAS, opção desligável) |
| Preço | preço de venda (`10,00` ou `R$ 10,00`) |
| Comissão (R$) | quanto a garota ganha por unidade; o PDV converte para o percentual do produto (R$ 15 em R$ 45 = 33,33%) |
| Grupo | cria o grupo se não existir; vazio = DIVERSOS |
| Unidade | UN, KG... (vazio = UN) |
| Quantidade | estoque inicial: o produto passa a controlar estoque e o saldo vira um lançamento "Inicial" |
| Estoque mínimo | ponto de pedido |
| Código de barras, Atalho | opcionais |
| Controla estoque | `S` para controlar começando em zero (para contar depois no painel de estoque) |

## Regras de código
* **Códigos reservados do caixa** (comissão das garotas, 50 por padrão, e saída da comanda, 1002) **nunca** são usados em produto: na
  numeração em sequência são pulados e, se a planilha trouxer um deles, a linha é recusada.
* *Usar o código da planilha*: respeita a coluna; os sem código recebem o próximo livre. *Numerar tudo em sequência*: ignora a coluna e
  numera a partir do número que você escolher.
* Produto que já existe (mesmo código, ou mesmo nome sem código) é **atualizado**; dá para desligar essa opção.
* **Código repetido na planilha:** cada código é de um produto só (é o que o caixa usa para achar o item). Se a mesma linha de código
  aparecer duas vezes, a segunda é recusada na prévia ("aparece de novo na linha N"): dê um número livre a ela.
* **Produto guardado** (já vendido e inativo, depois de *Excluir todos os produtos*): se a planilha traz o nome dele com outro código,
  ele volta a valer **com o código da planilha**; se a planilha quer o código que ele ocupa para outro produto, ele cede o código
  (passa para um código de arquivo, de 10.000.000 em diante) e **mantém o nome**, para o histórico das vendas não mudar.

## Começar do zero: excluir todos os produtos
Para cadastrar a tabela inteira de novo, use **Excluir todos os produtos...** (botão no alto da janela de importação, ou
**Utilitários > Excluir todos os produtos**; só o administrador, nível 4). A tela mostra os números e só executa depois de você digitar
**APAGAR**.
* Um **backup é feito antes** (o caminho aparece no fim); para desfazer, restaure esse backup em Utilitários > Restaurar backup.
* Com mesa, comanda ou balcão **abertos com itens**, a exclusão é recusada: feche ou cancele antes.
* **Produto que já foi vendido não é apagado**, porque o cupom, os relatórios e os estornos dependem dele. Ele fica **guardado como
  inativo** (some do caixa e das listas) e volta a valer, com o preço novo, quando a planilha trouxer o mesmo código ou nome (a prévia
  avisa "estava inativo"). Os demais são excluídos de verdade, com o estoque, os movimentos de estoque e as composições deles.
* Grupos, subgrupos e unidades **ficam**; os códigos dos produtos excluídos ficam livres para a planilha nova.

## A tabela da casa (`docs/produtos_da_casa.csv`)
Planilha pronta com os 31 produtos da folha de preços do salão, já com os **códigos da folha** (use *Usar o código da planilha*, que é o
padrão). Na folha, os códigos 6 (Catuaba, Fogo Paulista e Montila), 25 (Whisk Nasc. e Capirinha) e 20 (Ice e Long Neck) se repetiam; como
cada código é de um produto só, Fogo Paulista ficou com 7, Montila com 8, Capirinha com 22 e Long Neck com 21 (números que não estavam
em uso). A Música não tem código na folha e recebe o primeiro número livre (9). Confira os preços e as comissões antes de importar.
