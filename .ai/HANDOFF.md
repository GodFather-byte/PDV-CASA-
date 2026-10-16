# HANDOFF

## Último trabalho: vale da garota no acerto (desconto do Pix)
- Janela *Pagar comissão* (`comissao_ui.dialogo_pagar`): campo "A garota pegou vale? Valor do vale (R$)". O vale sai só da parte
  paga por Pix (o dinheiro dele já saiu do caixa antes); não pode passar do Pix. Dinheiro e gaveta não mudam.
- `ComissaoController.pagar(..., pix_cent, vale_cent)`: `pix_cent` é a parte paga por Pix (bruta); o Pix que vai para ela é
  `pix_cent - vale_cent` (devolvido e gravado como `pix_cent`), `vale_cent` fica em `acertos_garotas` (esquema v16). O fechamento
  (`pix_do_turno`) soma o Pix líquido. Recibo: linha "Vale (já recebido)".
- Testes: `TesteValeDaGarota` (test_acerto_garota_shows) e 2 de tela (test_comissao_na_tela). Suíte inteira: 1.239 OK.

## Anteriores (já mesclados)
Reusar número de produto guardado + fim do instalador de licenças no Actions (#52), excluir produto (#51), limite R$ 200 por comanda (#50).

## Pendências
Nenhuma.
