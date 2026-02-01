import sys
import os
import time

# Adiciona o diretório raiz ao caminho do Python para os imports funcionarem
sys.path.append(os.getcwd())

from src.controllers.produto_controller import ProdutoController
from src.controllers.venda_controller import VendaController
from src.sync.sincronizador import Sincronizador

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def menu_principal():
    # Instancia os controladores
    prod_ctrl = ProdutoController()
    venda_ctrl = VendaController()
    sync_robo = Sincronizador()

    while True:
        limpar_tela()
        print("=== PDV BOATE SYSTEM (OFFLINE FIRST) ===")
        print("1. 📦 Cadastrar Produto (Estoque)")
        print("2. 💰 Realizar Venda (Simular Caixa)")
        print("3. 🔄 Sincronizar com Nuvem (Simular Internet)")
        print("4. ❌ Sair")
        print("========================================")
        opcao = input("Escolha uma opção: ")

        if opcao == '1':
            nome = input("Nome do Produto: ")
            preco = float(input("Preço (R$): "))
            cod = input("Código de Barras: ")
            sucesso, msg = prod_ctrl.cadastrar_produto(nome, preco, cod, estoque_inicial=100)
            print(msg)
            time.sleep(2)

        elif opcao == '2':
            print("\n--- NOVA VENDA ABERTA ---")
            id_venda = venda_ctrl.iniciar_venda()
            total_venda = 0.0
            
            while True:
                codigo = input("Bipe o produto (ou 'F' para fechar): ")
                if codigo.upper() == 'F':
                    break
                
                produto = prod_ctrl.buscar_por_codigo(codigo)
                if produto:
                    # produto retorna uma tupla: (id, cod, nome, preco, estq)
                    print(f" -> {produto[2]} | R$ {produto[3]:.2f}")
                    venda_ctrl.adicionar_item(id_venda, produto[0], 1, produto[3])
                    total_venda += produto[3]
                    print(f"Subtotal: R$ {total_venda:.2f}")
                else:
                    print("Produto não encontrado!")
            
            pagamento = input("Forma de Pagamento (Dinheiro/Pix/Cartão): ")
            venda_ctrl.finalizar_venda(id_venda, total_venda, pagamento)
            print(f"Venda {id_venda} finalizada! Salvo localmente.")
            time.sleep(3)

        elif opcao == '3':
            print("\n--- INICIANDO SINCRONIZAÇÃO ---")
            print("Verificando vendas paradas no banco local...")
            sync_robo.enviar_vendas_pendentes()
            input("\nPressione ENTER para voltar...")

        elif opcao == '4':
            print("Fechando sistema...")
            break

if __name__ == "__main__":
    menu_principal()
  
