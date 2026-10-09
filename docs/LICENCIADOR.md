# WillPDV Licenças: o programa que emite as licenças

É um programa **separado do PDV**, só para quem vende o sistema. Você escolhe a loja e o tipo de licença, toca em **Gerar licença** e
copia o código (ou uma mensagem pronta) para mandar ao cliente. Não precisa de Python nem de linha de comando.

> **Não entregue este programa a clientes.** O cliente só recebe o *código* da licença. Quem tem este programa **e a chave de
> segurança** emite licenças.

## Tipos de licença

| Tipo | Quando usar | Validade |
| --- | --- | --- |
| **Mensal** | a loja que paga todo mês (ou a cada 3, 6, 12 meses) | de 1 a 60 **meses de calendário**: 1 mês a partir de 09/10 vai até 09/11 |
| **Permanente** | a loja que comprou o sistema | sem vencimento na prática (100 anos) |
| **Teste** | demonstração para quem ainda não contratou | de 1 a 90 dias |

Como o PDV se comporta: avisa **7 dias antes** de vencer, dá **5 dias de carência** depois do vencimento e só então bloqueia a
entrada (nunca com um turno recente aberto). Renovar é emitir um código novo e mandar de novo: a loja cola no mesmo lugar.

## Instalar

1. No GitHub: aba **Actions > Gerar instalador (Windows)** > execução mais recente > **Artifacts** >
   `WillLicencas-Instalador-<versão>-<commit>`. Baixe, extraia o .zip e rode `WillLicencas-Setup-1.0.0.exe`.
2. Se o Windows avisar "protegeu o seu computador", clique em **Mais informações > Executar assim mesmo** (o instalador ainda não
   tem assinatura digital paga).
3. Não pede senha de administrador. Pode ficar instalado junto com o PDV no mesmo computador.

## Primeira vez: a chave de segurança

A chave de segurança é o que prova que a licença é sua. Ela é um arquivo (`licenca_privada.key`) que fica **só neste
computador**, em `C:\Users\SEU_USUARIO\.pdv-casa\`. Abra a aba **Chave de segurança**:

- **Já emitia licenças pelo PC e tem a chave?** Se for o mesmo computador, ela já aparece como *"conferida: combina com a do PDV"*.
  Se for outro, use **Importar chave...** e escolha o arquivo `licenca_privada.key`.
- **Aparece "Esta chave NÃO é a do PDV"?** É uma chave diferente da que o PDV carrega: os caixas recusariam as licenças. Importe a
  chave certa (a que foi usada para criar o PDV).
- **Nunca criou uma chave?** Use **Criar chave nova** e depois coloque a *chave pública* mostrada na tela em `CHAVE_PUBLICA_HEX`
  (arquivo `src/core/licenca.py`) e gere o PDV de novo. **Só faça isso uma vez:** trocar a chave invalida todas as licenças já
  emitidas.
- Faça logo uma **cópia de segurança** (botão da mesma aba, num pendrive). Sem a chave não se emite mais licença, e **ela não está
  no GitHub nem em lugar nenhum além do seu computador e das suas cópias**.

## Emitir uma licença

1. Aba **Emitir licença**. Digite a **loja** (a mesma chave de loja do PDV; as já usadas aparecem na lista).
2. Escolha **Mensal** (e quantos meses), **Permanente** ou **Teste** (e quantos dias). A tela mostra até quando vale.
3. **Gerar licença**. Aparece o código (`PDVL1....`).
4. **Copiar mensagem pronta para o cliente** (já traz o código e o passo a passo) ou **Copiar código** ou **Salvar em arquivo**.
5. No caixa do cliente: tela de entrada > **Código de licença...** > colar > confirmar.

## Acompanhar e renovar

A aba **Lojas e vencimentos** mostra cada loja uma vez, com a licença mais nova: vermelho = vencida, amarelo = vence em até 7 dias.
Selecione uma loja e toque em **Renovar a selecionada**: o formulário já vem preenchido com o mesmo tipo e prazo.

O histórico fica em `C:\Users\SEU_USUARIO\AppData\Local\WillPDV-Licencas\historico.json` (guarda o código de cada licença emitida).

## Conferir um código

Aba **Conferir um código**: cole um código e veja de que loja é, quando foi emitido e até quando vale (útil quando o cliente liga
perguntando por que "não entra").

## Atualizar ou desinstalar

Rode o instalador novo por cima: se o programa estiver aberto o instalador avisa e fecha. A chave e o histórico **não** são apagados
ao atualizar nem ao desinstalar.

## Logotipo

O ícone e as imagens dos instaladores (do PDV e deste programa) ficam em `instalador/`. Para usar a sua marca, troque
`willpdv.ico`, `willpdv-assistente.bmp` (164x314) e `willpdv-assistente-pequena.bmp` (55x55), e os `willlicencas-*` equivalentes, mantendo
os nomes. Para regenerar os desenhos padrão: `pip install pillow` e `python -m tools.gerar_logos`.

## Para quem mantém o sistema

- Código em `licenciador/` (`nucleo.py` = regras, `tela.py` = janela, `autoteste.py`, `app.py` = entrada). Mesmo formato de chave e de
  código do `tools/gerar_licenca.py` (que continua funcionando).
- Gerar localmente no Windows: `pip install pyinstaller` e `python build_licenciador.py` (precisa do Inno Setup 6; sem ele só o `.exe`).
- No GitHub, o job "Programa de licenças" do workflow *Gerar instalador (Windows)* gera, testa (autoteste no `.exe`, instalação
  silenciosa e atualização por cima com o programa aberto) e guarda o instalador como artifact. **Não** vai para a aba Releases.
- Testes: `python -m unittest tests.test_licenciador`.
