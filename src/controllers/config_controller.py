"""Configurações (manual ADM seção 8): dados da loja, parâmetros operacionais e máquinas.

As listas `CAMPOS_*` descrevem os formulários; a interface os desenha sem código extra."""
from __future__ import annotations

from src.core.erros import ErroNegocio, ErroValidacao

# (chave, rótulo, tipo[texto|int|decimal|sn|escolha], seção, opções)
CAMPOS_LOJA = [
    ("razao_social", "Razão social", "texto"), ("nome_fantasia", "Nome fantasia", "texto"),
    ("slogan", "Slogan (impresso no cupom)", "texto"), ("cnpj", "CNPJ", "texto"), ("ie", "Inscrição estadual", "texto"),
    ("endereco", "Endereço", "texto"), ("complemento", "Complemento", "texto"), ("bairro", "Bairro", "texto"),
    ("cidade", "Cidade", "texto"), ("uf", "UF", "texto"), ("cep", "CEP", "texto"),
    ("telefone", "Telefone", "texto"), ("email", "E-mail", "texto"),
    ("logotipo", "Logotipo (bmp 180x121, 256 cores)", "texto"),
]

CAMPOS_MAQUINA = [
    ("terminal", "Nº do terminal", "int"), ("nome_computador", "Nome do computador", "texto"),
    ("descricao", "Descrição", "texto"),
    ("modo_impressao", "Impressão de cupons e relatórios", "escolha",
     [("tela", "Mostrar na tela"), ("arquivo", "Salvar em arquivo"), ("windows", "Impressora padrão do Windows")]),
    ("colunas_fita", "Colunas da fita (impressora de cupom)", "int"),
    ("impressora_remota_pasta", "Pasta dos pedidos da impressora remota (cozinha/bar)", "texto"),
    ("balanca", "Balança", "escolha", [("Nenhuma", "Nenhuma"), ("Toledo", "Toledo"), ("Filizola", "Filizola")]),
    ("balanca_porta", "Porta da balança (ex.: COM1)", "texto"),
    ("gaveta", "Gaveta de dinheiro", "sn"), ("leitor_optico", "Leitor óptico de código de barras", "sn"),
]

CAMPOS_CONFIG = [
    ("num_mesas", "Número de mesas / posições de consumo", "int", "Mesas e serviço"),
    ("cobra_servico_mesa", "Cobrar serviço nas mesas", "sn", "Mesas e serviço"),
    ("servico_pct", "Percentual de serviço (%)", "decimal", "Mesas e serviço"),
    ("controle_garcom", "Exigir o garçom ao fechar a mesa", "sn", "Mesas e serviço"),
    ("controle_comandas", "Controle de comandas", "sn", "Mesas e serviço"),
    ("comissao_garcom_pct", "Comissão dos garçons sobre produtos (%)", "decimal", "Mesas e serviço"),
    ("tempo_inatividade_min", "Alertar mesa parada após (minutos, 0 = desligado)", "int", "Mesas e serviço"),
    ("pergunta_pessoas", "Perguntar o nº de pessoas ao abrir a mesa", "sn", "Mesas e serviço"),
    ("num_turnos", "Número de turnos por dia", "int", "Caixa"),
    ("exigir_senha_gaveta", "Exigir senha de supervisor para abrir a gaveta", "sn", "Caixa"),
    ("exigir_senha_sangria", "Exigir senha de supervisor para sangria", "sn", "Caixa"),
    ("exigir_senha_cancelamento", "Exigir senha de supervisor para cancelamentos", "sn", "Caixa"),
    ("exigir_senha_desconto", "Exigir senha de supervisor para desconto", "sn", "Caixa"),
    ("imprimir_cupom", "Imprimir cupom ao fechar a venda", "sn", "Caixa"),
    ("taxa_entrega_padrao", "Taxa de entrega padrão (R$)", "texto", "Caixa"),
    ("programa_comunicacao", "Programa de comunicação (caminho do executável)", "texto", "Utilitários"),
    ("pasta_backup", "Pasta do backup (vazio = pasta Backup do sistema)", "texto", "Utilitários"),
    ("email_loja", "E-mail da loja", "texto", "E-mail"), ("email_destino", "E-mail de destino dos relatórios", "texto", "E-mail"),
    ("smtp_servidor", "Servidor de e-mail (provedor)", "texto", "E-mail"),
    ("chave_loja", "Chave da loja (licença)", "texto", "Nuvem"), ("api_url", "Endereço da API de sincronização", "texto", "Nuvem"),
    ("api_token", "Token da API", "texto", "Nuvem"), ("sync_intervalo_seg", "Intervalo da sincronização (segundos)", "int", "Nuvem"),
]
_TIPO_CONFIG = {c[0]: c[2] for c in CAMPOS_CONFIG}


class ConfigController:
    def __init__(self, banco):
        self.banco = banco

    # --------------------------------------------------------------- loja
    def loja(self) -> dict:
        return dict(self.banco.um("SELECT * FROM loja WHERE id = 1"))

    def salvar_loja(self, dados: dict) -> None:
        validos = {c[0] for c in CAMPOS_LOJA}
        limpos = {k: (str(v).strip() if v is not None else None) for k, v in dados.items() if k in validos}
        if limpos.get("uf") and len(limpos["uf"]) != 2:
            raise ErroValidacao("UF deve ter 2 letras.", {"uf": "inválido"})
        self.banco.atualizar("loja", 1, limpos)

    def nome_loja(self) -> str:
        l = self.loja()
        return l["nome_fantasia"] or l["razao_social"] or "PDV"

    # ------------------------------------------------------------- máquina
    def maquina(self, terminal: int | None = None) -> dict:
        terminal = terminal or self.banco.cfg_int("terminal", 1)
        r = self.banco.um("SELECT * FROM maquinas WHERE terminal = ?", (terminal,))
        if r is None:
            self.banco.inserir("maquinas", {"terminal": terminal})
            r = self.banco.um("SELECT * FROM maquinas WHERE terminal = ?", (terminal,))
        return dict(r)

    def salvar_maquina(self, dados: dict, terminal: int | None = None) -> None:
        atual = self.maquina(terminal)
        permitidos = {c[0] for c in CAMPOS_MAQUINA if c[0] != "terminal"}
        limpos = {}
        for k, v in dados.items():
            if k not in permitidos:
                continue
            if k in ("gaveta", "leitor_optico"):
                v = 1 if str(v).strip().upper() in ("S", "1", "SIM", "TRUE") or v is True else 0
            elif k == "colunas_fita":
                v = int(v)
                if not 24 <= v <= 80:
                    raise ErroValidacao("A fita deve ter entre 24 e 80 colunas.", {k: "inválido"})
            limpos[k] = v
        self.banco.atualizar("maquinas", atual["id"], limpos)

    # --------------------------------------------------------------- config
    def todas(self) -> dict:
        return {c[0]: self.banco.cfg(c[0]) for c in CAMPOS_CONFIG}

    def salvar_config(self, valores: dict) -> None:
        with self.banco.transacao():
            for chave, valor in valores.items():
                if chave not in _TIPO_CONFIG:
                    raise ErroNegocio(f"Configuração desconhecida: {chave}")
                tipo = _TIPO_CONFIG[chave]
                v = str(valor).strip()
                if tipo == "sn":
                    v = "S" if v.upper() in ("S", "1", "SIM", "TRUE") else "N"
                elif tipo == "int":
                    try:
                        v = str(int(float(v.replace(",", ".") or 0)))
                    except ValueError:
                        raise ErroValidacao(f"Valor inteiro inválido em '{chave}'.", {chave: "inválido"}) from None
                    if int(v) < 0:
                        raise ErroValidacao(f"'{chave}' não pode ser negativo.", {chave: "inválido"})
                elif tipo == "decimal":
                    try:
                        v = str(float(v.replace(",", ".") or 0))
                    except ValueError:
                        raise ErroValidacao(f"Número inválido em '{chave}'.", {chave: "inválido"}) from None
                    if float(v) < 0 or float(v) > 100:
                        raise ErroValidacao(f"'{chave}' deve estar entre 0 e 100.", {chave: "inválido"})
                if chave == "num_mesas" and not 1 <= int(v) <= 999:
                    raise ErroValidacao("O número de mesas deve ficar entre 1 e 999.", {chave: "inválido"})
                if chave == "num_turnos" and not 1 <= int(v) <= 9:
                    raise ErroValidacao("O número de turnos deve ficar entre 1 e 9.", {chave: "inválido"})
                self.banco.cfg_set(chave, v)
