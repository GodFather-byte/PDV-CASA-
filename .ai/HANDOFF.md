# Handoff

Atualizado por: Codex em 2026-10-11

## Objetivo atual

Concluída a repaginação do menu inicial do PDV, solicitada pelo dono para deixá-lo mais
moderno e intuitivo. Próxima tarefa funcional a definir.

## Feito nesta sessão

- Menu com paleta escura de maior contraste, barra lateral compacta e nomes mais diretos.
- "Abrir caixa" em destaque e atalhos administrativos com descrições, em duas colunas.
- Painel com rolagem independente da navegação; indicadores com quebra de texto e estoque
  em duas colunas para telas menores. Avisos de backup e atualização empilhados.
- Atalhos rápidos acessíveis por Tab, Enter e espaço; mantidos os atalhos por letras,
  navegação por setas, permissões e atualização periódica.
- Fonte do menu: Segoe UI no Windows e Helvetica no Linux (evita fallback minúsculo no Tk).
- Validação no Linux com X virtual de 24 bits: 186 testes de interface aprovados
  (`tests.test_ui` e `tests.test_ui_fumaca`), incluindo três novos testes do menu.
- Inspeção visual em 1280×800 e 1000×600. Nenhuma regra de negócio ou esquema alterado.

## Arquivos relevantes

- `src/ui/app.py`: montagem, navegação e indicadores do menu principal.
- `src/ui/menu_widgets.py`: paleta, cartões, atalhos e painel rolável.
- `tests/test_ui.py`: testes do menu, teclado, clique e rolagem em janela compacta.

## Decisões tomadas e motivo

- Priorizar o caixa no topo; descrições explicam os demais atalhos sem exigir abrir submenus.
- Preservar as letras antigas (inclusive M para Cadastros), evitando mudar os hábitos dos operadores.
- Usar componentes Tkinter existentes, sem dependências adicionais para a interface.

## Próximo passo

Conferir o visual no Windows da loja e ajustar conforme o retorno do dono.

## Pendências e armadilhas

- O novo visual foi validado no Linux; não houve execução desta alteração no Windows.
- Validação em loja, fiscal, TEF e balança real continuam pendentes.
- Testes gráficos no Linux precisam de X virtual com 24 bits de cor.
- A suíte de UI emite aviso Tk sobre callback `destroy` pendente, já observado antes
  desta alteração; a execução conclui com OK, sem falhas.

## Como rodar e testar

Ver `AGENTS.md`. Neste ambiente:

```bash
cd /workspace/PDV-CASA-
source .venv/bin/activate
export PATH=/workspace/cloud-setup/x11/usr/bin:$PATH
xvfb-run -a -s "-screen 0 1920x1080x24" python -m unittest tests.test_ui tests.test_ui_fumaca
```

Para abrir o programa em uma máquina com interface gráfica: `python -m src.app`.
