"""Utilitários (manual ADM seção 7): backup, limpeza do movimento e programa de comunicação."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from src.controllers import notificacoes
from src.core import formatacao as fmt
from src.core import registro
from src.core.erros import ErroNegocio
from src.database import protecao
from src.database.conexao import RAIZ

log = logging.getLogger("pdv.backup")


class UtilitarioController:
    def __init__(self, banco, operador_id: int | None = None):
        self.banco = banco
        self.operador_id = operador_id

    # --------------------------------------------------------------- backup
    def pasta_backup(self) -> Path:
        escolhida = self.banco.cfg("pasta_backup").strip()
        return Path(escolhida) if escolhida else RAIZ / "Backup"

    def pasta_backup_extra(self) -> Path | None:
        """Segunda cópia (pendrive, outro disco ou pasta de rede): protege se o disco do caixa estragar."""
        escolhida = self.banco.cfg("pasta_backup_extra").strip()
        return Path(escolhida) if escolhida else None

    def pastas_backup(self) -> list[Path]:
        return [p for p in (self.pasta_backup(), self.pasta_backup_extra()) if p is not None]

    def backup(self, manter: int = 60) -> str:
        """Cópia consistente do banco com data e hora no nome, conferida logo depois de gravada. Mantém os `manter`
        mais novos. Se houver pasta extra configurada, grava lá também; falha só na extra não cancela o backup."""
        pasta = self.pasta_backup()
        pasta.mkdir(parents=True, exist_ok=True)
        nome = f"loja_offline-{fmt.agora().replace(':', '').replace(' ', '-')}.db"
        destino = pasta / nome
        self.banco.copiar_para(str(destino))
        problema = protecao.verificar_arquivo(destino)
        if problema:                       # nunca deixa uma cópia ruim ocupar o lugar de uma boa
            destino.unlink(missing_ok=True)
            raise ErroNegocio(f"O backup saiu danificado e foi descartado ({problema}). Verifique o disco.")
        self.banco.cfg_set("ultimo_backup", fmt.agora())
        self.banco.log("backup", str(destino), self.operador_id)
        if self.banco.caminho != ":memory:":
            protecao.registrar_pasta(self.banco.caminho, pasta)
        self._podar(pasta, manter)
        extra = self.pasta_backup_extra()
        erro_extra = ""
        if extra is not None:
            try:
                extra.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(destino, extra / nome)
                if self.banco.caminho != ":memory:":
                    protecao.registrar_pasta(self.banco.caminho, extra)
                self._podar(extra, manter)
            except OSError as e:
                erro_extra = f"não foi possível gravar na pasta extra ({e})"
                log.warning("Backup extra falhou: %s", e)
        self.banco.cfg_set("backup_extra_erro", erro_extra)
        return str(destino)

    @staticmethod
    def _podar(pasta: Path, manter: int) -> None:
        for p in sorted(pasta.glob(protecao.PADRAO_BACKUP), key=lambda p: p.name, reverse=True)[manter:]:
            try:
                p.unlink()
            except OSError:
                pass

    def backup_automatico(self, motivo: str, minimo_min: int = 0) -> str | None:
        """Backup sem o operador pedir (troca de turno, saída, início). NUNCA levanta erro: devolve o caminho ou None, e
        guarda o último problema em `backup_erro` para o painel avisar. `minimo_min` evita repetir um backup recente."""
        if minimo_min and (idade := self.idade_backup_horas()) is not None and idade * 60 < minimo_min:
            return None
        try:
            caminho = self.backup()
        except Exception as e:  # noqa: BLE001 - o backup nunca pode impedir o caixa de trabalhar
            log.error("Backup automático (%s) falhou: %s", motivo, e)
            self.banco.cfg_set("backup_erro", f"{fmt.agora()} {e}"[:300])
            notificacoes.avisar(self.banco, "backup", "backup_falhou", str(e))
            return None
        self.banco.cfg_set("backup_erro", "")
        log.info("Backup automático (%s): %s", motivo, caminho)
        return caminho

    def idade_backup_horas(self) -> float | None:
        ultimo = self.ultimo_backup()
        if not ultimo:
            return None
        try:
            return max((datetime.fromisoformat(fmt.agora()) - datetime.fromisoformat(ultimo)).total_seconds() / 3600, 0.0)
        except ValueError:
            return None

    def situacao_backup(self, limite_horas: int = 24) -> tuple[str, str]:
        """(nível, texto) para o painel: 'ok', 'aviso' (atrasado, com erro ou sem cópia extra que falhou) ou 'sem'."""
        erro = self.banco.cfg("backup_erro")
        idade = self.idade_backup_horas()
        if idade is None:
            return "sem", "ATENÇÃO: nenhum backup feito ainda. Faça em Utilitários > Backup de dados."
        quando = fmt.fmt_datahora(self.ultimo_backup())
        if erro:
            return "aviso", f"ATENÇÃO: o último backup automático falhou. Último que deu certo: {quando}."
        if idade >= limite_horas:
            return "aviso", f"ATENÇÃO: último backup há {int(idade // 24)} dia(s) e {int(idade % 24)} h ({quando})."
        extra_erro = self.banco.cfg("backup_extra_erro")
        if extra_erro:
            return "aviso", f"Último backup: {quando}, mas {extra_erro}."
        return "ok", f"Último backup: {quando}"

    def listar_backups(self) -> list[Path]:
        return protecao.listar_backups(self.pastas_backup())

    def pedir_restauracao(self, backup: str) -> None:
        """Marca a restauração para o próximo início do programa e antes guarda uma cópia do banco de agora."""
        if not protecao.backup_valido(backup):
            raise ErroNegocio("O backup escolhido está danificado ou não é um banco do PDV.")
        self.backup()                        # rede de segurança: a situação de agora também fica guardada
        self.banco.log("restauracao_pedida", str(backup), self.operador_id)
        protecao.pedir_restauracao(self.banco.caminho, backup)

    def pacote_suporte(self) -> str:
        return str(registro.pacote_suporte(self.pasta_backup().parent / "Suporte"))

    def ultimo_backup(self) -> str | None:
        return self.banco.cfg("ultimo_backup") or None

    # -------------------------------------------------------------- limpeza
    def limpar_movimento(self, antes_de: str) -> dict:
        """Apaga vendas e movimentos ANTERIORES à data (o período apagado termina no dia anterior).

        Salvaguardas: faz backup antes e não apaga o dia de hoje em diante."""
        data = fmt.para_data_iso(antes_de)
        if not data:
            raise ErroNegocio("Informe a data limite (dd/mm/aaaa).")
        if data > fmt.hoje():
            raise ErroNegocio("A data limite não pode ser futura.")
        if data == fmt.hoje():
            raise ErroNegocio("A limpeza apaga até o dia anterior à data informada; use no máximo a data de hoje "
                              "menos 1 dia para preservar o movimento atual.")
        alvo = ("status IN ('fechada','cancelada') AND date(COALESCE(fechada_em, aberta_em)) < ?")
        copia = self.backup()
        with self.banco.transacao():
            # A numeração dos cupons continua de onde parou (turno_controller.proximo_cupom), mesmo sem as vendas apagadas.
            self.banco.cfg_set("ultimo_cupom_emitido", self.banco.valor(
                "SELECT MAX(COALESCE(MAX(cupom), 0), ?) FROM vendas", (self.banco.cfg_int("ultimo_cupom_emitido", 0),), 0))
            ids = [r[0] for r in self.banco.todos(f"SELECT id FROM vendas WHERE {alvo}", (data,))]
            for i in range(0, len(ids), 500):
                lote = ids[i:i + 500]
                marcas = ",".join("?" * len(lote))
                self.banco.executar(f"UPDATE caderneta SET venda_id = NULL WHERE venda_id IN ({marcas})", lote)
                self.banco.executar(f"UPDATE repiques SET venda_id = NULL WHERE venda_id IN ({marcas})", lote)
                self.banco.executar(f"DELETE FROM vendas WHERE id IN ({marcas})", lote)
            # Fica o turno que ainda tem venda ou que recebeu o adiantamento de uma conta fechada depois do corte.
            turnos = [r[0] for r in self.banco.todos(
                """SELECT t.id FROM turnos t WHERE t.status = 'fechado' AND date(t.aberto_em) < ?
                   AND NOT EXISTS (SELECT 1 FROM vendas v WHERE v.turno_id = t.id)
                   AND NOT EXISTS (SELECT 1 FROM pagamentos_venda p WHERE p.turno_id = t.id)""", (data,))]
            comissoes = 0
            for t in turnos:
                # Comissões das garotas: a paga aponta para a sangria que vai ser apagada; as pagas e canceladas saem com o
                # turno, mas a PENDENTE é dinheiro devido e fica (só perde o turno).
                self.banco.executar("UPDATE comissoes_garotas SET movimento_id = NULL WHERE movimento_id IN "
                                    "(SELECT id FROM movimentos_caixa WHERE turno_id = ?)", (t,))
                self.banco.executar("UPDATE comissoes_garotas SET turno_id = NULL WHERE turno_id = ? AND status = 'pendente'", (t,))
                self.banco.executar("UPDATE comissoes_garotas SET pago_turno_id = NULL WHERE pago_turno_id = ?", (t,))
                comissoes += self.banco.executar(
                    "DELETE FROM comissoes_garotas WHERE turno_id = ? AND status <> 'pendente'", (t,)).rowcount
                self.banco.executar("DELETE FROM acertos_garotas WHERE turno_id = ?", (t,))      # o acerto sai com o turno e a sangria dele
                self.banco.executar("DELETE FROM movimentos_caixa WHERE turno_id = ?", (t,))
                self.banco.executar("DELETE FROM repiques WHERE turno_id = ?", (t,))
                self.banco.executar("DELETE FROM turnos WHERE id = ?", (t,))
            movs = self.banco.executar("DELETE FROM movimentos_estoque WHERE date(criado_em) < ?", (data,)).rowcount
            logs = self.banco.executar("DELETE FROM log_eventos WHERE date(quando) < ?", (data,)).rowcount
            self.banco.log("limpeza_movimento", f"até {data}: {len(ids)} vendas, {len(turnos)} turnos", self.operador_id)
        return {"vendas": len(ids), "turnos": len(turnos), "movimentos_estoque": movs, "logs": logs, "comissoes": comissoes,
                "backup": copia}

    # ------------------------------------------------------ comunicação
    def abrir_programa_comunicacao(self) -> None:
        """Abre o programa configurado (ex.: TeamViewer). Sem configuração, abre a Calculadora do Windows."""
        caminho = self.banco.cfg("programa_comunicacao").strip()
        try:
            if caminho:
                if not os.path.exists(caminho):
                    raise ErroNegocio(f"Programa não encontrado: {caminho}")
                subprocess.Popen([caminho])
            elif os.name == "nt":
                subprocess.Popen(["calc.exe"])
            else:
                raise ErroNegocio("Configure o programa de comunicação em Configurações > Configurações.")
        except OSError as e:
            raise ErroNegocio(f"Não foi possível abrir o programa: {e}") from e
