# HANDOFF

## Último trabalho: WillPDV 1.3.0 — produtos, proteção local e operação Asaas
- Usuário autorizou agentes e confirmou exclusão definitiva do cadastro comercial, preservando
  cupons/relatórios antigos. Amarula código 8 pode ser excluída e Red Bull cadastrada no código 8;
  IDs distintos impedem relabeling de vendas antigas e estorno no estoque do novo produto.
- Esquema local v17: `produtos_historico` guarda a identidade histórica, metadados e saldo;
  cadastro `produtos` é removido fisicamente. Relações de vendas/partes/estoque apontam para
  histórico, relatórios/reimpressão/Telegram ajustados. Migração preserva IDs, sequências e FKs;
  códigos legados com sufixo `~id` são normalizados no histórico e removidos do catálogo.
- Exclusão individual recusa vendas abertas (inclusive partes), insumos de composição e
  pedidos de compra pendentes. Exclusão total faz backup, remove catálogo/fichas técnicas,
  mas mantém movimentos/compras/vendas. Importação posterior cria identidades novas.
- `protecao.py`: restauração prepara/valida cópia antes da troca, preserva pedido e banco em
  falhas; banco vazio existente não abre como loja nova. `conexao.py`: recusa esquema futuro
  antes de alterar banco e faz backup verificado `.antes-migracao-v*.bak` antes da migração.
- Licença: separa tentativa/sucesso, falhas repetem progressivamente (1–30 minutos);
  consulta concluída mantém intervalo de 6 horas. Login consulta em thread, aplica só no Tk,
  impede duplicações e resposta tardia após fechar. Painel mostra validade/último sucesso/erro.
- Asaas: webhook agora persiste inbox sem HTTP externo e responde rapidamente.
  `backend/operacao_asaas.py`: fila, backoff, agenda persistente, locks e indicadores.
  `python -m backend.worker_asaas` processa eventos e concilia periodicamente; alternativa
  via scheduler de servidor: `--uma-vez --limite 100`. Logs `ALERTA_ASAAS` e estado autenticado
  em `/v1/admin/cobrancas/operacao`. Sem envio externo de e-mail/WhatsApp.
- Docs atualizados: COBRANCA_LICENCAS_ASAAS, IMPORTAR_PRODUTOS, INSTALAR_E_TESTAR e MAPA.
- Validação integrada: 1322 testes, 1311 aprovados e 11 skips (10 exigem PostgreSQL e
  1 referência opcional cryptography). Após os últimos ajustes de migração/indicador,
  52 testes direcionados aprovados (incluindo versão/empacotamento); compileall de
  src/backend/tests passou.
  Runtime Python 3.12.10 + Tk 8.6 isolado na sessão, sem alterar Python/PATH global.
  Job CI novo: `Asaas / PostgreSQL 16` (`cobrancas-postgres`).
- Primeiro CI: Linux Python 3.12 e instalador Windows passaram. PostgreSQL revelou
  classificação incorreta de inserções pelo `rowcount` do psycopg; corrigida com
  `ON CONFLICT DO NOTHING RETURNING id`, com teste de contrato dos dois dialetos.
  Backend após correção: 42 testes, 32 aprovados e 10 PG pulados localmente.

## Pendências
- Homologar a conta Asaas sandbox e webhook real; nenhum serviço contratado nem cobrança real feita.
- Deploy: executar `python -c "import backend.main"` primeiro para criar tabelas aditivas,
  depois API e worker supervisionado usando mesmo PostgreSQL, ambiente, API Key e timezone.
  Worker é obrigatório: sem ele o webhook fica gravado, mas a licença não é renovada.
  Não foi instalado agendador/worker em produção. Worker separado pode acrescentar custo;
  conferir orçamento de R$ 50/mês e backups antes de contratar.
- Verificar CI PostgreSQL e build/instalador Windows após push. PostgreSQL não disponível localmente.
- Valores por loja continuam definidos no vínculo; troca de valor/plano/assinatura foi
  expressamente adiada pelo usuário. Pix/boleto por link, não débito automático.
- Regras offline preservadas: validade paga + 5 dias de carência, proteção de turno recente;
  estorno não revoga imediatamente código assinado já entregue.
