# Handoff

Atualizado por: Codex em 2026-10-11

## Objetivo atual

Concluída a modernização da tela de entrada que aparece ao abrir o PDV, em continuidade
à repaginação do menu principal pedida pelo dono.

## Feito nesta sessão

- Login com visual escuro alinhado ao menu, painel de identificação da loja e boas-vindas.
- Campos maiores, instruções para selecionar/digitar o usuário e botão "Entrar no PDV" em destaque.
- Opção "Mostrar senha", desativada por padrão em cada nova janela de entrada.
- Selecionar o operador ou pressionar Enter no usuário leva à senha; Enter na senha entra,
  Esc cancela. Mantidos os caminhos de licença e troca obrigatória da senha de fábrica.
- Estilos ttk exclusivos do login; demais formulários mantêm seus estilos.
- 24 testes aprovados no Linux com X virtual de 24 bits: `TesteTelaEntrada`, `TesteMenu`,
  `TesteLoginComLicenca` e `TesteFluxoDeEntrada`, incluindo três novos testes de interação.
- Inspeção visual da tela normal, erro de senha e opção de código de licença; esta última
  ocupa 783×545 no ambiente Linux.
- Nenhuma alteração nas regras de autenticação, licença, negócio ou banco de dados.

## Entrega anterior

- Commit `41bbef4`: menu principal modernizado, caixa em destaque, atalhos com descrições,
  navegação compacta, painel rolável e ajuste para notebooks. 186 testes de UI aprovados.

## Arquivos relevantes

- `src/ui/login.py`: apresentação da entrada, estilos e visibilidade da senha.
- `src/ui/menu_widgets.py`: paleta e fonte compartilhadas pelo login e menu.
- `src/ui/app.py`: fluxo entre login, menu e caixa.
- `tests/test_ui.py`: interação da entrada e regressões de autenticação/licença.

## Decisões tomadas e motivo

- Unificar a aparência da entrada e do menu sem adicionar dependências gráficas.
- Manter o campo editável de usuário e os atalhos familiares para facilitar o atendimento.
- Separar apresentação de autenticação: métodos existentes de entrada e licença preservados.

## Próximo passo

Conferir o visual da entrada e do menu no Windows da loja e ajustar conforme o retorno do dono.

## Pendências e armadilhas

- Novo visual validado no Linux; estas alterações não foram executadas no Windows.
- Validação em loja, fiscal, TEF e balança real continuam pendentes.
- Testes gráficos no Linux precisam de X virtual com 24 bits de cor.
- A suíte completa de UI já emitia aviso Tk de callback `destroy` pendente; isso foi observado
  antes da repaginação e não produziu falhas nas execuções concluídas.

## Como rodar e testar

Ver `AGENTS.md`. Neste ambiente:

```bash
cd /workspace/PDV-CASA-
source .venv/bin/activate
export PATH=/workspace/cloud-setup/x11/usr/bin:$PATH
xvfb-run -a -s "-screen 0 1920x1080x24" python -m unittest tests.test_ui.TesteTelaEntrada tests.test_ui.TesteMenu tests.test_ui.TesteLoginComLicenca tests.test_ui.TesteFluxoDeEntrada
```

Para abrir o programa em uma máquina com interface gráfica: `python -m src.app`.
