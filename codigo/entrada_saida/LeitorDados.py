import csv
import logging
from datetime import datetime
from pathlib import Path

from grafo.grafo import Conta, Grafo, PadraoReal, Transacao

log = logging.getLogger(__name__)

NUM_COLUNAS = 11


class LeitorDados:
    def carregarTransacoes(self, caminho: str, limite: int = 0) -> list[Transacao]:
        arquivo_csv = Path(caminho)
        if not arquivo_csv.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        contas: dict[tuple[str, str], Conta] = {}
        transacoes: list[Transacao] = []
        descartadas = 0

        with arquivo_csv.open("r", newline="", encoding="utf-8-sig") as arquivo:
            leitor = csv.reader(arquivo)
            cabecalho = next(leitor, None)
            if cabecalho is None or len(cabecalho) != NUM_COLUNAS:
                raise ValueError("CSV de transações inválido: eram esperadas 11 colunas.")

            for linha in leitor:
                if limite > 0 and len(transacoes) >= limite:
                    break
                if len(linha) != NUM_COLUNAS:
                    descartadas += 1
                    continue
                try:
                    transacoes.append(self._criarTransacao(linha, contas))
                except (ValueError, IndexError):
                    descartadas += 1

        if descartadas:
            log.warning("%d linhas descartadas em %s", descartadas, caminho)
        log.info("%d transações, %d contas distintas", len(transacoes), len(contas))
        return transacoes

    def carregarPadroes(self, caminho: str) -> list[PadraoReal]:
        arquivo_txt = Path(caminho)
        if not arquivo_txt.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        contas: dict[tuple[str, str], Conta] = {}
        padroes: list[PadraoReal] = []
        tipo_atual = None
        transacoes_atuais: list[Transacao] = []

        with arquivo_txt.open("r", encoding="utf-8-sig") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if not linha:
                    continue
                if linha.startswith("BEGIN LAUNDERING ATTEMPT"):
                    if tipo_atual is not None:
                        padroes.append(PadraoReal(tipo_atual, transacoes_atuais))
                    tipo_atual = self._normalizarTipo(linha)
                    transacoes_atuais = []
                    continue
                if linha.startswith("END LAUNDERING ATTEMPT"):
                    if tipo_atual is not None:
                        padroes.append(PadraoReal(tipo_atual, transacoes_atuais))
                    tipo_atual = None
                    transacoes_atuais = []
                    continue
                if tipo_atual is None:
                    continue
                campos = next(csv.reader([linha]))
                if len(campos) == NUM_COLUNAS:
                    try:
                        transacoes_atuais.append(self._criarTransacao(campos, contas))
                    except (ValueError, IndexError):
                        pass

        if tipo_atual is not None:
            padroes.append(PadraoReal(tipo_atual, transacoes_atuais))
        return padroes

    def construirGrafo(self, transacoes: list[Transacao]) -> Grafo:
        grafo = Grafo()
        for transacao in transacoes:
            grafo.adicionarTransacao(transacao)
        return grafo


    @staticmethod
    def _normalizarTipo(linha: str) -> str:
        """'BEGIN LAUNDERING ATTEMPT - CYCLE:  Max 6 hops' -> 'CYCLE'"""
        resto = linha.replace("BEGIN LAUNDERING ATTEMPT", "", 1).strip(" :-")
        return resto.split(":", 1)[0].strip()

    @staticmethod
    def _conta(banco: str, numero: str, contas: dict) -> Conta:
        chave = (banco.strip(), numero.strip())
        conta = contas.get(chave)
        if conta is None:
            conta = contas[chave] = Conta(*chave)
        return conta

    @staticmethod
    def _parseInstante(s: str) -> datetime:
        s = s.strip()
        return datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
                        int(s[11:13]), int(s[14:16]))

    @classmethod
    def _criarTransacao(cls, campos: list[str], contas: dict) -> Transacao:
        return Transacao(
            origem=cls._conta(campos[1], campos[2], contas),
            destino=cls._conta(campos[3], campos[4], contas),
            valor=float(campos[7]),
            moeda=campos[8].strip(),
            instante=cls._parseInstante(campos[0]),
            formatoPagamento=campos[9].strip(),
            rotuloLavagem=campos[10].strip() == "1",
        )