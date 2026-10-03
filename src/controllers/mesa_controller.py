from src.database.conexao import get_banco
from src.core.formatacao import agora, para_centavos
from src.core.seguranca import ErroNegocio
import sqlite3

class MesaController:
    """Controlador para as operações de Mesas (Item 6.05 do Manual e Operações do Caixa)."""

    def __init__(self):
        self.banco = get_banco()

    def abrir_mesa(self, numero_mesa: int, garcom_id: int = None):
        """Abre uma nova mesa."""
        with self.banco.transacao():
            # Verifica se já está aberta
            mesa = self.banco.um("SELECT id, status FROM mesas WHERE numero = ?", (numero_mesa,))
            if mesa and mesa["status"] == "aberta":
                raise ErroNegocio(f"A mesa {numero_mesa} já está aberta.")

            if mesa:
                # Reabre mesa existente (se foi fechada)
                self.banco.executar("UPDATE mesas SET status = 'aberta', garcom_id = ?, total_cent = 0, servico_cent = 0 WHERE id = ?",
                                    (garcom_id, mesa["id"]))
                return mesa["id"]
            else:
                # Cria nova mesa
                mesa_id = self.banco.inserir("mesas", {
                    "numero": numero_mesa,
                    "status": "aberta",
                    "garcom_id": garcom_id,
                    "total_cent": 0,
                    "servico_cent": 0
                })
                return mesa_id

    def listar_mesas_abertas(self):
        """Retorna todas as mesas com status 'aberta' para o grid do caixa."""
        query = """
            SELECT m.*, o.nome as garcom_nome
            FROM mesas m
            LEFT JOIN operadores o ON m.garcom_id = o.id
            WHERE m.status = 'aberta'
            ORDER BY m.numero
        """
        return [dict(r) for r in self.banco.todos(query)]

    def adicionar_item_mesa(self, numero_mesa: int, produto_id: int, quantidade: float, preco_unitario: float):
        """Adiciona um item na mesa e atualiza os totais (Subtotal e Serviço)."""
        from src.controllers.venda_controller import VendaController
        # Usa o VendaController ou lógica própria para lançar na mesa

        # Como o esquema atual pode não ter uma tabela de `itens_mesa`,
        # precisamos garantir que ela existe, ou usar `vendas` com um campo `mesa_id`.
        # Vamos assumir que a Mesa está atrelada a uma Venda Aberta.

        mesa = self.banco.um("SELECT * FROM mesas WHERE numero = ? AND status = 'aberta'", (numero_mesa,))
        if not mesa:
            # Se não existe e alguém quer lançar direto, a gente abre
            mesa_id = self.abrir_mesa(numero_mesa)
            mesa = self.banco.um("SELECT * FROM mesas WHERE id = ?", (mesa_id,))

        venda_id = mesa["venda_id"]

        if not venda_id:
            # Abre uma venda para esta mesa
            venda_ctrl = VendaController()
            venda_id = venda_ctrl.iniciar_venda()
            self.banco.executar("UPDATE mesas SET venda_id = ? WHERE id = ?", (venda_id, mesa["id"]))

        # Agora adiciona o item na Venda
        venda_ctrl = VendaController()
        sucesso = venda_ctrl.adicionar_item(venda_id, produto_id, quantidade, preco_unitario)

        if not sucesso:
            raise ErroNegocio("Falha ao adicionar item à mesa (Verifique estoque e preço).")

    def transferir_mesa(self, mesa_origem: int, mesa_destino: int):
        """Transfere todos os itens e a venda de uma mesa para outra (F10 do manual)."""
        origem = self.banco.um("SELECT * FROM mesas WHERE numero = ? AND status = 'aberta'", (mesa_origem,))
        if not origem:
            raise ErroNegocio(f"A mesa {mesa_origem} não está aberta.")

        destino = self.banco.um("SELECT * FROM mesas WHERE numero = ?", (mesa_destino,))

        with self.banco.transacao():
            if destino and destino["status"] == "aberta":
                raise ErroNegocio(f"A mesa destino {mesa_destino} já está ocupada. Faça transferência de itens se desejar mesclar.")

            if destino:
                # Transfere para a destino existente mas fechada
                self.banco.executar("UPDATE mesas SET status = 'aberta', venda_id = ?, garcom_id = ? WHERE id = ?",
                                    (origem["venda_id"], origem["garcom_id"], destino["id"]))
            else:
                # Cria a mesa destino
                self.banco.inserir("mesas", {
                    "numero": mesa_destino,
                    "status": "aberta",
                    "venda_id": origem["venda_id"],
                    "garcom_id": origem["garcom_id"]
                })

            # Libera a mesa origem
            self.banco.executar("UPDATE mesas SET status = 'fechada', venda_id = NULL WHERE id = ?", (origem["id"],))

    def fechar_mesa(self, numero_mesa: int, total_final_cent: int, forma_pagamento: str):
        """Fecha a mesa, registrando a venda (F5 do manual)."""
        from src.controllers.venda_controller import VendaController

        mesa = self.banco.um("SELECT * FROM mesas WHERE numero = ? AND status = 'aberta'", (numero_mesa,))
        if not mesa:
            raise ErroNegocio("Mesa não encontrada ou já está fechada.")

        venda_id = mesa["venda_id"]
        venda_ctrl = VendaController()

        sucesso = venda_ctrl.finalizar_venda(venda_id, total_final_cent / 100.0, forma_pagamento)

        if sucesso:
            with self.banco.transacao():
                self.banco.executar("UPDATE mesas SET status = 'fechada', venda_id = NULL WHERE id = ?", (mesa["id"],))
        else:
            raise ErroNegocio("Erro ao finalizar a venda da mesa.")
