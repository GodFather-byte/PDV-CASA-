# Handoff

Atualizado por: Claude em 2026-10-15

## Objetivo atual

Pedido do dono: um modo de excluir todos os produtos cadastrados de uma vez, para cadastrar a tabela de novo (importação).
Branch `claude/great-clarke-s4any5` (o PR #47, da tela do caixa, já foi mesclado).

## Feito nesta sessão

- `UtilitarioController.resumo_exclusao_produtos` / `excluir_todos_produtos`: backup antes; recusa com venda aberta com itens;
  apaga os produtos SEM venda (com composições, itens e movimentos de estoque, e lançamentos de estoque que ficaram vazios) e
  deixa INATIVOS os que já saíram em venda (`itens_venda`/`itens_venda_partes`), porque o histórico depende deles.
- Importação (`importacao_produtos.py`): produto achado por código/nome que estava inativo volta a ficar ativo ao ser
  atualizado, e a prévia avisa ("estava inativo"). Isso vale também fora da exclusão em massa.
- Telas: `utilitarios_ui.excluir_produtos` (mostra os números, exige digitar APAGAR); item novo em Utilitários
  (`util_excluir_produtos`, nível 4) e botão "Excluir todos os produtos..." na janela de importar (desligado sem nível).
- `docs/IMPORTAR_PRODUTOS.md` com a seção "Começar do zero".
- **Códigos exatos da planilha**: produto guardado (inativo) não prende código — se a planilha traz o nome dele com outro código,
  ele assume o código novo (`atualizar`); se a planilha quer o código que ele ocupa para outro produto, ele cede (`liberar_id`,
  `_arquivar_codigo`: código de arquivo ≥ 10.000.000, nome intacto). Código repetido na planilha continua recusado (o código é único).
- **`docs/produtos_da_casa.csv`**: os 31 produtos da folha de preços do dono (fotografada) com os códigos da folha; os 3 "6", 2 "25" e
  2 "20" repetidos ganharam 7, 8, 22 e 21. Leitura da folha (preços corrigidos à mão, Cerveja 15, Vodka 45, Campari 45/15, Suco código 3,
  Combo 10 latas código 23 por 120) a confirmar com o dono.

## Validação

- `tests/test_excluir_produtos.py` (28): regra, histórico, estoque, reimportação, códigos exatos (CSV da casa) e telas.

## Pendências e armadilhas

- Quem quiser apagar também o histórico de vendas usa a Limpeza do movimento antes; só então os produtos vendidos deixam de ficar
  guardados? Não: a limpeza apaga vendas ANTERIORES a uma data e as ligações somem, então uma nova exclusão total as apaga de vez.
- Validar com o dono: exclusão total + importação da planilha no Windows da loja.
- Equipamentos reais, emissão fiscal, TEF e validação em loja continuam pendentes.

## Como rodar e testar

Ver `AGENTS.md`. Neste ambiente de nuvem o Python 3.13 não tem Tk; use `python3.12` (com `python3-tk`) e
`xvfb-run -a -s "-screen 0 1920x1080x24" python3.12 -m unittest discover -s tests`.
