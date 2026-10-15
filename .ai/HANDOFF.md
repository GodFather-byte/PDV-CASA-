# Handoff

Atualizado por: Claude em 2026-10-15

## Objetivo atual

Pedido do dono: modo claro e modo escuro, com a escolha nas configurações. Branch `claude/great-clarke-s4any5` (os PRs #47 e #48
já foram mesclados).

## Feito nesta sessão

- `src/ui/paleta.py` (novo): as duas paletas (`COR` das telas de cadastro, `PAL` do menu/entrada, `CX` do caixa, `ESTADOS` dos
  cartões das comandas) e `aplicar(modo)`, que troca o CONTEÚDO dos dicionários `tema.COR`, `menu_widgets.PAL`, `caixa_tema.CX` e
  `painel_mesas.ESTADOS` no mesmo objeto (as telas guardam a referência). `aplicar_da_configuracao(banco)` lê `tema_visual`.
- Configuração `tema_visual` (`escuro` padrão | `claro`), primeira aba "Aparência" em Configurações. Ao gravar,
  `config_ui.aplicar_visual` avisa e chama `ctx.ao_mudar_tema` (= `App.aplicar_visual`): paleta nova, estilos ttk refeitos, telas
  abertas fechadas e menu refeito. O programa abre no modo gravado (`App.__init__`).
- `tema.aplicar_tema` agora é guiado pela paleta (campos, listas, abas, caixas de seleção, rolagem, menus). As cores fixas das
  telas viraram chaves da paleta (`sobre`, `rotulo`, `titulo`, `papel`, `ok_fundo`/`perigo_fundo`/`aviso_fundo`, `virtual`,
  `inativo`...). Use `COR["rotulo"]`/`["titulo"]` para TEXTO e `marinho`/`marinho2` só para fundos de barras e botões.
- `app.ICONES` virou a função `icones()` (cores dependem do modo). Constantes de cor do caixa viraram `CX["comissao"]` etc.
- Modo claro das telas de cadastro: o visual de sempre (com `ok`/`perigo`/`aviso` um pouco mais escuros, para ler melhor).

## Validação

- `tests/test_tema_claro_escuro.py` (26): paletas iguais nos dois modos, hexadecimais válidos, contraste WCAG (texto e destaques
  ≥ 4,5; texto principal ≥ 7), troca no lugar, configuração, menu refeito e telas abrindo nos dois modos.
- `BaseUI.setUp` volta ao padrão (`paleta.aplicar`) para um teste não vazar o modo para os outros.
- Capturas conferidas nos dois modos: menu, entrada, caixa, cadastro e configurações (o painel de estoque não aparece nas capturas
  do ambiente de teste, mas abre e usa as cores certas nos testes).

## Pendências e armadilhas

- Trocar o modo FECHA as telas abertas (cadastros, relatórios, configurações...): editar e não gravar perde a edição. O caixa
  aberto não é fechado (não fica na lista de janelas): ele só muda ao ser aberto de novo.
- Cor nova em tela: use a paleta (`tema.COR`, `PAL`, `CX`), nunca hexadecimal solto, ou ela não troca com o modo.
- Validar com o dono no Windows: legibilidade do modo claro no caixa e a troca ao vivo.
- Equipamentos reais, emissão fiscal, TEF e validação em loja continuam pendentes.

## Como rodar e testar

Ver `AGENTS.md`. Neste ambiente de nuvem o Python 3.13 não tem Tk; use `python3.12` (com `python3-tk`) e
`xvfb-run -a -s "-screen 0 1920x1080x24" python3.12 -m unittest discover -s tests`.
