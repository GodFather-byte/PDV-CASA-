import time
import requests # Você vai precisar instalar: pip install requests
from src.database.conexao import BancoDados

class Sincronizador:
    def __init__(self):
        self.banco = BancoDados()
        # URL do seu futuro servidor (onde você vai ver os relatórios)
        self.api_url = "https://api.seupdv.com.br/v1/sincronizar"

    def verificar_conexao(self):
        """
        Testa se tem internet tentando acessar o Google rapidinho.
        """
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except:
            return False

    def enviar_vendas_pendentes(self):
        """
        O coração do sistema offline-first.
        """
        # 1. Busca vendas não sincronizadas (sincronizado = 0)
        cursor = self.banco.conexao.cursor()
        cursor.execute("SELECT * FROM vendas WHERE sincronizado = 0")
        vendas_pendentes = cursor.fetchall()

        if not vendas_pendentes:
            print("Nada para sincronizar.")
            return

        print(f"Encontrei {len(vendas_pendentes)} vendas offline. Tentando enviar...")

        if not self.verificar_conexao():
            print("Sem internet. Tentarei novamente mais tarde.")
            return

        # 2. Loop de envio (Simulação por enquanto)
        for venda in vendas_pendentes:
            venda_id = venda[0]
            total = venda[2]
            
            # AQUI ENTRARIA O CÓDIGO REAL DE ENVIO PARA SUA API
            enviado_sucesso = self._simular_envio_api(venda)

            if enviado_sucesso:
                # 3. Se a API confirmou o recebimento, atualizamos o banco local
                cursor.execute("UPDATE vendas SET sincronizado = 1 WHERE id = ?", (venda_id,))
                self.banco.conexao.commit()
                print(f"Venda {venda_id} (R$ {total}) sincronizada com sucesso!")

    def _simular_envio_api(self, dados_venda):
        """
        MOCK: Finge que enviou para a nuvem.
        No futuro, trocaremos isso por um 'requests.post(self.api_url, json=dados)'
        """
        time.sleep(0.5) # Simula o delay da internet
        return True # Finge que deu certo sempre

    def iniciar_loop(self, intervalo=60):
        """
        Roda infinitamente a cada X segundos.
        """
        print("Robô de sincronização iniciado...")
        while True:
            self.enviar_vendas_pendentes()
            time.sleep(intervalo)

if __name__ == "__main__":
    robo = Sincronizador()
    robo.iniciar_loop(intervalo=10) # Tenta sincronizar a cada 10 segundos para teste
