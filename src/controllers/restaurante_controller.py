from src.database.conexao import get_banco
from src.core.seguranca import ErroNegocio

class RestauranteController:
    """Controlador com regras de negócio específicas para Restaurantes, Bares e Pizzarias (Manuais 1 e 2)."""
    
    def __init__(self):
        self.banco = get_banco()

    def enviar_para_cozinha(self, numero_mesa: int, produto_nome: str, observacao: str):
        """
        Simula a impressão remota na cozinha (Impressora Não Fiscal / F8).
        Gera um registro que um serviço de spooler leria para imprimir fisicamente.
        """
        texto_impressao = f"MESA {numero_mesa} | {produto_nome} | OBS: {observacao}"
        with self.banco.transacao():
            self.banco.executar(
                "INSERT INTO log_eventos (quando, evento, detalhe) VALUES (datetime('now', 'localtime'), 'COZINHA', ?)",
                (texto_impressao,)
            )

    def registrar_repique(self, garcom_id: int, valor_repique_cent: int, numero_mesa: int):
        """
        Registra a Caixinha (Repique / Tecla F9) deixada pelo cliente para o garçom.
        Esse valor não entra como faturamento de produto, vai direto para a conta do Garçom/Repique.
        """
        with self.banco.transacao():
            # Insere no log ou numa tabela de comissões futura
            self.banco.executar(
                "INSERT INTO log_eventos (quando, operador_id, evento, detalhe) VALUES (datetime('now', 'localtime'), ?, 'REPIQUE', ?)",
                (garcom_id, f"Caixinha Mesa {numero_mesa}: R$ {valor_repique_cent/100:.2f}")
            )

    def calcular_divisao_pizza(self, produtos_ids: list[int], tipo_cobranca: str = "maior"):
        """
        Lida com o 'Dividir em' do manual para Pizzarias (Meio a Meio).
        tipo_cobranca pode ser 'maior' ou 'media'.
        """
        if not produtos_ids: return 0
        
        precos = []
        for pid in produtos_ids:
            p = self.banco.um("SELECT preco_venda_cent FROM produtos WHERE id = ?", (pid,))
            if p: precos.append(p["preco_venda_cent"])
            
        if not precos: return 0
        
        if tipo_cobranca == "maior":
            return max(precos)
        else:
            return sum(precos) / len(precos)
