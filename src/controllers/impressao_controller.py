"""Textos para a impressora de cupom (fita de 40 colunas) e envio para tela/arquivo/Windows.

Não há emissão fiscal: tudo sai como 'CUPOM NÃO FISCAL'. Leitura X e Redução Z são relatórios
gerenciais calculados a partir do banco, não comandos de impressora fiscal (ECF).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from src.controllers.caixa_controller import CaixaController
from src.controllers.config_controller import ConfigController
from src.controllers.relatorio_controller import RelatorioController
from src.core import formatacao as fmt
from src.core.posicao import nome as nome_posicao
from src.core.relatorio import para_texto
from src.database.conexao import RAIZ
from src.controllers.fila_impressao_controller import FilaImpressao
from src.hardware import impressora_termica as term
from src.hardware.imagem_escpos import logotipo_escpos
from src.hardware.impressora_termica import ErroImpressao, ImpressoraTermica

# Documentos que levam o logotipo da loja no topo (os internos, como sangria e fechamento, não).
TIPOS_COM_LOGOTIPO = {"cupom", "pre_conta", "entrega"}

# Ênfase ESC/POS por tipo de documento (quais linhas saem em negrito/dobro de altura).
_ESTILOS = {
    "cupom": {"negrito_linhas": 1, "grande_prefixos": ("TOTAL",)},
    "pre_conta": {"negrito_linhas": 1, "grande_prefixos": ("TOTAL",)},
    "entrega": {"negrito_linhas": 1, "grande_prefixos": ("TOTAL", "LEVAR TROCO")},
    "fechamento": {"negrito_linhas": 1, "grande_prefixos": ("RESULTADO", "Valor esperado")},
    "pedido": {"negrito_linhas": 1},
    "comprovante": {"negrito_linhas": 1, "grande_prefixos": ("Valor",)},
    "relatorio": {"negrito_linhas": 1},
}

M, Q = fmt.fmt_num, fmt.fmt_qtd


def _lr(esq: str, dir_: str, w: int) -> str:
    esq = esq[: max(w - len(dir_) - 1, 1)]
    return esq.ljust(w - len(dir_)) + dir_


class ImpressaoController:
    def __init__(self, banco):
        self.banco = banco
        self.config = ConfigController(banco)
        self.caixa = CaixaController(banco)
        self.fila = FilaImpressao(banco)

    # ------------------------------------------------------------- base
    def largura(self) -> int:
        return int(self.config.maquina()["colunas_fita"] or 40)

    def cabecalho(self, w: int) -> list[str]:
        l = self.config.loja()
        linhas = [(l["nome_fantasia"] or l["razao_social"] or "PDV").upper().center(w)]
        if l["razao_social"] and l["razao_social"] != l["nome_fantasia"]:
            linhas.append(l["razao_social"].center(w))
        if l["slogan"]:
            linhas.append(l["slogan"].center(w))
        endereco = ", ".join(x for x in (l["endereco"], l["bairro"], l["cidade"]) if x)
        if endereco:
            linhas.append(endereco[:w].center(w))
        if l["cnpj"]:
            linhas.append(f"CNPJ {l['cnpj']}".center(w))
        if l["telefone"]:
            linhas.append(f"Tel. {l['telefone']}".center(w))
        return linhas

    # ------------------------------------------------------------ cupons
    def _corpo_itens(self, venda_id: int, w: int) -> list[str]:
        out = []
        for it in self.caixa.itens(venda_id):
            out.append(f"{it['codigo'][-6:]} {it['nome']}"[:w])
            if it["partes_nomes"]:
                out += [f"  1/{it['partes']} {n}"[:w] for n in it["partes_nomes"]]
            out.append(_lr(f"  {Q(it['quantidade'])} {it['unidade']} x {M(it['preco_unit_cent'])}", M(it["total_cent"]), w))
            if it["observacao"]:
                out.append(f"  * {it['observacao']}"[:w])
        return out

    def _totais(self, v: dict, w: int) -> list[str]:
        out = [_lr("Subtotal", M(v["subtotal_cent"]), w)]
        if v["desconto_cent"]:
            out.append(_lr("Desconto (-)", M(v["desconto_cent"]), w))
        if v["servico_cent"]:
            out.append(_lr("Serviço (+)", M(v["servico_cent"]), w))
        if v["taxa_cent"]:
            out.append(_lr("Taxa de entrega (+)", M(v["taxa_cent"]), w))
        out.append(_lr("TOTAL", M(v["total_cent"]), w))
        return out

    def _origem(self, v: dict) -> str:
        if v["modalidade"] == "mesa":
            return nome_posicao(v.get("comanda"), v["posicao"])
        if v["modalidade"] == "entrega":
            return f"Entrega pedido {v['posicao']}"
        if v["modalidade"] == "caderneta":
            return "Caderneta"
        return "Balcão"

    def cupom(self, venda_id: int, segunda_via: bool = False) -> str:
        w = self.largura()
        v = self.caixa.obter(venda_id)
        op = self.banco.valor("SELECT nome FROM operadores WHERE id = ?", (v["operador_id"],), "")
        linhas = self.cabecalho(w) + ["=" * w]
        titulo = "CUPOM NÃO FISCAL" + (" - CANCELADO" if v["status"] == "cancelada" else "")
        if segunda_via:
            linhas.append("** SEGUNDA VIA - REIMPRESSAO **".center(w))
        linhas += [titulo.center(w), _lr(f"Cupom {v['cupom'] or '-'}", self._origem(v), w),
                   _lr(fmt.fmt_datahora(v["fechada_em"] or v["aberta_em"]), f"Op: {op}", w), "-" * w]
        if v["cliente_id"]:
            c = self.banco.um("SELECT nome FROM clientes WHERE id = ?", (v["cliente_id"],))
            linhas.append(f"Cliente: {c['nome']}"[:w])
        linhas += self._corpo_itens(venda_id, w) + ["-" * w] + self._totais(v, w)
        pags = self.caixa.pagamentos(venda_id)
        if pags:
            linhas.append("-" * w)
            linhas += [_lr(p["tipo"], M(p["valor_cent"]), w) for p in pags]
            if v["troco_cent"]:
                linhas.append(_lr("Troco", M(v["troco_cent"]), w))
            if v["vale_cent"]:
                linhas.append(_lr("Contra-vale emitido", M(v["vale_cent"]), w))
        elif v["modalidade"] == "caderneta" and v["status"] == "fechada":
            linhas.append("Lançado na caderneta do cliente".center(w))
        if v["mensagem"]:
            linhas.append(f"Msg: {v['mensagem']}"[:w])
        rodape = self.banco.cfg("mensagem_rodape") or "Obrigado e volte sempre!"
        linhas += ["=" * w, rodape.center(w)]
        return "\n".join(linhas)

    def pre_conta(self, venda_id: int) -> str:
        """Conta enviada à mesa ou comanda para o cliente conferir antes de pagar."""
        w = self.largura()
        v = self.caixa.obter(venda_id)
        titulo = "CONTA DA COMANDA (NÃO É CUPOM FISCAL)" if v.get("comanda") else "CONTA DA MESA (NÃO É CUPOM FISCAL)"
        linhas = self.cabecalho(w) + ["=" * w, titulo.center(w),
                                      _lr(self._origem(v), fmt.fmt_datahora(fmt.agora()), w), "-" * w]
        linhas += self._corpo_itens(venda_id, w) + ["-" * w] + self._totais(v, w)
        if v["pessoas"] > 1:
            linhas.append(_lr(f"Por pessoa ({v['pessoas']})", M(fmt.dividir_cent(v["total_cent"], v["pessoas"])), w))
        return "\n".join(linhas)

    def pedido_entrega(self, venda_id: int) -> str:
        w = self.largura()
        v = self.caixa.obter(venda_id)
        c = self.banco.um(
            """SELECT c.*, b.nome AS bairro FROM clientes c LEFT JOIN bairros b ON b.id = c.bairro_id WHERE c.id = ?""",
            (v["cliente_id"],))
        linhas = self.cabecalho(w) + ["=" * w, "E N T R E G A".center(w),
                                      _lr(fmt.fmt_datahora(v["aberta_em"]), f"Pedido {v['posicao']}", w), "-" * w,
                                      f"Cliente : {c['nome']}"[:w], f"Número  : {c['numero_consulta']}"[:w],
                                      f"Endereço: {c['endereco'] or ''} {c['complemento'] or ''}".strip()[:w * 2],
                                      f"Bairro  : {c['bairro'] or ''}", f"Telefone: {c['telefone'] or ''}", "-" * w]
        linhas += self._corpo_itens(venda_id, w) + ["-" * w] + self._totais(v, w) + ["=" * w]
        if v["troco_para_cent"]:
            linhas += [f"Pagamento: levar troco para {M(v['troco_para_cent'])}".strip(),
                       _lr("LEVAR TROCO DE", M(max(v["troco_para_cent"] - v["total_cent"], 0)), w)]
        if v["mensagem"]:
            linhas.append(f"Mensagem: {v['mensagem']}")
        return "\n".join(linhas)

    def pedido_remoto(self, venda_id: int, item_ids: list[int] | None = None) -> dict[str, str]:
        """Tickets para a cozinha/bar: um por subgrupo marcado com 'impressora remota'.
        As observações dos itens (ao ponto, sem gelo...) só aparecem aqui, não no cupom do cliente."""
        w = self.largura()
        v = self.caixa.obter(venda_id)
        sql = """SELECT i.id, i.quantidade, i.observacao, pr.nome, s.nome AS subgrupo FROM itens_venda i
                 JOIN produtos pr ON pr.id = i.produto_id JOIN subgrupos s ON s.id = pr.subgrupo_id
                 WHERE i.venda_id = ? AND i.cancelado = 0 AND s.impressora_remota = 1"""
        params: list = [venda_id]
        if item_ids:
            sql += f" AND i.id IN ({','.join('?' * len(item_ids))})"
            params += item_ids
        porsub: dict = {}
        for r in self.banco.todos(sql + " ORDER BY s.nome, i.id", params):
            porsub.setdefault(r["subgrupo"], []).append(r)
        saida = {}
        for sub, itens in porsub.items():
            linhas = [f"PEDIDO - {sub}".center(w), _lr(self._origem(v), fmt.fmt_hora(fmt.agora())[:5], w), "-" * w]
            for r in itens:
                linhas.append(f"{Q(r['quantidade'], 0) if r['quantidade'] == int(r['quantidade']) else Q(r['quantidade'])} x {r['nome']}"[:w])
                if r["observacao"]:
                    linhas.append(f"   >> {r['observacao']}"[:w])
            saida[sub] = "\n".join(linhas)
        return saida

    # ------------------------------------------------- turno e relatórios
    def fechamento(self, resumo: dict) -> str:
        w = self.largura()
        t = resumo["turno"]
        linhas = self.cabecalho(w) + ["=" * w, "FECHAMENTO DE TURNO".center(w),
                                      _lr(f"Turno {t['numero']}", f"Cupons {resumo['cupom_inicial']} a {resumo['cupom_final']}", w),
                                      f"Abertura  : {fmt.fmt_datahora(t['aberto_em'])}",
                                      f"Fechamento: {fmt.fmt_datahora(t.get('fechado_em') or fmt.agora())}", "-" * w,
                                      _lr("Valor inicial (+)", M(resumo["valor_inicial"]), w), "Recebimentos:"]
        linhas += [_lr(f"  {r['tipo']}{'' if r.get('na_gaveta', 1) else ' *'}", M(r["valor"]), w) for r in resumo["recebimentos"]]
        if any(not r.get("na_gaveta", 1) for r in resumo["recebimentos"]):
            linhas.append("  * fora da gaveta")
        for rotulo, chave in (("Troco", "troco"), ("C. Vale emitido", "vale_emitido"), ("Venda (+)", "venda"),
                              ("Desconto (-)", "desconto"), ("Serviço (+)", "servico"), ("Taxa (+)", "taxa"),
                              ("Repique", "repique"), ("Venda caderneta", "venda_caderneta"),
                              ("Pagtos caderneta (+)", "pagtos_caderneta"), ("Entradas financ. (+)", "entradas"),
                              ("Saídas financ. (-)", "saidas")):
            linhas.append(_lr(rotulo, M(resumo[chave]), w))
        linhas += ["-" * w, _lr("TC (cupons)", str(resumo["tc"]), w), _lr("TM", M(resumo["tm"]), w),
                   _lr("Pessoas", str(resumo["pessoas"]), w), _lr("Valor por pessoa", M(resumo["valor_por_pessoa"]), w),
                   "-" * w]
        if resumo.get("fora_da_gaveta"):
            linhas.append(_lr("Fora da gaveta (cartão/Pix)", M(resumo["fora_da_gaveta"]), w))
        linhas.append(_lr("Valor esperado", M(resumo["esperado"]), w))
        if "valor_final" in resumo:
            linhas += [_lr("Valor final (declarado)", M(resumo["valor_final"]), w),
                       _lr("RESULTADO (sobra/falta)", M(resumo["resultado"]), w)]
        return "\n".join(linhas + ["=" * w])

    def comprovante_movimento(self, tipo: str, valor_cent: int, descricao: str, operador: str) -> str:
        w = self.largura()
        titulo = "SANGRIA" if tipo == "saida" else "ENTRADA DE CAIXA"
        return "\n".join(self.cabecalho(w) + ["=" * w, titulo.center(w), fmt.fmt_datahora(fmt.agora()),
                                              _lr("Valor", M(valor_cent), w), f"Motivo: {descricao}"[:w * 2],
                                              f"Operador: {operador}", "", "_" * w, "Assinatura".center(w)])

    def leitura_x(self, turno_id: int) -> str:
        """Parcial gerencial do turno (equivale ao uso da Leitura X do manual; não é fiscal)."""
        from src.controllers.turno_controller import TurnoController
        return "LEITURA X (GERENCIAL - NÃO FISCAL)\n" + self.fechamento(TurnoController(self.banco).resumo(turno_id))

    def reducao_z(self, data_iso: str | None = None) -> str:
        """Fechamento gerencial do dia (não fiscal: não bloqueia vendas nem zera contadores)."""
        d = data_iso or fmt.hoje()
        rel = RelatorioController(self.banco).totalizacao_fita({"de": d, "ate": d})
        rel.titulo = f"Redução Z (gerencial) {fmt.fmt_data(d)}"
        return para_texto(rel, self.largura())

    def tabela_precos(self) -> str:
        """Botão 'Imprimir Tabela' do cadastro de produtos: código, descrição e preço."""
        w = self.largura()
        linhas = ["TABELA DE PREÇOS".center(w), fmt.fmt_datahora(fmt.agora()).center(w), "=" * w]
        from src.controllers.produto_controller import ProdutoController
        prods = ProdutoController(self.banco)
        for p in prods.listar_venda():
            linhas.append(_lr(f"{p['codigo'][-6:]} {p['nome']}", M(prods.preco_vigente(p)), w))
        return "\n".join(linhas)

    # ----------------------------------------------------------- saída
    def pasta_saida(self) -> Path:
        p = RAIZ / "impressao"
        p.mkdir(exist_ok=True)
        return p

    def _historico(self, texto: str, nome: str) -> str:
        """Grava sempre uma cópia do documento em impressao/ (rastreabilidade)."""
        seguro = re.sub(r"[^A-Za-z0-9_-]+", "_", nome)[:40] or "documento"
        caminho = self.pasta_saida() / f"{fmt.agora().replace(':', '').replace(' ', '-')}-{seguro}.txt"
        caminho.write_text(texto, encoding="utf-8")
        return str(caminho)

    def impressora_termica(self) -> ImpressoraTermica:
        return ImpressoraTermica.da_maquina(self.config.maquina())

    def modo(self) -> str:
        return self.config.maquina()["modo_impressao"]

    def deve_mostrar_na_tela(self) -> bool:
        return self.modo() == "tela"

    def _logotipo(self, tipo: str | None) -> bytes | None:
        """Logotipo em ESC/POS para o documento, ou None (desligado, sem arquivo ou arquivo inválido).
        Um logotipo ruim nunca impede o cupom de sair: o erro vai para o log e o cupom sai sem ele."""
        if tipo not in TIPOS_COM_LOGOTIPO:
            return None
        m = self.config.maquina()
        caminho = (self.config.loja().get("logotipo") or "").strip()
        if not m["impressora_termica_logotipo"] or not caminho:
            return None
        try:
            return logotipo_escpos(caminho, int(m["colunas_fita"] or 48))
        except ErroImpressao as e:
            self.banco.log("logotipo_invalido", str(e)[:300])
            return None

    def opcoes_cupom(self, venda_id: int) -> dict:
        """Vias e gaveta de um cupom, a partir das formas de pagamento usadas na venda.

        vias  = maior 'nº de vias' entre as formas (cadastro de tipos de pagamento), de 1 a 3;
        gaveta = alguma forma fica fisicamente na gaveta (dinheiro, cheque, ticket) ou houve troco."""
        r = self.banco.um(
            """SELECT COALESCE(MAX(t.vias), 1) AS vias, COALESCE(MAX(t.na_gaveta), 0) AS na_gaveta
               FROM pagamentos_venda p JOIN tipos_pagamento t ON t.id = p.tipo_pagamento_id WHERE p.venda_id = ?""",
            (venda_id,))
        troco = self.banco.valor("SELECT troco_cent FROM vendas WHERE id = ?", (venda_id,), 0)
        return {"copias": max(1, min(int(r["vias"] or 1), 3)), "abrir_gaveta": bool(r["na_gaveta"]) or troco > 0}

    def enviar(self, texto: str, nome: str = "documento", tipo: str | None = None, abrir_gaveta: bool = False,
               copias: int = 1, venda_id: int | None = None) -> str:
        """Grava o histórico e entrega o documento à saída configurada.

        Na térmica o documento vai para a FILA e este método volta na hora: a thread da fila imprime, tenta de novo
        se a impressora estiver fora e o caixa não espera. Só levanta ErroImpressao para erro de configuração
        (ex.: nenhuma impressora definida). No modo Windows manda o arquivo para a impressora padrão."""
        caminho = self._historico(texto, nome)
        modo = self.modo()
        if modo == "termica":
            imp = self.impressora_termica()
            if not imp.configurada:
                raise ErroImpressao("Nenhuma impressora térmica configurada (Configurações > Máquinas).")
            dados = imp.montar(texto, abrir_gaveta=abrir_gaveta, copias=copias, logotipo=self._logotipo(tipo),
                               **_ESTILOS.get(tipo or "", {"negrito_linhas": 1}))
            self.fila.enfileirar("caixa", nome, dados, tipo, venda_id)
        elif modo == "windows" and hasattr(os, "startfile"):
            os.startfile(caminho, "print")  # type: ignore[attr-defined]
        return caminho

    def enviar_remoto(self, texto: str, nome: str) -> str:
        """Pedido para a cozinha/bar: vai para a impressora remota (pasta ou rede), nunca para a do caixa.
        Por rede entra na fila (a cozinha fora do ar não trava o caixa). Também grava no histórico."""
        caminho = self._historico(texto, nome)
        m = self.config.maquina()
        conexao = (m["impressora_remota_conexao"] or "pasta").strip()
        if conexao == "rede":
            if not (m["impressora_remota_endereco"] or "").strip():
                raise ErroImpressao("Informe o endereço da impressora remota (Configurações > Máquinas).")
            dados = term.texto_para_escpos(texto, codepage=m["impressora_termica_codepage"] or "cp850",
                                           cortar=True, negrito_linhas=1)
            self.fila.enfileirar("remota", nome, dados, "pedido")
        elif conexao == "pasta":
            pasta = (m["impressora_remota_pasta"] or "").strip()
            if pasta:
                destino = Path(pasta)
                destino.mkdir(parents=True, exist_ok=True)
                seguro = re.sub(r"[^A-Za-z0-9_-]+", "_", nome)[:40]
                (destino / f"{fmt.agora().replace(':', '').replace(' ', '-')}-{seguro}.txt").write_text(texto, encoding="utf-8")
        return caminho

    # -------------------------------------------------- gaveta / teste / 2ª via
    def abrir_gaveta(self) -> None:
        """Abre a gaveta pelo pulso da impressora térmica."""
        self.impressora_termica().abrir_gaveta()

    def imprimir_teste(self) -> None:
        """Página de teste da impressora térmica (Configurações > Máquinas)."""
        imp = self.impressora_termica()
        imp.imprimir(imp.ticket_teste(self.config.nome_loja()), grande_prefixos=("TOTAL",), negrito_linhas=1)

    def reimprimir_cupom(self, venda_id: int) -> str:
        """Segunda via de um cupom já fechado/cancelado. Envia para a saída e devolve o texto."""
        texto = self.cupom(venda_id, segunda_via=True)
        self.enviar(texto, f"2via_cupom_{self.banco.valor('SELECT cupom FROM vendas WHERE id=?', (venda_id,)) or venda_id}",
                    tipo="cupom", venda_id=venda_id)
        return texto
