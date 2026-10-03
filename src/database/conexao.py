"""Conexão SQLite do PDV: cria o esquema, migra bancos legados e oferece
transações aninhadas e atalhos de consulta."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.core import formatacao as fmt
from src.database import esquema, sementes

RAIZ = Path(__file__).resolve().parents[2]


def caminho_padrao() -> str:
    """Banco na raiz do projeto (fora da pasta de código), ou o caminho em PDV_DB."""
    return os.environ.get("PDV_DB") or str(RAIZ / "loja_offline.db")


class BancoDados:
    def __init__(self, caminho: str | None = None, semear: bool = True):
        self.caminho = str(caminho or caminho_padrao())
        self._profundidade = 0
        self.conexao = self._abrir()
        try:
            if self._banco_legado():
                self._guardar_legado()
                self.conexao.close()
                for sufixo in ("", "-wal", "-shm"):
                    try:
                        os.remove(self.caminho + sufixo)
                    except FileNotFoundError:
                        pass
                self.conexao = self._abrir()
            self._criar_esquema()
            if semear:
                sementes.aplicar(self)
        except Exception:
            self.conexao.close()
            raise

    # ------------------------------------------------------------- abertura
    def _abrir(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.caminho, isolation_level=None, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        if self.caminho != ":memory:":
            con.execute("PRAGMA journal_mode = WAL")
        return con

    def _banco_legado(self) -> bool:
        """Protótipo antigo (produtos sem coluna 'codigo'), sem versão de esquema."""
        if self.conexao.execute("PRAGMA user_version").fetchone()[0] != 0:
            return False
        tem = self.conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='produtos'").fetchone()
        if not tem:
            return False
        colunas = [r[1] for r in self.conexao.execute("PRAGMA table_info(produtos)")]
        return "codigo" not in colunas

    def _guardar_legado(self) -> None:
        if self.caminho == ":memory:":
            return
        destino = f"{self.caminho}.legado-{fmt.agora().replace(':', '').replace(' ', '-')}.bak"
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        copia = sqlite3.connect(destino)
        try:
            self.conexao.backup(copia)
        finally:
            copia.close()

    def _criar_esquema(self) -> None:
        for comando in esquema.TABELAS:
            self.conexao.execute(comando)
        self.conexao.execute(f"PRAGMA user_version = {esquema.VERSAO_ESQUEMA}")

    # ------------------------------------------------------------ transações
    @contextmanager
    def transacao(self):
        """BEGIN na primeira camada; SAVEPOINT nas aninhadas. Reverte tudo se houver exceção."""
        nome = f"sp{self._profundidade}"
        if self._profundidade == 0:
            self.conexao.execute("BEGIN IMMEDIATE")
        else:
            self.conexao.execute(f"SAVEPOINT {nome}")
        self._profundidade += 1
        try:
            yield self
        except BaseException:
            self._profundidade -= 1
            if self._profundidade == 0:
                self.conexao.execute("ROLLBACK")
            else:
                self.conexao.execute(f"ROLLBACK TO {nome}")
                self.conexao.execute(f"RELEASE {nome}")
            raise
        else:
            self._profundidade -= 1
            if self._profundidade == 0:
                self.conexao.execute("COMMIT")
            else:
                self.conexao.execute(f"RELEASE {nome}")

    # ------------------------------------------------------------- consultas
    def executar(self, sql: str, params=()) -> sqlite3.Cursor:
        return self.conexao.execute(sql, params)

    def um(self, sql: str, params=()):
        return self.conexao.execute(sql, params).fetchone()

    def todos(self, sql: str, params=()) -> list[sqlite3.Row]:
        return self.conexao.execute(sql, params).fetchall()

    def valor(self, sql: str, params=(), padrao=None):
        linha = self.conexao.execute(sql, params).fetchone()
        return linha[0] if linha is not None and linha[0] is not None else padrao

    def inserir(self, tabela: str, dados: dict) -> int:
        colunas = ", ".join(dados)
        marcas = ", ".join("?" for _ in dados)
        cur = self.conexao.execute(f"INSERT INTO {tabela} ({colunas}) VALUES ({marcas})", tuple(dados.values()))
        return cur.lastrowid

    def atualizar(self, tabela: str, id_: int, dados: dict) -> None:
        if not dados:
            return
        sets = ", ".join(f"{c} = ?" for c in dados)
        self.conexao.execute(f"UPDATE {tabela} SET {sets} WHERE id = ?", (*dados.values(), id_))

    # ------------------------------------------------------- config e auditoria
    def cfg(self, chave: str, padrao: str = "") -> str:
        v = self.valor("SELECT valor FROM config WHERE chave = ?", (chave,))
        return padrao if v is None else v

    def cfg_bool(self, chave: str, padrao: bool = False) -> bool:
        return self.cfg(chave, "S" if padrao else "N").strip().upper() in ("S", "1", "SIM", "TRUE")

    def cfg_int(self, chave: str, padrao: int = 0) -> int:
        try:
            return int(float(self.cfg(chave, str(padrao)) or padrao))
        except ValueError:
            return padrao

    def cfg_set(self, chave: str, valor) -> None:
        self.executar("INSERT OR REPLACE INTO config(chave, valor) VALUES (?, ?)", (chave, str(valor)))

    def log(self, evento: str, detalhe: str = "", operador_id: int | None = None) -> None:
        self.executar("INSERT INTO log_eventos(quando, operador_id, evento, detalhe) VALUES (?,?,?,?)",
                      (fmt.agora(), operador_id, evento, detalhe))

    # --------------------------------------------------------------- backup
    def copiar_para(self, destino: str) -> None:
        """Cópia consistente do banco inteiro (API de backup do SQLite)."""
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        copia = sqlite3.connect(destino)
        try:
            self.conexao.backup(copia)
        finally:
            copia.close()

    def fechar(self) -> None:
        try:
            self.conexao.close()
        except sqlite3.Error:
            pass


if __name__ == "__main__":
    banco = BancoDados()
    print(f"Banco criado/conectado com sucesso em {banco.caminho}")
    banco.fechar()
