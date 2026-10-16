# HANDOFF

## Último trabalho: WillPDV 1.4.0 — backup seguro, auditoria e início da migração Qt
- Decisões confirmadas: um caixa por boate; manter SQLite local e PostgreSQL na nuvem;
  backup em pasta escolhida pelo operador e sincronizada pelo OneDrive/Google Drive;
  migrar para PySide6/Qt; painel web fica para depois. Sem contratar serviços.
- Backup externo em `src/core/backup_seguro.py` e `UtilitarioController`: AES-256-GCM
  em blocos, scrypt, arquivo `.pdvbkp`, gravação atômica e recuperação conferida antes
  da publicação. Senha automática protegida por DPAPI do usuário Windows em
  `<banco>.backup.key`, nunca no SQLite. Guardar a senha original fora do computador.
- Configuração/geração/verificação/restauração em Utilitários no Tk e na prévia Qt.
  Cada backup normal também gera cópia externa se configurada; erro externo preserva
  cópia local e avisa no painel/log. Retenção padrão 60 arquivos próprios.
  O PDV NÃO confirma upload: isso depende do sincronizador. Pasta/conta real não
  foram configuradas e nenhum dado do cliente foi enviado por este trabalho.
- Esquema v18: `auditoria_eventos`, gatilhos transacionais e identidade da sessão
  via `BancoDados.definir_operador_auditoria` / setter `Contexto.operador`.
  Eventos de cadastro/preço/exclusão/venda/desconto/cancelamento/estoque/permissão,
  antes/depois por lista permitida sem senhas/hashes/tokens.
  Consulta somente leitura por `Contexto.auditoria`, nível 4 e `rel_auditoria`.
- Tk: Relatórios > Caixa > Alterações e auditoria detalhada.
  Qt: Auditoria na navegação. Filtros e paginação de 100 com detalhe JSON.
- `python -m src.app --qt`: prévia Qt, sem fallback Tk no mesmo processo.
  Padrão e `--tk` continuam a interface completa. Mesma trava de instância e banco.
  Qt tem login/licença assíncrona/troca obrigatória de senha, principal, produtos,
  operadores, auditoria, backup e caixa mínimo usando os controllers existentes.
- Caixa Qt: turno, balcão/mesa/comanda, produtos/quantidades, pagamento/troco,
  fechamento/cancelamento com permissões e supervisor. Sair preserva venda aberta;
  fechamento recusado impede logout. Não cria outro fluxo de venda.
- NÃO anunciar migração completa: comissões (código 50), saída 1002, partes/montagem,
  desconto/serviço manual, transferência, entrega/caderneta, sangria/repique,
  equipamentos e demais módulos ainda exigem Tk. Recursos não migrados são
  explicitamente bloqueados no piloto; conferir `docs/INTERFACE_QT.md`.
- Dependências: PySide6-Essentials (sem WebEngine), cryptography e integrações em
  requirements.txt. Build onedir inclui avisos e textos LGPL/GPL e metadados.
  Instalador ganha atalho opcional de uso `WillPDV Qt (prévia)` no Menu Iniciar,
  sem mudar o atalho padrão. CI testa Qt empacotado e instalado separadamente.
- Docs: BACKUP_EXTERNO, AUDITORIA, INTERFACE_QT, TERCEIROS_QT; README,
  INSTALAR_E_TESTAR e MAPA atualizados. Prévia fictícia na pasta da sessão.
- Validação: auditoria/Tk/migração 61 testes; base/auditoria Qt 48; caixa Qt 19;
  integração inicial 71; último seletor backup/módulos/instalador 39, todos aprovados.
  Build PyInstaller Windows real gerado. Autotestes do executável final Tk (88
  módulos e telas) e Qt + criptografia + DPAPI + recuperação real aprovados.
  Suíte inteira: 1465 testes, 1454 passaram, 10 pulados (PostgreSQL local ausente)
  e uma falha na rota direta do novo relatório de auditoria. Dispatcher corrigido;
  seletor final de 159 testes (fumaça Tk, auditoria, Qt, caixa, backup, integração
  e instalador) passou inteiro, sem skips. Não confundir logs de falhas simuladas
  do autoteste com falhas da suíte. Conferir matriz CI após push.
- Runtime isolado Python 3.12.10 + Tk 8.6 + Qt 6.12, sem mudar Python/PATH global.
  Qt instalado em pasta temporária curta por limite de caminhos do Windows,
  referenciada por .pth no runtime da sessão, mantida para próximas validações.

## Pendências
- Finalizar migração Qt dos recursos usados nas boates, sobretudo comissão das garotas;
  homologar em cópia do banco antes de substituir Tk em operação.
- Escolher pasta real/senha no computador do caixa, confirmar sincronização pelo site
  do provedor e ensaiar recuperação em outra máquina. Backup local antigo continua
  sem criptografia; não pôr o banco em uso nem os backups abertos na pasta sincronizada.
- Painel web e múltiplos caixas fora desta etapa; múltiplos caixas não são necessários.
- Asaas anterior preservado: homologar sandbox/credenciais/webhook real e hospedar API
  mais `python -m backend.worker_asaas` supervisionado (ou scheduler `--uma-vez`).
  Inicializar tabelas com `python -c "import backend.main"` antes de API/worker paralelos.
  Mesmo PostgreSQL/ambiente/chave/timezone. Sem worker não renova. Nenhum deploy
  contratado. Orçamento alvo até R$50/mês, confirmar preços antes de contratar.
- Troca de valor/plano/assinatura adiada; Pix/boleto por link, não débito automático.
  Offline mantém validade paga + 5 dias de carência e proteção de turno recente;
  estorno não revoga imediatamente licença assinada já entregue.
