# HANDOFF

## Último trabalho: cobrança mensal de licenças pelo Asaas
- Decisões do usuário: Pix/boleto por link (pagamento pelo cliente a cada mês), valor configurável
  por loja, manter validade offline + 5 dias de carência e proteção de turno recente.
  Orçamento de hospedagem: até R$ 50/mês, se houver opção adequada.
- `backend/cobrancas.py`: assinatura mensal criada no painel Asaas e vinculada à loja;
  consulta remota com Decimal, eventos idempotentes, cálculo por vencimento + mês de calendário,
  conciliação paginada e recálculo de validade em estorno. Segredos só no servidor.
- `POST /v1/webhooks/asaas`: cabeçalho `asaas-access-token` comparado com `ASAAS_WEBHOOK_TOKEN`;
  consulta API com `ASAAS_API_KEY` e `ASAAS_AMBIENTE=sandbox|producao`.
- Administração: `python -m backend.lojas cobranca vincular LOJA sub_ID VALOR_CENT`,
  `cobranca listar`, `cobranca conciliar LOJA`. Não cria cliente/assinatura no Asaas.
  Comando manual `assinatura` é recusado para lojas vinculadas (não afeta lojas manuais).
- Três tabelas exclusivamente na nuvem, criadas via SQLAlchemy conforme o padrão do backend;
  nenhuma migração no SQLite local. Renovação existente do PDV e chave pública preservadas.
- Guia separado: `docs/COBRANCA_LICENCAS_ASAAS.md`, com custos, Render/Neon, segredos,
  cadastro, testes sandbox, operação, backup e limitações; links em NUVEM e LICENCIADOR.
- Validação: 85 testes direcionados, 84 passaram e 1 pulado (referência opcional cryptography).
  Sem Python funcional no PATH: usado Python 3.12.10 embutido isolado na pasta da sessão,
  com dependências do backend e httpx. Testes novos simulam o Asaas; não usam conta real.
  Sem validação de telas Tkinter ou concorrência PostgreSQL neste ambiente.

## Pendências
- Configurar conta/credenciais e assinatura sandbox, hospedar API e homologar webhook real.
  Nada foi contratado, publicado ou cobrado por este trabalho.
- Produção: serviço sempre ligado (Render gratuito não recomendado), PostgreSQL persistente,
  backup/restauração testados e orçamento conferido com câmbio/taxas antes de contratar.
- Importante: estorno recalcula a validade no servidor, mas não revoga uma licença offline
  já entregue; ela segue até seu prazo/carência. Não há botão de pagar no PDV,
  cartão recorrente/Pix Automático, troca de plano/assinatura nem painel web novo.
- Valores são definidos no vínculo. Alteração posterior de preço precisa de evolução
  administrativa e testes; não alterar manualmente o banco para contornar divergências.
