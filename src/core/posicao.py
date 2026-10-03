"""Posições de consumo: mesa ("2") ou comanda ("C2").

Uma comanda é uma venda de modalidade 'mesa' com comanda = 1: aparece junto das mesas, tem serviço,
pré-conta e transferência iguais, mas a numeração é própria (a comanda 2 e a mesa 2 coexistem).
"""
from __future__ import annotations

import re

_PADRAO = re.compile(r"^\s*([cC])?\s*(\d{1,4})\s*$")


def interpretar(texto) -> tuple[bool, int]:
    """'2' -> (False, 2) mesa; 'C2', 'c2' ou 'c 2' -> (True, 2) comanda.

    Levanta ValueError se não for um número de mesa ou de comanda. O 0 é aceito como mesa (a tela usa 0 para balcão)."""
    m = _PADRAO.match("" if texto is None else str(texto))
    if m is None:
        raise ValueError("Digite o número da mesa ou C e o número da comanda (ex.: 5 ou C2).")
    comanda, numero = bool(m.group(1)), int(m.group(2))
    if comanda and numero == 0:
        raise ValueError("A comanda 0 não existe: use de 1 em diante (ex.: C2).")
    return comanda, numero


def parece_comanda(texto) -> bool:
    """True para a letra C seguida de número ('C2'): o que o operador digita ou o leitor lê do cartão da comanda."""
    m = _PADRAO.match("" if texto is None else str(texto))
    return bool(m and m.group(1))


def rotulo(comanda, posicao) -> str:
    """Como a posição aparece nas listas: '5' para mesa, 'C2' para comanda."""
    return f"C{posicao}" if comanda else str(posicao)


def nome(comanda, posicao) -> str:
    return f"Comanda {posicao}" if comanda else f"Mesa {posicao}"
