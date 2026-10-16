# HANDOFF

## Último trabalho
- Base: `main` em `4f089df` (1.4.0), comissão/acerto/saída Qt integrados. A validação
  anterior passou em 245 testes e no build/autotestes Windows; confira `docs/INTERFACE_QT.md`.
- Investigação do CI: PostgreSQL e build Windows passaram. Linux Python 3.10/3.12 falhou
  somente em `test_build_inclui_avisos_licencas_e_versoes_reais`: algumas versões de wheel
  não fornecem arquivos `.dist-info` de licença separados. O teste agora exige cópia exata
  dos arquivos que cada wheel realmente fornece, sem pressupor a existência de pasta vazia.
- Teste direcionado da distribuição passou com o runtime Python 3.12.10/PySide6 6.12.0;
  `git diff --check` passou. A correção ainda não foi publicada nem validada no CI remoto.

## Pendências
- Publicar a correção de `tests/test_modernizacao_integracao.py` e confirmar o CI Linux.
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
