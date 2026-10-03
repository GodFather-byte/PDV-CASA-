"""Login e níveis de acesso (manual ADM: seções 1 e 8.01).

Cinco níveis: 0 (somente caixa) até 4 (tudo). Cada módulo tem um nível mínimo
configurável; níveis maiores herdam o acesso dos menores.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.core import seguranca
from src.core.erros import ErroNegocio, ErroPermissao

GRUPOS_MENU = ["Cadastros", "Caixa", "Lançamentos", "Relatórios", "Utilitários", "Configurações"]


@dataclass(frozen=True)
class Operador:
    id: int
    nome: str
    nivel: int
    garcom: bool = False
    entregador: bool = False
    vendedor: bool = False

    @property
    def so_caixa(self) -> bool:
        return self.nivel == 0


class AcessoController:
    def __init__(self, banco):
        self.banco = banco

    # --------------------------------------------------------------- login
    def nomes_login(self) -> list[str]:
        return [r[0] for r in self.banco.todos("SELECT nome FROM operadores WHERE ativo = 1 ORDER BY nome")]

    def autenticar(self, nome: str, senha: str) -> Operador:
        linha = self.banco.um("SELECT * FROM operadores WHERE nome = ? AND ativo = 1", ((nome or "").strip(),))
        if linha is None:
            raise ErroNegocio("Usuário não encontrado.")
        if not seguranca.conferir(senha, linha["senha"]):
            self.banco.log("login_falhou", linha["nome"], linha["id"])
            raise ErroNegocio("Senha Incorreta")
        return self._operador(linha)

    @staticmethod
    def _operador(l) -> Operador:
        return Operador(l["id"], l["nome"], l["nivel"], bool(l["garcom"]), bool(l["entregador"]), bool(l["vendedor"]))

    def operador(self, operador_id: int) -> Operador:
        return self._operador(self.banco.um("SELECT * FROM operadores WHERE id = ?", (operador_id,)))

    # ------------------------------------------------------------ permissões
    def nivel_modulo(self, modulo: str) -> int:
        n = self.banco.valor("SELECT nivel FROM acessos WHERE modulo = ?", (modulo,))
        if n is None:
            raise KeyError(f"módulo desconhecido: {modulo}")
        return n

    def pode(self, operador: Operador, modulo: str) -> bool:
        return operador.nivel >= self.nivel_modulo(modulo) and operador.nivel > 0

    def exigir(self, operador: Operador, modulo: str) -> None:
        if not self.pode(operador, modulo):
            descricao = self.banco.valor("SELECT descricao FROM acessos WHERE modulo = ?", (modulo,))
            raise ErroPermissao(f"Seu nível de acesso não permite: {descricao}.")

    def modulos(self, grupo: str | None = None) -> list[dict]:
        sql = "SELECT modulo, descricao, grupo, nivel FROM acessos"
        params = ()
        if grupo:
            sql += " WHERE grupo = ?"
            params = (grupo,)
        return [dict(r) for r in self.banco.todos(sql + " ORDER BY rowid", params)]

    def modulos_permitidos(self, operador: Operador, grupo: str) -> list[dict]:
        return [m for m in self.modulos(grupo) if operador.nivel >= m["nivel"] and operador.nivel > 0]

    def grupos_visiveis(self, operador: Operador) -> list[str]:
        """Botões do menu principal que o operador pode ver (o Caixa é de todos)."""
        visiveis = []
        for g in GRUPOS_MENU:
            if g == "Caixa" or self.modulos_permitidos(operador, g):
                visiveis.append(g)
        return visiveis

    def alterar_nivel_modulo(self, modulo: str, nivel: int) -> None:
        if not 1 <= nivel <= 4:
            raise ErroNegocio("O nível do módulo deve ser de 1 a 4 (o nível 0 já é o do caixa).")
        self.nivel_modulo(modulo)
        self.banco.executar("UPDATE acessos SET nivel = ? WHERE modulo = ?", (nivel, modulo))

    # ------------------------------------------------------------ supervisor
    def precisa_senha(self, operador: Operador, modulo: str, chave_config: str) -> bool:
        """True se a operação está configurada para exigir senha e o operador não tem nível."""
        if not self.banco.cfg_bool(chave_config, True):
            return False
        return operador.nivel < self.nivel_modulo(modulo)  # nível 0 sempre fica abaixo de qualquer módulo

    def validar_supervisor(self, senha: str, modulo: str) -> Operador | None:
        """Procura um operador ativo com nível suficiente cuja senha confere (janela
        'Digite uma Senha Válida' do caixa)."""
        minimo = max(self.nivel_modulo(modulo), 1)
        for l in self.banco.todos("SELECT * FROM operadores WHERE ativo = 1 AND nivel >= ?", (minimo,)):
            if seguranca.conferir(senha, l["senha"]):
                self.banco.log("senha_supervisor", f"{modulo} autorizado por {l['nome']}", l["id"])
                return self._operador(l)
        self.banco.log("senha_supervisor_negada", modulo)
        return None
