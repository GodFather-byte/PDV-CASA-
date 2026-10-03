import time
import requests
from src.database.conexao import BancoDados
from src.controllers.sync_controller import SyncController

class Sincronizador:
    def __init__(self):
        self.banco = BancoDados()
        self.sync_ctrl = SyncController(self.banco)
        # URL do backend FastAPI (Evicommerce)
        self.api_url = "http://localhost:8000/v1/sincronizar"
        self.token = "MeuTokenSuperSeguro"

    def verificar_conexao(self):
        try:
            requests.get("http://localhost:8000/docs", timeout=3)
            return True
        except requests.RequestException:
            return False

    def enviar_vendas_pendentes(self):
        pendentes = self.sync_ctrl.contagem_pendentes()
        if pendentes == 0:
            return

        print(f"Encontrei {pendentes} vendas offline. Montando lote...")

        if not self.verificar_conexao():
            print("Sem conexao com backend. Tentarei novamente mais tarde.")
            return

        lote = self.sync_ctrl.montar_lote(limite=50)
        
        try:
            resposta = requests.post(
                self.api_url, 
                json=lote, 
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            
            if resposta.status_code == 200:
                dados = resposta.json()
                aceitas = dados.get("aceitas", [])
                
                if aceitas:
                    confirmadas = self.sync_ctrl.confirmar(aceitas)
                    print(f"Sucesso: {confirmadas} vendas sincronizadas (confirmadas)!")
                else:
                    print("Servidor nao retornou UUIDs confirmados.")
            else:
                print(f"Erro no servidor ({resposta.status_code}): {resposta.text}")
                
        except requests.RequestException as e:
            print(f"Erro de rede ao enviar lote: {e}")

    def iniciar_loop(self, intervalo=60):
        print("Robo de sincronizacao iniciado...")
        while True:
            self.enviar_vendas_pendentes()
            time.sleep(intervalo)

if __name__ == "__main__":
    robo = Sincronizador()
    robo.iniciar_loop(intervalo=10)
