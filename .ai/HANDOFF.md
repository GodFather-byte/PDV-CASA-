# HANDOFF

## Último trabalho: limite de R$ 200,00 nas comandas dos clientes
- `CaixaController._conferir_limite_comanda` (chamado em `adicionar_item`): comanda (não mesa/balcão/caderneta) cujo consumo
  (itens não cancelados) já chegou ao limite não aceita mais lançamento: "é preciso acertar a comanda".
- Configuração `limite_comanda` (R$, padrão 200, 0 = sem limite) em Configurações > Mesas e serviço. Vale na mesma faixa de números
  da consumação mínima (`consumacao_minima_de/ate`), para deixar de fora as comandas das garotas.
- Teste: `tests/test_limite_comanda.py`. Suíte inteira: 1.224 OK.

## Anterior (já mesclado)
Modo claro/escuro (PR #49): `src/ui/paleta.py`, escolha em Configurações > Aparência. Mudar o modo fecha as janelas abertas;
validar o modo claro no caixa do Windows.

## Pendências
Nenhuma.
