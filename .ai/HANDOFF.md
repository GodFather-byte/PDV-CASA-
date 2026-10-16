# HANDOFF

## Último trabalho: excluir produto cadastrado (liberar código já usado)
- `entidades._excluir_produto` (campo `excluir_fn` da Entidade; `CadastroController.excluir` chama e devolve um texto para a tela).
  Sem venda: apaga de verdade (composição, itens/movimentos de estoque dele). Já vendido: fica inativo e o código vira `COD~id`,
  o nome ganha " (excluído id)", atalho e código de barras são limpos, liberando tudo para produto novo. Recusa se está em mesa,
  comanda ou venda aberta.
- Tela: `cadastros_tk.excluir` mostra o aviso quando o produto foi guardado em vez de apagado.
- Teste: `tests/test_excluir_produto_cadastrado.py`. Suíte inteira: 1.229 OK.

## Anteriores (já mesclados)
Limite de R$ 200 por comanda de cliente (`limite_comanda`, PR #50); modo claro/escuro (`src/ui/paleta.py`, PR #49).

## Pendências
Nenhuma.
