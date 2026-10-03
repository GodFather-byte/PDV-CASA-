import json
import base64
import hmac
import hashlib
from datetime import datetime

SECRET_KEY = b"SEGREDO_SUPER_FORTE_PDV_CASA_2026"

class LicencaExpirada(Exception):
    pass

class LicencaInvalida(Exception):
    pass

def gerar_licenca(chave_loja: str, dias_validade: int) -> str:
    """Gera uma chave de licença no formato Base64. Usado apenas no Backend/Admin."""
    # Calcula data de vencimento
    vencimento = datetime.now().timestamp() + (dias_validade * 86400)
    
    payload = {
        "loja": chave_loja,
        "expira_em": int(vencimento)
    }
    
    payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode('utf-8')
    
    # Assinatura HMAC
    assinatura = hmac.new(SECRET_KEY, payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
    
    return f"{payload_b64}.{assinatura}"

def validar_e_salvar_licenca(banco, token: str) -> dict:
    """Valida o token digitado pelo cliente e salva a validade no banco local."""
    try:
        payload_b64, assinatura = token.split('.')
    except ValueError:
        raise LicencaInvalida("Formato de licença inválido.")
        
    # Verifica assinatura
    assinatura_esperada = hmac.new(SECRET_KEY, payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
    if assinatura != assinatura_esperada:
        raise LicencaInvalida("Assinatura da licença não confere. Chave falsa!")
        
    try:
        payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
    except Exception:
        raise LicencaInvalida("Falha ao ler os dados da licença.")
        
    # Verifica se a loja bate
    chave_loja_local = banco.cfg("chave_loja")
    if chave_loja_local and payload["loja"] != chave_loja_local:
        raise LicencaInvalida("Esta licença pertence a outra loja.")
        
    # Verifica validade
    agora = int(datetime.now().timestamp())
    if agora > payload["expira_em"]:
        raise LicencaExpirada("Esta licença já passou do prazo de validade.")
        
    # Salva no banco offline
    data_formatada = datetime.fromtimestamp(payload["expira_em"]).strftime("%Y-%m-%d %H:%M:%S")
    with banco.transacao():
        banco.executar("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('licenca_expira_em', ?)", (data_formatada,))
        banco.executar("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('licenca_token', ?)", (token,))
        
    return payload

def verificar_bloqueio(banco):
    """Verifica se o sistema deve ser bloqueado hoje."""
    vencimento_str = banco.cfg("licenca_expira_em")
    
    if not vencimento_str:
        raise LicencaExpirada("Nenhuma licença foi ativada neste caixa.")
        
    vencimento = datetime.strptime(vencimento_str, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > vencimento:
        raise LicencaExpirada(f"Sua licença expirou em {vencimento.strftime('%d/%m/%Y')}. Por favor, renove sua mensalidade.")
