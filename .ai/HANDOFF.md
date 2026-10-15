# Handoff

Atualizado por: Claude em 2026-10-15

## Objetivo atual

Pedido do dono (com a imagem de referência): refazer a tela do caixa mais moderna, poder navegar dentro das comandas das
garotas e dos clientes, e imprimir o comprovante de saída financeira quando o dinheiro sai do caixa para pagar a garota.
Tudo na branch `claude/great-clarke-s4any5`.

## Feito nesta sessão

- **Comprovante de saída ao pagar a garota** (`comissao_ui.pagar_garota`): além do recibo, sai o comprovante de saída
  (`comprovante_movimento`, o mesmo da sangria) com o valor que saiu do caixa (`dinheiro_cent`, sem o Pix) e o motivo
  `Comissão/Acerto garota N NOME`. Pagando fora do caixa não há saída. `ComissaoController.pagar` devolve
  `movimento_descricao`.
- **Tela do caixa em três colunas** (`caixa_ui.py`, `painel_mesas.py`, `caixa_tema.py`): cabeçalho com indicadores
  (abertas, aguardando acerto, em aberto na casa, turno e hora); painel de comandas à esquerda como cartões grandes com busca
  (texto-guia), abas de filtro e colunas (3/2/1) que acompanham a largura da janela (`definir_colunas`, `_dispor`); venda
  atual no centro com selo da situação e texto-guia nos campos; total com o detalhe do acréscimo e as ações do dia a dia em
  duas colunas na direita (`_n_fixos` = quantas ficam à vista; o resto, em Mais opções). Paleta azul-noite só no `CX`.
- **Navegação**: PgUp/PgDn e botões ◀ ▶ (`navegar_comanda`, `PainelMesas.vizinha`) passam pela comanda anterior/seguinte
  da lista do painel (respeita aba e busca; clientes e garotas); seta para cima na 1ª linha volta ao código; Enter ou duplo
  clique numa linha abre as ações (`_menu_linha`): item (observação, transferir, cancelar) e comissão (pagar, cancelar).
- **Nome da comanda** (esquema v15, `vendas.apelido`, `CaixaController.definir_apelido`): clique no título ou Mais opções >
  Nomear comanda; aparece no cartão, no título (`Comanda 12 · Carlos`) e a busca do painel acha por ele.
- Cartão da garota mostra o nome e "N drinks marcados" (`pendentes_por_garota` já trazia nome e lançamentos).
- README (seções "A tela do caixa", "Mesas e comandas" e "Comissão das garotas") e MAPA atualizados.

## Validação

- Testes novos: `tests/test_tela_caixa_cartoes.py` (35) e os do comprovante em `test_comissao_na_tela`/`test_ui`.
- Capturas de tela conferidas em 1664×900 e 1366×768 (scripts no scratchpad da sessão, fora do repositório).

## Pendências e armadilhas

- Validar com o operador no Windows da loja: leitura da nova tela (fontes Segoe UI), PgUp/PgDn e o comprovante de saída.
- "Drinks marcados" conta os lançamentos de comissão pendentes (um por marcação), não pontos.
- A janela de pagamento (F12) e as demais telas seguem como estavam; só o caixa foi refeito.
- Telas pequenas (<1250 px): painel em 1 coluna; abaixo de ~1000 px a venda atual fica estreita.
- Equipamentos reais, emissão fiscal, TEF e validação em loja continuam pendentes.

## Como rodar e testar

Ver `AGENTS.md`. Neste ambiente de nuvem o Python 3.13 não tem Tk; use `python3.12` (com `python3-tk`) e
`xvfb-run -a -s "-screen 0 1920x1080x24" python3.12 -m unittest discover -s tests`.
