"""Renovação automática da licença pela nuvem: o PDV pede o código da própria loja (GET /v1/licenca, com o token dela)
e o ativa se estender o prazo. O fornecedor só registra até quando a loja pagou (python -m backend.lojas assinatura);
se ela não pagar, a data não avança e a licença vence normalmente no caixa."""
from __future__ import annotations

import logging

from src.core import formatacao as fmt
from src.core import licenca
from src.core.erros import ErroNegocio
from src.sync.atualizacoes import url_atualizacoes

log = logging.getLogger("pdv.licenca")

INTERVALO_HORAS = 6
CHAVE_CONSULTA = "licenca_nuvem_consultada_em"


def url_licenca(api_url: str) -> str:
    return url_atualizacoes(api_url)[: -len("/atualizacoes")] + "/licenca"


def consultar(api_url: str, token: str, http=None, timeout=(3, 10)) -> str | None:
    """Só a rede: o código emitido pela nuvem, ou None (sem nuvem, sem assinatura, sem rede)."""
    if not (api_url or "").strip() or not (token or "").strip():
        return None
    if http is None:
        try:
            import requests as http
        except ImportError:
            return None
    try:
        r = http.get(url_licenca(api_url), headers={"Authorization": f"Bearer {token.strip()}"}, timeout=timeout)
        if r.status_code != 200:
            log.info("A nuvem não emitiu licença (HTTP %s).", r.status_code)
            return None
        codigo = r.json().get("codigo")
    except (OSError, ValueError, AttributeError) as e:
        log.info("Consulta de licença falhou: %s", e)
        return None
    return codigo if isinstance(codigo, str) else None


def aplicar(banco, codigo: str | None) -> bool:
    """Ativa o código se ele estender o prazo atual. Código igual, mais curto ou inválido é ignorado. True se renovou."""
    if not codigo or codigo == banco.cfg("licenca_token").strip():
        return False
    try:
        lic = licenca.ativar(banco, codigo)
    except ErroNegocio as e:                       # mais antiga que a atual, de outra loja, adulterada...
        log.info("Licença da nuvem não aplicada: %s", e)
        return False
    log.info("Licença renovada pela nuvem até %s.", lic["expira_em"].isoformat())
    return True


def renovar(banco, http=None, forcar: bool = False, timeout=(3, 10)) -> bool:
    """Consulta (no máximo a cada 6 horas, salvo `forcar`) e aplica. Só faz algo quando a licença é exigida."""
    if not licenca.exigida(banco):
        return False
    ultima = banco.cfg(CHAVE_CONSULTA)
    if not forcar and ultima and 0 <= fmt.minutos_entre(ultima) < INTERVALO_HORAS * 60:
        return False
    banco.cfg_set(CHAVE_CONSULTA, fmt.agora())
    return aplicar(banco, consultar(banco.cfg("api_url"), banco.cfg("api_token"), http, timeout))
