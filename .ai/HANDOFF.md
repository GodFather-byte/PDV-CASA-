# HANDOFF

## Último trabalho: comissão/acerto/saída Qt integrados e validados
- Base: 1.4.0, commit 96be2a1. Validação integrada concluída em 2026-10-16.
  Usuário autorizou commit e push em 2026-10-16 após a validação.
  Entrega na própria `main`; remoto conferido na mesma base, sem merge necessário.
- Divisão combinada (um escritor por arquivo): Claude = `src/ui_qt/comissao.py` (novo),
  edição pontual em `src/ui_qt/caixa.py`, `docs/INTERFACE_QT.md` e este arquivo.
  Após Claude liberar os arquivos, Copilot integrou testes, autoteste e documentação.
  Controllers, esquema, regras de licença e Tk intocados.
- Reuso: `ComissaoController` (lançar/pagar/cancelar), `CaixaController.liberar_saida`,
  `ImpressaoController` (via, recibo, comprovante de saída, ticket), `AcessoController`
  via `JanelaCaixa._autorizar`; `entregar_via` importado de `src/ui/comissao_ui.py`.
- `comissao_na_linha` preservada: ligada = modo na linha (`modo_comissao`, `lbl_cod_titulo`
  "Garota nº:", `lbl_qtd_titulo` = rótulo do valor/pontos, `lbl_comissao_nome`, `btn_lancar`
  "Lançar comissão"; Enter no código avança, Enter no valor/botão grava, Esc descarta);
  desligada = janela (`_dialogo_comissao`). Comissões marcadas aparecem na tabela com
  `Qt.UserRole = "c<id>"`; Cancelar item nelas cancela o lançamento (só na linha).
- F12 na comanda da garota: só comissão → acerto; consumo + comissão → escolher; comanda
  vazia de garota ativa com shows → acerto só de shows (como `CaixaUI.pagar`).
- `tests/test_qt_comissao.py`: 35 testes com banco real em memória, modos linha/janela,
  pontos/reais, supervisor, cadastro/valor alto, shows/vale/Pix, gaveta, cancelamento,
  painel, F12, saída 1002 e falhas de impressão sem desfazer registros.
  Corrigidas fixtures: turno retorna inteiro, comanda precisa estar no intervalo,
  serviço integra o total; venda vazia cancelada é excluída pelo controller existente.
  Senha de comissão explicitamente habilitada nos testes de autorização (padrão N).
- `src/autoteste.py`: módulo Qt de comissão registrado. `src/ui_qt/app.py.autoteste`:
  comissão pela entrada, painel e diálogos reais, saída preservando comissão.
  O executável exige licença para abrir turno; o autoteste insere SOMENTE um turno
  fictício em seu banco em memória. Nenhuma proteção de produção foi alterada.
- Validação final: 245 testes, todos aprovados, sem skips:
  `python -m unittest tests.test_qt_app tests.test_qt_caixa tests.test_qt_comissao
  tests.test_autoteste tests.test_comissao_garotas tests.test_comissao_na_tela`
  com `QT_QPA_PLATFORM=offscreen`. Mensagens de falha simulada do autoteste são
  esperadas pelos testes negativos, não falhas desta execução. `git diff --check` OK.
- Build Windows `build_pdv.py --sem-instalador` concluído. Executável
  `dist/WillPDV/WillPDV.exe`: `--autoteste-qt` e `--autoteste` aprovados, incluindo
  criptografia/recuperação e DPAPI no Qt. Nenhum banco real usado.
- O runtime isolado EXISTE e funcionou (Python 3.12.10, PySide6 6.12.0):
  `C:\Users\ITAUTEC\.copilot\session-state\1346668e-9aaf-42b5-bd54-7b7ad43bf97b\files\python-runtime\python.exe`.
  `python` no PATH continua sendo somente o atalho da Store.
  Relatórios na mesma sessão, pasta `files`: `comissao-validacao-final.log`,
  `comissao-empacotado-qt-final.txt`, `comissao-empacotado-tk-final.txt`,
  `comissao-build-qt-final.log`.

## Pendências
- Conferir CI após publicar. Instalador não foi gerado nesta rodada;
  executável permanece 1.4.0.
- Homologar comissão/acerto/saída em cópia do banco e periféricos reais antes do uso
  comercial. Testes offscreen não confirmam impressão física, gaveta ou ergonomia.
- Restante da migração Qt: partes/montagem, desconto/serviço manual, transferência,
  caderneta/entrega, sangria/repique, gaveta, balança, consulta de comanda; homologar em
  cópia do banco antes de substituir o Tk em operação.
- Escolher pasta real/senha do backup externo no computador do caixa, confirmar sincronização
  pelo site do provedor e ensaiar recuperação em outra máquina. Backup local antigo segue sem
  criptografia; não pôr o banco em uso nem os backups abertos na pasta sincronizada.
- Painel web e múltiplos caixas fora desta etapa; múltiplos caixas não são necessários.
- Asaas: homologar sandbox/credenciais/webhook real e hospedar API mais
  `python -m backend.worker_asaas` supervisionado (ou scheduler `--uma-vez`). Inicializar
  tabelas com `python -c "import backend.main"` antes de API/worker paralelos. Mesmo
  PostgreSQL/ambiente/chave/timezone. Sem worker não renova. Nenhum deploy contratado.
  Orçamento alvo até R$50/mês, confirmar preços antes de contratar.
- Troca de valor/plano/assinatura adiada; Pix/boleto por link, não débito automático.
  Offline mantém validade paga + 5 dias de carência e proteção de turno recente;
  estorno não revoga imediatamente licença assinada já entregue.
