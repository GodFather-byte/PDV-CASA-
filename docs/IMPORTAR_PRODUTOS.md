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
