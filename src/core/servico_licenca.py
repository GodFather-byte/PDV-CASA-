"""Serviço único de licenciamento do PDV: configuração, verificação em thread e regras de bloqueio.

Toda a decisão fica aqui (a tela só mostra o que este módulo manda), no cliente pdv_licenca.py (raiz do projeto).

REGRA CRÍTICA: o bloqueio nunca interrompe uma venda ou comanda em andamento. `bloqueio_pendente` só vira True quando
não há venda aberta; enquanto houver, o bloqueio espera (ou vale na próxima abertura do programa).

Sem SERVER e PUBLIC_KEY_PEM preenchidos abaixo o serviço fica desligado e o PDV funciona como antes.
"""
from __future__ import annotations

import threading

import pdv_licenca

# ------------------------------------------------------------------ PREENCHER (valores do fornecedor)
SERVER = "https://COLE-AQUI-O-ENDERECO-DO-SERVIDOR"
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
COLE-AQUI-A-CHAVE-PUBLICA-ED25519
-----END PUBLIC KEY-----"""
SUPORTE_PADRAO = "Fale com o suporte do fornecedor."      # também em Configurações: lic_suporte
# ---------------------------------------------------------------------------------------------------

CHAVE_LICENCA = "lic_chave"          # chaves da tabela config
CHAVE_SERVIDOR = "lic_servidor"      # opcional: sobrescreve SERVER (ex.: servidor de testes)
CHAVE_SUPORTE = "lic_suporte"
INTERVALO_SEGUNDOS = 4 * 3600
_PLACEHOLDER = "COLE-AQUI"

MENSAGENS = {
    "sem_chave": "Este caixa ainda não tem chave de licença. Informe a chave fornecida pelo suporte.",
    "bloqueada": "Esta licença está bloqueada.",
    "invalida": "A chave de licença informada não é válida.",
    "outra_maquina": "Esta licença está em uso em outro computador.",
    "sem_token_valido": "Não foi possível confirmar a licença e não há uma validação recente salva neste computador. "
                        "Verifique a internet e tente novamente.",
}

SQL_VENDA_EM_ANDAMENTO = "SELECT 1 FROM vendas WHERE status IN ('aberta','conta_enviada') LIMIT 1"


def mascarar(chave: str) -> str:
    """Só os 4 últimos caracteres aparecem."""
    chave = (chave or "").strip()
    return "—" if not chave else "•" * 8 + chave[-4:]


class ServicoLicenca:
    def __init__(self, banco, checar=None, extra_em_andamento=None, servidor: str | None = None,
                 chave_publica: str | None = None, pasta=None):
        self.banco = banco
        self._checar = checar or pdv_licenca.checar_licenca
        self._extra_em_andamento = extra_em_andamento      # ex.: janela do caixa aberta (a tela informa)
        self._servidor = servidor
        self._chave_publica = chave_publica if chave_publica is not None else PUBLIC_KEY_PEM
        self._pasta = pasta
        self.resultado: pdv_licenca.Resultado | None = None
        self._thread: threading.Thread | None = None
        self._saida: list = []

    # ------------------------------------------------------------ configuração
    @property
    def servidor(self) -> str:
        return (self._servidor or self.banco.cfg(CHAVE_SERVIDOR).strip() or SERVER).strip()

    @property
    def ativo(self) -> bool:
        """Só liga depois que o fornecedor preencheu o servidor e a chave pública."""
        return _PLACEHOLDER not in self.servidor and _PLACEHOLDER not in self._chave_publica

    def chave(self) -> str:
        return self.banco.cfg(CHAVE_LICENCA).strip()

    def salvar_chave(self, chave: str) -> None:
        chave = "".join((chave or "").split())
        if not chave:
            raise ValueError("Informe a chave de licença.")
        self.banco.cfg_set(CHAVE_LICENCA, chave)
        self.resultado = None

    def chave_mascarada(self) -> str:
        return mascarar(self.chave())

    def tem_permanente(self) -> bool:
        return pdv_licenca.permanente_valida(self._chave_publica, self._pasta) is not None

    def ativar_permanente(self, codigo: str) -> None:
        """Ativa o código de licença permanente (emitido pelo dono). Levanta pdv_licenca.CodigoInvalido se não servir."""
        pdv_licenca.ativar_permanente(codigo, self._chave_publica, self._pasta)
        self.resultado = pdv_licenca.Resultado(True, "permanente")

    def contato_suporte(self) -> str:
        return self.banco.cfg(CHAVE_SUPORTE).strip() or SUPORTE_PADRAO

    def machine_id(self) -> str:
        return pdv_licenca.machine_id()

    # ------------------------------------------------------------ verificação (rede só na thread)
    @property
    def verificando(self) -> bool:
        return self._thread is not None

    def iniciar_verificacao(self) -> bool:
        """Dispara a consulta numa thread e volta na hora. O banco só é lido aqui, na thread da tela: a thread recebe
        tudo pronto e entrega o resultado em `coletar`. False se desligado ou se já há uma consulta em curso."""
        if not self.ativo or self._thread is not None:
            return False
        servidor, chave, publica, pasta = self.servidor, self.chave(), self._chave_publica, self._pasta
        saida = self._saida = []

        def rede():
            try:
                saida.append(self._checar(servidor, chave, publica, pasta))
            except Exception:                            # nunca derruba a thread nem vaza detalhe: vira "sem validação"
                saida.append(pdv_licenca.Resultado(False, "sem_token_valido"))
        self._thread = threading.Thread(target=rede, name="licenca", daemon=True)
        self._thread.start()
        return True

    def coletar(self) -> bool:
        """Chamar da thread da tela. True quando uma consulta terminou agora e `resultado` foi atualizado."""
        if self._thread is None or self._thread.is_alive() or not self._saida:
            return False
        self._thread = None
        self.resultado = self._saida[0]
        return True

    # ------------------------------------------------------------ regras
    def venda_em_andamento(self) -> bool:
        if self.banco.valor(SQL_VENDA_EM_ANDAMENTO):
            return True
        return bool(self._extra_em_andamento and self._extra_em_andamento())

    @property
    def bloqueado(self) -> bool:
        return self.ativo and self.resultado is not None and not self.resultado.permitido

    @property
    def bloqueio_pendente(self) -> bool:
        """Bloqueado E sem nada em andamento: é a hora de mostrar a tela de bloqueio."""
        return self.bloqueado and not self.venda_em_andamento()

    @property
    def aviso(self) -> str:
        r = self.resultado
        return r.aviso if self.ativo and r and r.permitido else ""

    def mensagem_bloqueio(self) -> str:
        r = self.resultado
        return MENSAGENS.get(r.motivo, MENSAGENS["sem_token_valido"]) if r else ""

    def status_texto(self) -> str:
        if not self.ativo:
            return "Licenciamento não configurado neste caixa."
        r = self.resultado
        if r is None:
            return "Verificando..." if self.verificando else "Ainda não verificada nesta sessão."
        if not r.permitido:
            return "Bloqueada — " + self.mensagem_bloqueio()
        if r.motivo == "permanente":
            return "Ativa — licença permanente"
        base = "Ativa (mensalidade em atraso)" if r.motivo == "atraso" else "Ativa"
        if r.offline:
            base += ", validada offline (sem internet)"
        if r.expira_em:
            base += f". Validação vale até {r.expira_em.astimezone().strftime('%d/%m/%Y %H:%M')}"
        return base
