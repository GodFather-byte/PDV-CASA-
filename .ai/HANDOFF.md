# Handoff

Atualizado por: Codex em 2026-10-11

## Objetivo atual

Publicar e mesclar as melhorias do menu principal e da tela de entrada. O dono autorizou
commit, push, criação de PR e merge. Push concluído; PR e merge aguardam acesso à API do GitHub.

## Estado do trabalho

- Branch remota: `codex/moderniza-menu-entrada`.
- `41bbef4`: menu principal modernizado, caixa em destaque, atalhos com descrições,
  navegação compacta, indicadores adaptados e painel rolável.
- `57a7ea3`: entrada modernizada, campos maiores, opção de mostrar senha e navegação por teclado.
- Regras de autenticação, licença, permissões e banco preservadas.
- Suíte completa no Linux: 1.113 testes, execução concluída com OK e 5 pulados
  (87,573 segundos). Os testes de interface usaram X virtual de 24 bits.
- Inspeção visual: menu em 1280×800 e 1000×600; login normal, erro de senha e código de licença.
- Os commits de código estão confirmados no GitHub. O push funciona com a autenticação existente.
- A API `api.github.com` foi negada pelo proxy (HTTP 403 ao estabelecer o túnel), antes de
  executar operações de PR. Nenhum PR foi criado e nenhum merge foi realizado.
- Inclusão de `api.github.com` salva no rascunho da configuração do ambiente; ainda não
  aplicada à máquina na última verificação. Outros domínios e configurações preservados.

## Arquivos relevantes

- `src/ui/app.py`: montagem, navegação e indicadores do menu principal.
- `src/ui/menu_widgets.py`: paleta, fonte, atalhos e painel rolável.
- `src/ui/login.py`: apresentação da entrada e visibilidade da senha.
- `tests/test_ui.py`: novos testes de interação, layout e rolagem; regressões de login.
- Fora do checkout, `/workspace/cloud-setup/pr-menu-entrada.md`: descrição preparada para o PR.
- Fora do checkout, `/workspace/cloud-setup/pre-merge-tests.log`: resultado da suíte completa.

## Próximo passo

1. O dono deve revisar/salvar a mudança de rede nas configurações do ambiente e publicá-la.
2. Conferir aplicação da rede e repetir a leitura da API do GitHub com a autenticação existente.
3. Consultar PR existente da branch antes de criar um novo, anexar o PR à tarefa e verificar
   os checks do GitHub. Mesclar quando os checks necessários passarem.
4. Conferir o merge na `main` remota e informar o link do PR ao dono.

## Pendências e armadilhas

- Não pedir token apenas porque a API foi bloqueada: Git já funciona e GH_TOKEN está presente.
- Salvar o rascunho não aplica a configuração nem publica o ambiente.
- Novo visual validado no Linux; estas alterações não foram executadas no Windows.
- Validação em loja, fiscal, TEF e balança real continuam pendentes.
- A suíte já emitia aviso Tk de callback `destroy` pendente antes destas alterações;
  a execução completa concluiu com OK, sem falhas.

## Como rodar e testar

Ver `AGENTS.md`. Neste ambiente:

```bash
cd /workspace/PDV-CASA-
source .venv/bin/activate
export PATH=/workspace/cloud-setup/x11/usr/bin:$PATH
xvfb-run -a -s "-screen 0 1920x1080x24" python -X faulthandler -m unittest discover -s tests
```

Para abrir em uma máquina com interface gráfica: `python -m src.app`.
