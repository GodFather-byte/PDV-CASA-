"""Interfaces dos equipamentos do caixa: balança (F2) e gaveta de dinheiro (F11).

IMPORTANTE: os protocolos reais (Toledo, Filizola, pulso ESC/POS na gaveta) dependem do
equipamento ligado e de biblioteca serial, e não puderam ser testados aqui. Estas classes
definem o contrato que o caixa usa e falham com mensagem clara; o caixa então cai no
modo manual (digitar o peso; abrir a gaveta com a chave). Para suportar um modelo,
implemente `ler_peso`/`abrir` aqui sem mexer no restante do sistema.
"""
from __future__ import annotations


class DispositivoIndisponivel(Exception):
    """O equipamento não está configurado ou o driver não está implementado."""


class Balanca:
    def __init__(self, modelo: str = "Nenhuma", porta: str | None = None):
        self.modelo = modelo or "Nenhuma"
        self.porta = porta

    @property
    def configurada(self) -> bool:
        return self.modelo != "Nenhuma"

    def ler_peso(self) -> float:
        """Peso em kg. Levanta DispositivoIndisponivel se não for possível ler."""
        if not self.configurada:
            raise DispositivoIndisponivel("Nenhuma balança configurada (Configurações > Máquinas).")
        raise DispositivoIndisponivel(
            f"A leitura automática da balança {self.modelo} ainda não está implementada. Digite o peso.")


class Gaveta:
    def __init__(self, instalada: bool = False):
        self.instalada = instalada

    def abrir(self) -> None:
        if not self.instalada:
            raise DispositivoIndisponivel("Nenhuma gaveta configurada (Configurações > Máquinas).")
        raise DispositivoIndisponivel("O acionamento automático da gaveta ainda não está implementado. Abra com a chave.")
