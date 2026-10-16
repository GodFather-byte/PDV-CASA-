# HANDOFF

## Último trabalho: reusar o número de produto excluído/guardado; fim do instalador de licenças no Actions
- `entidades._antes_produto` chama `_liberar_produtos_guardados`: cadastro de produto que pede um código, nome ou código de barras
  preso a um produto INATIVO (guardado por já ter sido vendido, ex. depois de "Excluir todos os produtos") faz o inativo ceder
  (`_guardar_produto`: código `COD~id`, nome "(excluído id)", atalho e cbarra limpos). Produto ativo continua bloqueando.
- `.github/workflows/build-windows.yml`: removido o job `licenciador`; o workflow gera só o WillPDV. README e
  `docs/LICENCIADOR.md` dizem para gerar o instalador de licenças na máquina (`python build_licenciador.py`).
- Testes: `tests/test_excluir_produto_cadastrado.py`.

## Anteriores (já mesclados)
Excluir produto cadastrado (PR #51), limite de R$ 200 por comanda (#50), modo claro/escuro (#49).

## Pendências
Nenhuma.
