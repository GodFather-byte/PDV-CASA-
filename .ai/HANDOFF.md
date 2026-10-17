# HANDOFF

## Último trabalho
- Base: `main` em `e278947` (1.4.0), incluindo comissão/acerto/saída Qt integrados.
- Corrigido `test_build_inclui_avisos_licencas_e_versoes_reais`: compara os arquivos de
  licença realmente fornecidos pelas wheels, sem pressupor que todo pacote tenha arquivos
  `.dist-info` separados. O teste direcionado passou anteriormente com Python 3.12.10 e
  PySide6 6.12.0; `git diff --check` passou.
- Correção publicada em `e278947`. CI: PostgreSQL, build Windows, Linux Python 3.10 e 3.12
  passaram. Windows Python 3.10 passou; Windows Python 3.12 ainda estava executando os
  testes quando este handoff foi atualizado.
- Python não está disponível no PATH deste ambiente após reiniciar o VS Code.

- Restaurado o job `licenciador` no `build-windows.yml` (instalador WillPDV Licenças só nos Artifacts, nunca na Release), com README, docs/LICENCIADOR.md e teste de empacotamento de volta ao estado anterior a `734ee2b`. Falta ver o job verde no GitHub após o push.

## Pendências
- Confirmar a conclusão do job Windows Python 3.12 no workflow de testes:
  https://github.com/GodFather-byte/PDV-CASA-/actions/runs/38983842283
- Qt ainda bloqueia partes/montagem, desconto/serviço manual, transferência,
  caderneta/entrega, sangria/repique, gaveta, balança e consulta de comanda. Homologar
  em cópia do banco antes de substituir o Tk em operação.
- Comissão/acerto/saída: homologar impressão, gaveta e ergonomia com periféricos reais.
- Backup: escolher pasta e senha no caixa, confirmar sincronização no provedor e ensaiar
  recuperação em outra máquina; não sincronizar banco em uso nem cópias abertas.
- Asaas: homologar sandbox/credenciais/webhook e hospedar API e
  `python -m backend.worker_asaas` sob supervisão; validar custos antes de contratar.
  Troca de plano/valor e cobrança automática por débito seguem adiadas; cobrança por Pix/
  boleto via link. Sem worker supervisionado, não há renovação.
- Painel web e múltiplos caixas seguem fora de escopo. Usar cópias de dados em toda
  homologação; as confirmações de hardware, provedor e credenciais dependem do titular.
