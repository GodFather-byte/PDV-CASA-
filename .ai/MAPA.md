# Mapa do repositório

O repositório gera dois programas Windows: **WillPDV** (o PDV do cliente) e **WillPDV Licenças**
(gerador de licenças, só do fornecedor). Python + SQLite + Tkinter.

## Pontos de entrada

| Comando | O que abre |
|---|---|
| `python -m src.app` | PDV (`--sync`: segundo plano com a nuvem; `--autoteste`: autoteste) |
| `python -m licenciador.app` | Gerador de licenças |
| `python -m tools.gerar_licenca` | Licenças pela linha de comando (`novo-par`, `emitir`, `ver`) |
| `python -m uvicorn backend.main:app` | API da nuvem |
| `python -m backend.lojas` / `backend.atualizacoes` | Lojas, assinatura e versões na nuvem |
| `python build_pdv.py` / `build_licenciador.py` | Executável (PyInstaller) e instalador (Inno Setup) |

## Pastas

| Pasta | O que tem |
|---|---|
| `src/core/` | Dinheiro e datas (`formatacao.py`), licença Ed25519 (`licenca.py`, `ed25519.py`), senhas (`seguranca.py`), erros de negócio (`erros.py`), comanda e mesa (`posicao.py`), log (`registro.py`), base dos relatórios (`relatorio.py`), instância única (`instancia.py`) |
| `src/database/` | `esquema.py` (tabelas, `VERSAO_ESQUEMA`, `MIGRACOES`), `conexao.py`, `protecao.py` (integridade e backup), `sementes.py` (dados iniciais) |
| `src/controllers/` | Regras de negócio, um arquivo por assunto (lista abaixo) |
| `src/ui/` | Telas Tkinter: `app.py` (janela principal), `caixa_ui.py` (caixa), `login.py`, `tema.py` e uma tela por módulo |
| `src/hardware/` | Impressora térmica ESC/POS e gaveta, balança, logotipo no cupom, impressoras do Windows |
| `src/sync/` | `sincronizador.py`, `licenca_nuvem.py`, `atualizacoes.py`, `telegram_api.py` |
| `licenciador/` | `nucleo.py` (regras), `tela.py` (janela), `app.py`, `autoteste.py` |
| `backend/` | FastAPI: `main.py` (rotas), `lojas.py`, `atualizacoes.py`, `database.py` |
| `tools/` | `gerar_licenca.py`, `gerar_logos.py` (não vão no instalador do PDV) |
| `instalador/` | Scripts Inno Setup (`WillPDV.iss`, `WillLicencas.iss`) e imagens |
| `tests/` | Um `test_*.py` por assunto; `base.py` (banco em memória, relógio controlável); `ui_robo.py` (robô das janelas modais) |
| `docs/` | Guias por assunto (lista abaixo) |
| `.github/workflows/` | `testes.yml` (suíte) e `build-windows.yml` (instaladores) |

## Onde fica cada regra (`src/controllers/`)

| Assunto | Arquivo |
|---|---|
| Venda, itens, pagamento, mesas e comandas | `caixa_controller.py` |
| Turno, numeração de cupom, fechamento | `turno_controller.py`, `conferencia_turno.py` |
| Comissão das garotas | `comissao_controller.py`, `relatorio_comissoes.py` |
| Estoque (baixa, estorno, composição) | `estoque_controller.py` |
| Produtos e importação por planilha | `produto_controller.py`, `importacao_produtos.py` |
| Cadastros e entidades | `cadastro_controller.py`, `entidades.py` |
| Operadores e níveis de acesso | `acesso_controller.py` |
| Configurações da loja | `config_controller.py` (padrões em `CONFIG_PADRAO`, `src/database/sementes.py`) |
| Caderneta (venda a prazo) e contas | `caderneta_controller.py`, `contas_controller.py` |
| Entrega | `entrega_controller.py` |
| Impressão e fila | `impressao_controller.py`, `fila_impressao_controller.py`, `impressao_assistente.py` |
| Relatórios | `relatorio_controller.py`, `relatorio_vendas.py`, `relatorio_gestao.py` |
| Telegram do dono | `telegram_controller.py`, `telegram_textos.py`, `notificacoes.py` |
| Backup, limpeza e utilitários | `utilitario_controller.py` |

## Documentação (`docs/`)

`ESPECIFICACAO.md` (o que o sistema deve fazer), `INSTALAR_E_TESTAR.md`, `LICENCIADOR.md`,
`NUVEM.md`, `TELEGRAM.md`, `IMPRESSORA.md`, `ESTOQUE.md`, `IMPORTAR_PRODUTOS.md`, `PILOTO.md`,
`COORDENACAO.md` (histórico de pedidos entre agentes).

## Dados

Banco padrão `loja_offline.db` na raiz (no executável: `%LOCALAPPDATA%\WILL-PDV`); outro
arquivo pela variável `PDV_DB`. Bancos, `.env`, `config.ini` e `*.key` nunca vão para o git.
