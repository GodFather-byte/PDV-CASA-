# HANDOFF

## Último trabalho
- Modernização gradual da interface Qt opt-in concluída para esta etapa. O caixa Qt
  agora inclui montagem, desconto/serviço, observação, transferência, pré-conta,
  caderneta, entrega, sangria/suprimento, repique, gaveta, balança, reimpressão e
  consulta de comanda/comissão. A lista de entregas pendentes não descarta nem
  substitui a venda atual ao atribuir/cancelar; retomar exige venda atual vazia.
- Integradas ao menu Qt telas de consulta de estoque, relatório de vendas por período,
  configurações gerais e importação de produtos. Operações usam os controladores
  existentes; telas de consulta são somente leitura. Exclusão em massa, outros
  relatórios/financeiro, demais cadastros e assistência de impressão continuam no Tk.
- Atualizada `docs/INTERFACE_QT.md`. Homologar em cópia dos dados antes de operação;
  impressora, gaveta e balança ainda exigem teste físico.
- Validação: 195 testes Qt passaram; 356 testes direcionados de controladores e
  periféricos passaram; `git diff --check` limpo. Revisão do fluxo Qt encontrou e
  levou à correção da interferência entre lista de entregas e venda ativa; testes
  de regressão adicionados.

## Pendências
- Confirmar a conclusão do job Windows Python 3.12 do workflow de testes:
  https://github.com/GodFather-byte/PDV-CASA-/actions/runs/38983842283
- Homologar a migração Qt em cópia do banco, com teclado/escala e periféricos reais,
  especialmente impressão, gaveta, balança, entrega e recuperação após falhas.
- Backup: escolher pasta e senha no caixa, confirmar sincronização no provedor e
  ensaiar recuperação em outra máquina; não sincronizar banco em uso nem cópias abertas.
- Asaas: homologar sandbox/credenciais/webhook e hospedar API e
  `python -m backend.worker_asaas` sob supervisão; validar custos antes de contratar.
  Troca de plano/valor e cobrança automática por débito seguem adiadas; cobrança por
  Pix/boleto via link. Sem worker supervisionado, não há renovação.
- Painel web e múltiplos caixas seguem fora de escopo. Usar cópias de dados em toda
  homologação; hardware, provedor e credenciais dependem do titular.
