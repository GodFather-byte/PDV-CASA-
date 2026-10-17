# HANDOFF

## Último trabalho
- Integração da modernização Qt com WillPDV Licenças 1.1.0; conflito apenas neste
  handoff, resolvido preservando as duas frentes e a decisão de cobrança manual.
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

- Decisão do titular: a cobrança segue **manual** (Asaas cobra, o WillPDV Licenças emite o código). Nuvem
  (Render/Neon/Azure) e worker adiados até a carteira crescer. O trabalho de worker/monitor agendado e
  `render.yaml` pago ficou só na branch `claude/quirky-rubin-pgs2el` (commit `cb10681`, PR 55 fechado,
  revertido localmente na mesma branch); retomar dali quando for a hora.
- WillPDV Licenças 1.1.0 (`licenciador/`): faixa de aviso no topo com lojas vencidas ou vencendo em até 7
  dias; aba **Backup** (histórico copiado a cada emissão/remoção para a pasta escolhida, por exemplo a do
  Google Drive para computador, 30 cópias diárias; chave só vai criptografada com senha de 12+ caracteres,
  `.pdvbkp`, via `src/core/backup_seguro.py`); restaurar histórico e chave. Sem API do Google: o app do
  Drive sincroniza a pasta. Autoteste do executável passou a ter a etapa `backup` e 5 abas.
- Testes: `tests/test_licenciador.py` (45) passam com Tk em Xvfb. `cryptography` precisa estar no pacote do
  licenciador (PyInstaller); o autoteste do `.exe` no CI confere isso, confirmar o job verde.

## Pendências
- Titular: instalar o Google Drive para computador, escolher a pasta na aba Backup e anotar a senha da chave.
- Ideia aberta (pede OK do titular, regra de licença): renovar a partir do vencimento atual para o cliente
  não perder dias quando se renova antes. Hoje a validade conta a partir de hoje.
- Ideias menores: contato/valor/observação por loja, marcar "pago", exportar CSV.
- Qt já oferece montagem, desconto/serviço, transferência, caderneta/entrega,
  sangria/repique, gaveta, balança e consulta de comanda, além das telas acima.
  Homologar em cópia do banco com teclado/escala e periféricos reais, inclusive
  comissão/acerto/saída e recuperação após falhas.
- Backup do PDV: escolher pasta e senha no caixa, confirmar sincronização no provedor e ensaiar
  recuperação em outra máquina; não sincronizar banco em uso nem cópias abertas.
- Asaas (quando houver nuvem): homologar sandbox/credenciais/webhook e hospedar API e
  `python -m backend.worker_asaas` sob supervisão; validar custos antes de contratar.
- Painel web e múltiplos caixas seguem fora de escopo.
