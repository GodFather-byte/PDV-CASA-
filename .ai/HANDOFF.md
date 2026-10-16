# HANDOFF

## Último trabalho: vale da garota vale para dinheiro e Pix
- `ComissaoController.pagar(..., pix_cent, vale_cent)`: o vale (que já saiu do caixa quando a garota o pegou) é descontado do TOTAL
  do acerto; `a_pagar = total - vale`; `pix_cent` é a parte de `a_pagar` paga por Pix e o resto é dinheiro (única parte que vira
  sangria e comprovante de saída). Vale não pode passar do total. Vale gravado em `acertos_garotas.vale_cent` (esquema v16).
- Janela *Pagar comissão*: campo do vale antes do total ("Total - vale = a pagar"); "Tudo no Pix" paga `total - vale`.
- Recibo: "Vale (já recebido)"; sem Pix não mostra a linha do Pix. Substitui a regra anterior ("vale só do Pix", PR #53).
- Testes: `TesteValeDaGarota` e 3 de tela. 

## Pendências
Nenhuma.
