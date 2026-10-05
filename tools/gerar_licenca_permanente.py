"""Ferramenta DO DONO: emite um código de licença permanente para um caixa. Rode no SEU computador, nunca no do cliente.

    python -m tools.gerar_licenca_permanente --chave-privada licenca_servidor.key --machine-id <ID do caixa> --nome "Boate Estrela"

O `machine_id` aparece no caixa em Utilitários > Licença (botão Copiar) e na tela de bloqueio. O código sai na tela: mande-o
ao cliente, que cola em "Licença permanente...". Ele só vale naquele computador, não expira e funciona sem internet.

A chave privada é a do par que você gerou (README, passo 1). Ela é lida só deste arquivo, nunca é impressa nem enviada, e
esta ferramenta não vai no instalador do PDV. Guarde cada código emitido: não há como revogá-lo sem trocar o par de chaves.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import date
from pathlib import Path

import pdv_licenca

MACHINE_ID = re.compile(r"[0-9a-f]{32}")


def emitir(caminho_chave: str, machine_id: str, nome: str = "") -> str:
    """Código de licença permanente para `machine_id`, assinado com a chave privada de `caminho_chave`."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    machine_id = machine_id.strip().lower()
    if not MACHINE_ID.fullmatch(machine_id):
        raise ValueError("machine_id inválido: são 32 letras/números de 0 a 9 e a a f (copie na tela Licença do caixa).")
    try:
        chave = load_pem_private_key(Path(caminho_chave).read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as e:
        raise ValueError(f"Não consegui ler a chave privada em {caminho_chave}: {e}") from None
    if not isinstance(chave, Ed25519PrivateKey):
        raise ValueError("A chave privada precisa ser Ed25519 (veja o passo 1 do README).")
    payload = json.dumps({"permanente": True, "machine_id": machine_id, "nome": nome.strip(),
                          "emitida_em": date.today().isoformat()}, separators=(",", ":"), sort_keys=True)
    assinatura = base64.b64encode(chave.sign(payload.encode("utf-8"))).decode("ascii")
    return pdv_licenca.montar_codigo_permanente(payload, assinatura)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emite uma licença permanente para um caixa.")
    ap.add_argument("--chave-privada", required=True, help="arquivo .key gerado no passo 1 do README")
    ap.add_argument("--machine-id", required=True, help="ID do computador (tela Licença do caixa)")
    ap.add_argument("--nome", default="", help="identificação da loja, só para o seu controle (vai dentro do código)")
    args = ap.parse_args(argv)
    try:
        codigo = emitir(args.chave_privada, args.machine_id, args.nome)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    print("Código de licença permanente (válido só para esse computador, sem vencimento):\n")
    print(codigo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
