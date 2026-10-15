# Handoff

Atualizado por: Claude em 2026-10-15

## Objetivo atual

Dois pedidos do dono, concluídos na branch `claude/great-clarke-s4any5`:

1. A via (comprovante) da comissão da garota saía com o total acumulado (marcado 30, lança 5, saía 35).
   Agora sai só o valor do lançamento que acabou de ser marcado. A comissão continua somando na comanda
   (isso NÃO mudou: o dono confirmou que é só o comprovante).
2. Pagamento no cartão de crédito acrescenta R$ 5,00 de taxa ao total da venda.

## Feito nesta sessão

- `ImpressaoController.via_comissao(lancamento, nome, operador)`: sem a lista de pendentes nem
  "TOTAL A RECEBER". `LIMITE_VIA_COMISSAO` removido. O total a receber continua no acerto/recibo.
- Esquema v14: `tipos_pagamento.acrescimo_cent` (valor por forma, editável em Cadastros > Tipos de
  Pagamento) e `vendas.acrescimo_cent` (o que foi cobrado). Migração põe 500 em "Cartão Crédito"
  (e formas "cartão ... crédito" / "crédito"); "Crédito Loja" não é afetada. Sementes novas já vêm com 500.
- `CaixaController.calcular`: total inclui o acréscimo, uma vez por venda (o maior das formas lançadas).
  Caderneta não tem acréscimo. `adicionar_pagamento`/`remover_pagamento` recalculam o total.
  `acrescimo_da_forma()` diz quanto a forma acrescentaria agora.
- Tela de pagamento: ao escolher crédito, o valor sugerido já vem com a taxa e aparece aviso
  "Crédito: taxa de R$ 5,00 acrescentada". Resumo mostra "Tx créd.".
- Cupom, fechamento de turno (impresso e tela), relatórios de venda e Telegram mostram/somam a taxa.

## Validação

- Suíte completa (Linux, Python 3.12 + xvfb): 1.127 testes OK, 24 pulados. Testes novos em `tests/test_taxa_credito.py`.
  `test_comissao_na_tela`, `test_comissao_garotas`; testes de tela que pagavam crédito sem taxa ajustados.

## Pendências e armadilhas

- Validar com o operador no Windows da loja: via da comissão e taxa do crédito na maquininha.
- Forma de crédito com outro nome (ex.: "Visa Crédito") não recebe a taxa automaticamente: ajustar o
  campo "Acréscimo" no cadastro da forma.
- Equipamentos reais, emissão fiscal, TEF e validação em loja continuam pendentes.

## Como rodar e testar

Ver `AGENTS.md`. Neste ambiente de nuvem o Python 3.13 não tem Tk; use `python3.12` (com
`python3-tk`) e `xvfb-run -a -s "-screen 0 1920x1080x24" python3.12 -m unittest discover -s tests`.
