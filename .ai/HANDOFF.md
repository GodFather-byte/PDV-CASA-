# HANDOFF

## Último trabalho
- Ampliação do piloto opt-in Qt: caixa e operações complementares, cadastros,
  estoque, relatórios, configurações, importação, contas a pagar/receber,
  composição, fila/assistente de impressão e backup/restauração.
- A tela financeira usa `ContasController`, revalida `lanc_contas`, e permite
  cadastro/edição/cancelamento, filtros, repetição mensal, quitação e reversão.
- Documentação do piloto em `docs/INTERFACE_QT.md`; autoteste de distribuição
  acompanha os novos módulos Qt em `src/autoteste.py`.
- Validação: 288 testes Qt passaram; 19 testes de contas, permissões e autoteste
  passaram; os 5 testes de autoteste passaram após instalar `cryptography`
  (dependência já declarada em `requirements.txt`). Quatro testes direcionados
  do assistente Tk também passaram após tratar stdout indisponível e bytes fora
  de UTF-8 do comando `sc`.
- Suíte completa passou: 1687 testes, 62 skipped, no Python 3.15 do ambiente.
  `git diff --check` limpo.

## Pendências
- Revisar `git status` e diff para preservar mudanças de terceiros, depois
  commitar a continuação com trailer `Co-authored-by` obrigatório.
- Homologar o piloto em cópia do banco com teclado/escala e periféricos reais,
  especialmente impressão, gaveta, balança, entrega e recuperação após falhas.
- Backup: escolher pasta e senha, confirmar sincronização no provedor e ensaiar
  recuperação em outra máquina; não sincronizar banco em uso nem cópias abertas.
- Asaas: homologar sandbox/credenciais/webhook, hospedar API e
  `python -m backend.worker_asaas` sob supervisão e validar custos antes de
  contratar. Troca de plano/valor e cobrança automática por débito seguem adiadas.
- Painel web e múltiplos caixas seguem fora de escopo; hardware, provedor e
  credenciais dependem do titular.
