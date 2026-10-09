# Gerar, baixar, instalar e testar o WillPDV no Windows

O GitHub Actions gera o programa para você: um instalador (`WillPDV-Setup-<versão>.exe`) e uma versão portátil (a pasta do
programa, sem instalar). Não precisa de Python nem de Inno Setup no seu PC.

## 1. Gerar o instalador

O workflow é o `.github/workflows/build-windows.yml` ("Gerar instalador (Windows)"). Ele roda sozinho a cada push na `main`
ou numa branch `claude/...`, e também sob demanda:

1. No GitHub, abra a aba **Actions** > **Gerar instalador (Windows)**.
2. **Run workflow**, escolha a branch e confirme. (O botão só aparece depois que o arquivo do workflow está na `main`; até lá,
   o push na branch já dispara a geração sozinho.)
3. Espere uns 6 a 12 minutos. Ao final a execução fica verde.

O workflow não entrega um programa quebrado: depois de gerar, ele **abre o programa empacotado** (autoteste: módulos, banco,
menu, telas e conexão HTTPS com o Telegram), **instala o instalador de verdade** num diretório de teste, roda o autoteste no
programa instalado e desinstala. Se qualquer etapa falhar, a execução fica vermelha e não há instalador para baixar.

## 2. Baixar

Abra a execução (clique no nome dela em Actions) e role até **Artifacts**:

| Artifact | O que é |
| --- | --- |
| `WillPDV-Instalador-<versão>-<commit>` | o instalador (`WillPDV-Setup-<versão>.exe`) dentro de um .zip que o GitHub cria |
| `WillPDV-Portatil-<versão>-<commit>` | a pasta do programa em .zip: extraia e rode `WillPDV.exe`, sem instalar |
| `autoteste-<commit>` | os relatórios do autoteste (útil se algo falhar) |

Baixe o primeiro, extraia o .zip e use o `.exe` de dentro. A página da execução também mostra o tamanho e o SHA-256 do
instalador, para você conferir o arquivo. Os artifacts ficam 30 dias. Para um link fixo (que dá para mandar a um cliente), crie
uma tag: `git tag v1.2.0 && git push origin v1.2.0`. O instalador vai para a aba **Releases**, sem .zip.

## 3. Instalar

Dê dois cliques no `WillPDV-Setup-<versão>.exe` > Avançar > Instalar. O programa vai para `Arquivos de Programas\WillPDV`, com
atalho na Área de Trabalho e no Menu Iniciar.

- **"O Windows protegeu o seu computador" (SmartScreen):** o instalador ainda não tem assinatura digital paga, então o Windows
  desconfia de qualquer programa novo. Clique em **Mais informações > Executar assim mesmo**. Se o antivírus reclamar (é comum
  com programas empacotados em PyInstaller), libere o arquivo ou a pasta `WillPDV`.
- Windows de 64 bits.
- Os dados (banco, backups, licença, logs) ficam em `%LOCALAPPDATA%\WILL-PDV`, não na pasta do programa: atualizar ou
  desinstalar **não apaga as vendas**. Para atualizar, rode o instalador novo por cima (com o turno fechado).

## 4. Primeira abertura: o código de licença

No programa instalado a licença é **sempre exigida**. Na tela de entrada, o botão **Código de licença...** pede um código que
**você** gera no seu PC (o que tem a chave privada), com Python instalado, na pasta do projeto:

```powershell
python -m tools.gerar_licenca emitir --loja TESTE --dias 30
```

Cole a linha que começa por `PDVL1.` e confirme. Depois entre com **ADM / ADM**: o sistema obriga a trocar a senha. Se você
ainda não tem o par de chaves, veja "Como emitir as licenças" no `README.md` (a chave pública que vai no programa é a de
`src/core/licenca.py`; um código só vale se foi emitido pela chave privada correspondente).

## 5. Roteiro rápido de teste (uns 15 minutos)

1. Entrar (ADM, trocar a senha) e olhar o **menu novo**: setas + Enter, letras de atalho, cartões do painel.
2. **Configurações > Loja**: cadastrar o nome da casa.
3. **Cadastros > Produtos**: criar 2 produtos; **Lançamentos > Estoque**: lançar saldo (`50 skol`).
4. **Caixa**: abrir turno com fundo de caixa, vender no balcão e numa comanda, pagar em dinheiro e Pix, cancelar um item e uma
   venda, fazer uma sangria, **fechar o turno** e olhar a diferença.
5. **Utilitários > Backup de dados** e conferir o aviso verde no menu.
6. **Telegram** (opcional): `docs/TELEGRAM.md`. Precisa de internet no PC.
7. Impressora térmica e gaveta, se tiver: Configurações > Máquinas (`docs/PILOTO.md`).

## 6. Se algo der errado

- Rode o autoteste no PC (cria um relatório com o que está faltando):

  ```powershell
  & "C:\Program Files\WillPDV\WillPDV.exe" --autoteste "$env:USERPROFILE\Desktop\autoteste.txt" --rede
  ```

- Em **Utilitários > Pacote de suporte** o programa junta os registros de erro (nunca as vendas) para você me mandar.
- Os registros ficam em `%LOCALAPPDATA%\WILL-PDV\logs`.
- **Se o workflow ficar vermelho em poucos segundos**, sem rodar nenhum passo, o problema não é o código: é a conta do GitHub
  (por exemplo limite de uso ou cobrança do Actions). Abra o job na aba Actions e leia a mensagem no topo.

## Para quem mantém o sistema

- A cada versão nova: suba o número em `src/versao.py` e faça o push. O nome do artifact leva a versão e o commit.
- Módulo novo em `src/` precisa entrar em `MODULOS` (`src/autoteste.py`): um teste cobra isso, porque o PyInstaller só leva o
  que enxerga por `import` e o autoteste é quem prova que nada ficou de fora.
- Para gerar local, no Windows: `pip install -r requirements.txt pyinstaller` e `python build_pdv.py` (precisa do Inno Setup 6).
