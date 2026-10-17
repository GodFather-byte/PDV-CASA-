# HANDOFF

## Último trabalho
- Decisão do titular: hospedar a API no **Render (instância paga `starter`) + Neon** e rodar o worker
  do Asaas como **agendador no GitHub Actions**; ao crescer, migrar o worker para o Background Worker
  do Render (mesmo comando, sem `--uma-vez`).
- Novos: `.github/workflows/worker-asaas.yml` (lote a cada 5 min), `.github/workflows/monitor-asaas.yml`
  (indicador a cada 30 min) e `tools/monitor_asaas.py` com `tests/test_monitor_asaas.py`.
- `render.yaml`: plano `starter` e variáveis `ASAAS_*` declaradas (valores só no painel). Guia
  `docs/COBRANCA_LICENCAS_ASAAS.md` (seção 5.2 e 11) atualizado.
- Os agendamentos do GitHub só valem depois que estes arquivos estiverem no `main`. Sem os segredos
  configurados os jobs avisam e saem sem falhar.
- Os testes do backend ficam pulados se SQLAlchemy/httpx não estiverem instalados; no CI rodam.

## Pendências (dependem do titular)
- Neon: criar dois projetos (teste e produção). Render: serviço de teste e serviço de produção,
  Secret File `licenca_privada.key` (a chave já usada nos PDVs, nunca um par novo).
- GitHub > Settings > Secrets and variables > Actions: segredos `PDV_NUVEM_DB_URL`, `ASAAS_API_KEY`,
  `PDV_API_TOKEN`; variáveis `ASAAS_AMBIENTE` e `PDV_API_URL`. Um worker agendado serve a um banco
  só: para testar no sandbox e depois produção, troque os valores ao virar de ambiente.
- Homologar tudo no sandbox (seção 9 do guia) antes de vincular a loja real. A loja real já tem
  licença manual: registrar a validade atual com `python -m backend.lojas assinatura` **antes** de
  `cobranca vincular`.
- Custo estimado (render.com/pricing, 17/10/2026): instância paga mínima US$ 7/mês, workspace Hobby
  US$ 0; worker no GitHub sem custo. Valores em dólar, sem IOF/câmbio.
- Qt ainda bloqueia partes/montagem, desconto/serviço manual, transferência, caderneta/entrega,
  sangria/repique, gaveta, balança e consulta de comanda. Homologar em cópia do banco.
- Comissão/acerto/saída: homologar impressão, gaveta e ergonomia com periféricos reais.
- Backup: escolher pasta e senha no caixa, confirmar sincronização no provedor e ensaiar
  recuperação em outra máquina; não sincronizar banco em uso nem cópias abertas.
- Troca de plano/valor e cobrança automática por débito seguem adiadas. Painel web e múltiplos
  caixas seguem fora de escopo.
