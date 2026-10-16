# Interface Qt — piloto opt-in

Esta é a primeira etapa real, não a substituição completa do Tkinter. O caminho Tk
permanece disponível durante a homologação. Nunca mantenha dois programas abertos
sobre o mesmo banco. Faça backup antes de homologar em uma cópia dos dados.

## Início

Use Python 3.10+ e instale as dependências do projeto, incluindo
`PySide6-Essentials>=6.7,<7` (Qt Core/Gui/Widgets; não exige WebEngine).
Depois da integração do seletor no ponto de entrada:

```text
python -m src.app --qt
python -m src.app --tk
```

Também existe uma entrada direta do piloto, com as mesmas proteções:

```text
python -m src.ui_qt.app
```

Se Qt não estiver instalado ou falhar, o início deve informar o erro e encerrar.
Não há fallback silencioso nem abertura de Tk dentro do processo Qt.
`--sync` continua sendo um modo separado do programa, não uma promessa de
sincronização contínua pelo painel Qt.

## O que já existe

- Login Qt com o `AcessoController` existente: senhas, tentativas/bloqueio e
  troca obrigatória da senha igual ao nome (inclusive ADM/ADM).
- Licença local pelas APIs existentes, preservando carência, relógio e isenção
  de turno recente. Ativação manual de código e consulta online em thread:
  só a rede sai da thread Qt; o banco e os widgets permanecem na thread principal.
  A consulta respeita a agenda/repetição existente, com tentativa forçada quando
  a licença está bloqueada. Falha de rede nunca concede autorização adicional.
- Menu principal com sessão, permissões, turno e estados reais de licença,
  último backup e consulta da nuvem. “Serviço iniciado” não significa impressão,
  mensagem entregue ou sincronização concluída.
- Produtos e operadores: listagem, pesquisa, inclusão, edição e exclusão.
  Campos/seções/lookups são derivados das entidades originais; conversões,
  centavos, validações, hashing e salvaguardas continuam no `CadastroController`.
  Edição de operador com senha vazia mantém a senha. Permissões são conferidas
  novamente antes de salvar/excluir, inclusive se o nível mudou com a tela aberta.
- Caixa aberto por `JanelaCaixa(ctx, parent)` em janela Qt não bloqueante,
  com referência conservada pelo menu. Seu escopo operacional é incremental;
  consulte os avisos da própria tela durante a homologação.
  Sem turno, exibe abertura pelo controlador (que valida licença). A troca de
  turno permanece nessa janela e volta à abertura. Fechamento é recusado durante
  gravações; balcão com itens pede confirmação para manter a venda aberta;
  mesa/comanda vazia é descartada ao sair. O turno nunca é fechado sozinho.
- Comissão das garotas no caixa Qt (`src/ui_qt/comissao.py`), pelos mesmos
  `ComissaoController`, `ImpressaoController` e `AcessoController` do Tk:
  código 50 na linha de entrada com `comissao_na_linha` ligada (Garota nº +
  valor/pontos, Enter avança, Esc descarta) ou pela janela com ela desligada.
  Mesmas senhas (`caixa_comissao`/`exigir_senha_comissao`, pagamento
  `caixa_pagar_comissao`/`exigir_senha_sangria`, cancelamento
  `caixa_cancelamento`/`exigir_senha_cancelamento`), mesmas perguntas (não
  cadastrada, inativa, valor alto) e a via da garota (`imprimir_via_comissao`).
  As comissões marcadas aparecem na comanda da garota; F12 ou "Pagar a garota"
  abre o acerto (shows, vale, Pix, se sai da gaveta) com recibo e, se houve
  sangria, comprovante de saída. Botão Comissões lista, lança, paga e cancela.
- Saída sem consumo (código 1002): libera a comanda/mesa vazia (ou pergunta qual),
  pelo `CaixaController.liberar_saida`, e emite o ticket de saída. Com consumo é
  recusada sem alterar a venda.
- Encerrar sessão fecha as janelas e volta ao login; um caixa que recusa fechamento
  impede o logout. Encerrar sessão ou programa não fecha o turno automaticamente.
- Auditoria administrativa, somente leitura: acessível pelo menu para administrador
  ativo de nível 4 com `rel_auditoria`. Usa exclusivamente `ctx.auditoria.listar`,
  com filtros de início/fim ISO local inclusivos e ação (seleção ou código exato),
  páginas de 100 eventos e retratos JSON antes/depois. Os valores monetários dos
  retratos permanecem em centavos; senhas são omitidas pelo mecanismo de auditoria.
  Não há edição, exclusão nem consulta ao backend. Página cheia pode ter sucessora;
  não se inventa um total. A autorização é revalidada no controlador ao consultar,
  reabrir a tela e selecionar detalhes; acesso negado limpa os dados exibidos.
  Não é um monitor em tempo real: reaplique filtros/reabra para atualizar.
- Backup externo cifrado (permissão `util_backup`): configuração, exportação manual,
  verificação com senha, preparação de restauração e desativação, pelos métodos
  existentes do `UtilitarioController`. Senha de recuperação tem mínimo de 12
  caracteres e deve ser digitada duas vezes na configuração/exportação.
  A interface não grava senha em QSettings ou no banco. Guarde-a fora do PC.
  Configuração automática depende de DPAPI no Windows; exportação manual solicita
  a senha na hora e exige uma pasta previamente configurada no controlador.
  A cópia cifrada não prova upload para a nuvem. Restauração exige digitar
  `RESTAURAR`, é apenas preparada e acontece no próximo início protegido.

## Proteções e ciclo de vida

`preparar_inicio()` consome `InstanciaUnica`, `protecao.preparar_banco` e
`registro.configurar_logs`, as mesmas APIs do bootstrap atual, usando apenas
perguntas Qt. A trava é mantida até a saída. Cancelamento, falha de integridade
ou erro de início não permitem continuar sem proteção.

Com banco em arquivo, o ciclo executa backup inicial quando ausente/antigo
(12 horas), backup de saída com intervalo mínimo de 60 minutos e inicia/para os
serviços já existentes de impressão e Telegram. Falhas ficam no log e no estado
do painel; não são exibidas como sucesso. A instância padrão do banco é fechada
ao sair.

`App(banco=..., aplicacao=...)` aceita banco em memória e `QApplication` existente
para testes/integração. Um banco injetado pertence ao chamador e não é fechado
pelo aplicativo. Bancos em memória não iniciam serviços de arquivo nem backups.
O construtor `App` não substitui o bootstrap protegido: produção usa `main()`.
Quando já há `QApplication`, `main()` não chama `exec()` novamente e conserva o
aplicativo e a trava até `aboutToQuit`; o hospedeiro é responsável pelo loop.

Temporizadores são parados ao fechar as janelas. A consulta online recebe um
sinal de cancelamento e descarta resultados tardios sem acessar banco/widgets.
Uma requisição HTTP já em curso não pode ser interrompida pelo binding Qt:
ela termina sob os timeouts de conexão/leitura (3/5 segundos), em thread daemon,
sem segurar o processo. Não se usa `terminate()` inseguro.

## Limites assumidos

Demais relatórios, estoque, financeiro, configurações, demais
cadastros, importação, restauração local sem cifragem, assistência de impressão e outras
telas não foram migrados neste piloto. O menu os identifica como indisponíveis.
Para esses recursos, encerre o processo e inicie com `--tk`.

No caixa Qt também estão bloqueados, com orientação ao caixa clássico:
partes/montagem, desconto/serviço manual, observação, transferência, pré-conta,
caderneta, entrega, sangria/repique, gaveta, balança e reimpressão. Não homologue
um fluxo que dependa desses recursos como se já estivesse migrado. Da comissão
ficam só no Tk a consulta de comanda (que mostra a comissão pendente) e o modo
"cancelar" com senha única para várias linhas.

Não há configuração de nuvem, loja, impressoras ou visual pelo Qt nesta etapa:
prepare esses dados pelo Tk antes da homologação. O tema do piloto é escuro fixo;
não altera a configuração de aparência do Tk. Não há atualização automática do
programa nem sincronização contínua de vendas no Qt. Status de backup/licença
não substitui os testes de recuperação e de periféricos reais.

## Testes

Os testes importam Qt de verdade; pacote ausente é erro de dependência, não
motivo para pular silenciosamente:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest tests.test_qt_app tests.test_qt_caixa tests.test_qt_comissao
```

Há cobertura de autenticação, troca obrigatória, bloqueio por licença,
isenção de turno, consulta não bloqueante/cancelamento, formulários, centavos,
permissões, sessões, integração de janela de caixa, proteções iniciais e ciclo
de backup/serviços. Banco de teste é em memória e não usa a loja.
Comissão e saída cobrem os modos na linha/janela, conversão pontos/reais,
autorizações de supervisor, confirmações de cadastro/valor, acerto com shows,
vale e Pix, cancelamento, F12 e preservação dos registros quando a impressão falha.
Homologue também teclado, escala de tela, leitores, impressoras e os fluxos
operacionais efetivamente disponíveis no caixa.

Para integração com `--autoteste`, `src.ui_qt.app.autoteste(pasta: Path) -> list[str]`
reaproveita `QApplication` quando existente, abre menu e os dois cadastros reais,
confere comissão na linha, painel, diálogos de comissão/acerto e saída sem consumo,
fecha tudo e processa destruições pendentes. O turno é um cenário inserido somente
no banco em memória: não ativa licença nem modifica a exigência de produção.
O banco efêmero é em memória; a pasta
é aceita pelo protocolo do autoteste, mas não recebe arquivos. Não inicia rede,
periféricos, serviços nem o bootstrap sobre o banco de loja. Falhas levantam exceção;
sucesso devolve mensagens para o relatório do chamador.

## Distribuição e licenças

PySide6/Qt for Python oferece licenciamento LGPLv3/GPLv3 e comercial, com termos
específicos dos componentes distribuídos. O piloto usa Core/Gui/Widgets.
Antes de distribuir instaladores, confira os textos e avisos de licença das
versões efetivamente incluídas, componentes de terceiros e obrigações aplicáveis
ao método de empacotamento/redistribuição. Esta documentação não é parecer jurídico
nem afirma que uma forma de distribuição está automaticamente em conformidade.

Referências oficiais:
- https://doc.qt.io/qtforpython-6/licenses.html
- https://doc.qt.io/qt-6/licensing.html
