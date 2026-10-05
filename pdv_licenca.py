"""Cliente de licenciamento do PDV: valida a licença no servidor e guarda o último token assinado.

O PDV só carrega a chave PÚBLICA (Ed25519). Quem emite o token é o servidor; ler este código não permite emitir licença.

    POST {server}/validar  {"license_key": "...", "machine_id": "..."}
      200 {"status": "ok" | "atraso", "payload": "<json em string>", "signature": "<base64 Ed25519>"}
      403 {"status": "bloqueada" | "invalida" | "outra_maquina"}

O token vale 7 dias. Sem internet (ou com o servidor fora do ar) o último token salvo continua valendo até vencer.
A assinatura é conferida sobre os bytes UTF-8 da string `payload`, exatamente como o servidor a enviou.
Nada aqui registra em log a license_key nem o token.

Esta é a camada de criptografia e rede. As regras de uso (thread, bloqueio, venda em andamento) ficam em
src/core/servico_licenca.py.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

VALIDADE_TOKEN_DIAS = 7
TOLERANCIA_RELOGIO = timedelta(minutes=10)    # relógio ligeiramente atrás do último visto não conta como adulteração
SALTO_MAXIMO = timedelta(days=3)              # a "maior data vista" avança no máximo isto por consulta: data errada no futuro não trava a loja
ARQUIVO_TOKEN = "licenca.json"
MOTIVOS_403 = ("bloqueada", "invalida", "outra_maquina")
AVISO_ATRASO = "Mensalidade em atraso. Regularize o pagamento para evitar o bloqueio do sistema."


@dataclass(frozen=True)
class Resultado:
    permitido: bool
    motivo: str                       # ok | atraso | bloqueada | invalida | outra_maquina | sem_token_valido
    aviso: str = ""                   # só com permitido=True e mensalidade em atraso
    expira_em: datetime | None = None
    offline: bool = False             # True: veio do token salvo, o servidor não foi consultado


# ------------------------------------------------------------------ máquina e pasta
def machine_id() -> str:
    """Identificador estável do computador (hash do MachineGuid do Windows; o valor bruto nunca sai daqui)."""
    bruto = ""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                                0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as chave:
                bruto = str(winreg.QueryValueEx(chave, "MachineGuid")[0])
        except OSError:
            bruto = ""
    if not bruto:
        no = uuid.getnode()
        # Sem MAC o Python devolve um número ALEATÓRIO (bit 40 ligado) a cada execução: o id mudaria sempre. Nesse caso
        # sorteia um uma única vez e guarda na pasta de dados.
        bruto = f"mac-{no:012x}" if not (no >> 40) & 1 else _id_sorteado()
    return hashlib.sha256(f"pdv-machine|{bruto}".encode("utf-8")).hexdigest()[:32]


def _id_sorteado() -> str:
    arquivo = pasta_dados() / "machine_id.txt"
    try:
        valor = arquivo.read_text(encoding="ascii").strip()
        if valor:
            return valor
    except OSError:
        pass
    valor = f"rnd-{uuid.uuid4().hex}"
    try:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(valor, encoding="ascii")
    except OSError:
        pass
    return valor


def pasta_dados() -> Path:
    """Pasta de dados do usuário (fora da pasta do programa): %LOCALAPPDATA%\\WILL-PDV, a mesma do banco do executável."""
    if os.environ.get("PDV_LICENCA_DIR"):
        return Path(os.environ["PDV_LICENCA_DIR"])
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "WILL-PDV"
    return Path.home() / ".local" / "share" / "WILL-PDV"


def caminho_token(pasta: Path | str | None = None) -> Path:
    return Path(pasta) / ARQUIVO_TOKEN if pasta else pasta_dados() / ARQUIVO_TOKEN


# ------------------------------------------------------------------ assinatura
def _b64(texto: str) -> bytes:
    """Base64 comum ou URL-safe, com ou sem preenchimento e com quebras de linha."""
    limpo = "".join(texto.split())
    limpo += "=" * (-len(limpo) % 4)
    try:
        return base64.b64decode(limpo, validate=True)
    except ValueError:
        return base64.urlsafe_b64decode(limpo)


def verificar_assinatura(public_key_pem: str, payload: str, assinatura_b64: str) -> bool:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except ImportError:
        return False
    try:
        chave = load_pem_public_key(public_key_pem.encode("utf-8"))
        if not isinstance(chave, Ed25519PublicKey):
            return False
        chave.verify(_b64(assinatura_b64), payload.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def _data(valor) -> datetime | None:
    """Aceita epoch (segundos) ou ISO 8601; devolve datetime UTC."""
    try:
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return datetime.fromtimestamp(valor, timezone.utc)
        if isinstance(valor, str) and valor.strip():
            d = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass
    return None


def _validade(dados: dict, recebido_em: datetime | None) -> datetime | None:
    """Vencimento do token: o campo do payload, ou emissão + 7 dias, ou (sem nada disso) recebimento + 7 dias."""
    for campo in ("exp", "expira_em", "expires_at", "valido_ate"):
        d = _data(dados.get(campo))
        if d:
            return d
    for campo in ("iat", "emitido_em", "issued_at"):
        d = _data(dados.get(campo))
        if d:
            return d + timedelta(days=VALIDADE_TOKEN_DIAS)
    return recebido_em + timedelta(days=VALIDADE_TOKEN_DIAS) if recebido_em else None


def interpretar_token(token: dict, license_key: str, mid: str, public_key_pem: str, agora: datetime) -> Resultado | None:
    """Confere assinatura, máquina, licença e validade de um token. None se não serve (adulterado, de outra máquina,
    vencido ou ilegível)."""
    try:
        payload, assinatura = token["payload"], token["signature"]
        if not (isinstance(payload, str) and isinstance(assinatura, str)):
            return None
        if not verificar_assinatura(public_key_pem, payload, assinatura):
            return None
        dados = json.loads(payload)
        if not isinstance(dados, dict):
            return None
        if dados.get("machine_id", mid) != mid or dados.get("license_key", license_key) != license_key:
            return None
        status = token.get("status")
        if status not in ("ok", "atraso"):
            return None
        validade = _validade(dados, _data(token.get("recebido_em")))
        if validade is None or agora >= validade:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    if status == "atraso":
        return Resultado(True, "atraso", AVISO_ATRASO, validade)
    return Resultado(True, "ok", "", validade)


# ------------------------------------------------------------------ token salvo
def carregar_token(pasta: Path | str | None = None) -> dict | None:
    try:
        dados = json.loads(caminho_token(pasta).read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else None
    except (OSError, ValueError):
        return None


def salvar_token(token: dict, pasta: Path | str | None = None) -> None:
    destino = caminho_token(pasta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(token, separators=(",", ":")), encoding="utf-8")
    os.replace(temporario, destino)               # troca atômica: queda de energia não deixa o arquivo pela metade


def apagar_token(pasta: Path | str | None = None) -> None:
    try:
        caminho_token(pasta).unlink()
    except OSError:
        pass


# ------------------------------------------------------------------ rede
def _url_segura(url: str) -> bool:
    """A license_key viaja no corpo do POST: só https (http apenas para testes locais)."""
    p = urlparse(url)
    return bool(p.hostname) and (p.scheme == "https" or (p.scheme == "http" and p.hostname in ("localhost", "127.0.0.1")))


def _post_json(url: str, corpo: dict, timeout: float) -> tuple[int, dict]:
    pedido = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"), method="POST",
                                    headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:                # 403 e demais: o servidor respondeu
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def _avancar_visto(visto: datetime | None, agora: datetime) -> datetime:
    return agora if visto is None else max(visto, min(agora, visto + SALTO_MAXIMO))


def checar_licenca(server: str, license_key: str, public_key_pem: str, pasta: Path | str | None = None, *,
                   http=None, agora: datetime | None = None, mid: str | None = None, timeout: float = 8) -> Resultado:
    """Consulta o servidor e, se não houver resposta, usa o último token salvo. Bloqueia (rede, disco): chame sempre
    fora da thread da tela. `http(url, corpo, timeout) -> (status, dict)` pode ser trocado nos testes."""
    agora = agora or datetime.now(timezone.utc)
    mid = mid or machine_id()
    license_key = (license_key or "").strip()
    server = (server or "").strip().rstrip("/")
    if not license_key:
        return Resultado(False, "sem_chave")
    if not _url_segura(server):
        return Resultado(False, "sem_token_valido")
    salvo = carregar_token(pasta) or {}
    visto = _data(salvo.get("visto_em"))
    try:
        status, resposta = (http or _post_json)(f"{server}/validar", {"license_key": license_key, "machine_id": mid}, timeout)
    except (OSError, ValueError):
        status, resposta = 0, {}
    motivo = resposta.get("status") if isinstance(resposta, dict) else None
    if status == 403 and motivo in MOTIVOS_403:           # só um 403 do NOSSO servidor vale; portal cativo/proxy não bloqueia
        apagar_token(pasta)                               # bloqueada/inválida/outra máquina: o token antigo não vale mais
        return Resultado(False, motivo)
    if status == 200 and isinstance(resposta, dict):
        novo = {"status": resposta.get("status"), "payload": resposta.get("payload"),
                "signature": resposta.get("signature"), "recebido_em": agora.isoformat(), "visto_em": agora.isoformat()}
        resultado = interpretar_token(novo, license_key, mid, public_key_pem, agora)
        if resultado:
            try:
                salvar_token(novo, pasta)                 # falha ao gravar (disco/permissão) não pode bloquear quem está em dia
            except OSError:
                pass
            return resultado
        # 200 com assinatura que não confere (servidor falso, proxy): não troca nem apaga o token bom que já existe.
    return _pelo_token_salvo(salvo, license_key, mid, public_key_pem, agora, visto, pasta)


def _pelo_token_salvo(salvo: dict, license_key: str, mid: str, public_key_pem: str, agora: datetime,
                      visto: datetime | None, pasta) -> Resultado:
    if not salvo:
        return Resultado(False, "sem_token_valido")
    efetivo = visto if visto and agora < visto - TOLERANCIA_RELOGIO else agora   # relógio voltado não estende o token
    try:                                              # guarda a maior data vista mesmo com o token vencido
        salvo["visto_em"] = _avancar_visto(visto, agora).isoformat()
        salvar_token(salvo, pasta)
    except OSError:
        pass
    resultado = interpretar_token(salvo, license_key, mid, public_key_pem, efetivo)
    if resultado is None:
        return Resultado(False, "sem_token_valido")
    return Resultado(True, resultado.motivo, resultado.aviso, resultado.expira_em, offline=True)
