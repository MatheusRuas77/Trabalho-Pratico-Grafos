from dataclasses import dataclass
from heapq import nlargest
from typing import Iterator

from grafo.grafo import Conta, Grafo


def componentesFortes(grafo: Grafo) -> list[list[Conta]]:
    """Particiona o grafo com Tarjan iterativo."""
    indice: dict[Conta, int] = {}
    baixo: dict[Conta, int] = {}
    naPilha: set[Conta] = set()
    pilha: list[Conta] = []
    componentes: list[list[Conta]] = []
    contador = 0

    def sucessores(v: Conta) -> Iterator[Conta]:
        return (t.destino for t in grafo.saidas(v))

    for raiz in grafo.contas():
        if raiz in indice:
            continue
        indice[raiz] = baixo[raiz] = contador
        contador += 1
        pilha.append(raiz)
        naPilha.add(raiz)
        trabalho = [(raiz, sucessores(raiz))]

        while trabalho:
            v, it = trabalho[-1]
            desceu = False
            for w in it:
                if w not in indice:
                    indice[w] = baixo[w] = contador
                    contador += 1
                    pilha.append(w)
                    naPilha.add(w)
                    trabalho.append((w, sucessores(w)))
                    desceu = True
                    break
                if w in naPilha:
                    baixo[v] = min(baixo[v], indice[w])
            if desceu:
                continue

            trabalho.pop()
            if trabalho:
                pai = trabalho[-1][0]
                baixo[pai] = min(baixo[pai], baixo[v])
            if baixo[v] == indice[v]:
                componente = []
                while True:
                    w = pilha.pop()
                    naPilha.discard(w)
                    componente.append(w)
                    if w == v:
                        break
                componentes.append(componente)
    return componentes


@dataclass
class Cluster:
    idsContas: list[str]
    numTransacoes: int
    valorTotal: float
    valoresPorMoeda: dict[str, float]
    densidade: float
    numRotuladasLavagem: int

    @property
    def numContas(self) -> int:
        return len(self.idsContas)


@dataclass
class ResumoComponentes:
    """Estatísticas da partição completa e métricas dos clusters selecionados."""

    totalComponentes: int
    componentesMulticonta: int
    tamanhoMaior: int
    distribuicaoPorTamanho: dict[int, int]
    clusters: list[Cluster]

    def maioresClusters(self, limite: int = 3) -> list[Cluster]:
        """Exemplos entre os clusters que passaram pelo filtro."""
        return nlargest(limite, self.clusters, key=lambda cluster: cluster.numContas)


@dataclass
class ResultadoComponentes:
    fracos: ResumoComponentes
    fortes: ResumoComponentes


class DetectorComponentes:
    def __init__(self, tamanhoMin: int = 1):
        if tamanhoMin < 1:
            raise ValueError("tamanhoMin deve ser >= 1.")
        self.tamanhoMin = tamanhoMin

    def detectar(self, grafo: Grafo) -> ResultadoComponentes:
        return ResultadoComponentes(
            fracos=self._resumir(grafo, self._componentesFracos(grafo)),
            fortes=self._resumir(grafo, componentesFortes(grafo)),
        )

    @staticmethod
    def _componentesFracos(grafo: Grafo) -> list[list[Conta]]:
        visitadas: set[Conta] = set()
        componentes: list[list[Conta]] = []
        for raiz in grafo.contas():
            if raiz in visitadas:
                continue
            componente = []
            pilha = [raiz]
            visitadas.add(raiz)
            while pilha:
                conta = pilha.pop()
                componente.append(conta)
                for transacoes in (grafo.saidas(conta), grafo.entradas(conta)):
                    for transacao in transacoes:
                        vizinha = (
                            transacao.destino if transacao.origem == conta else transacao.origem
                        )
                        if vizinha not in visitadas:
                            visitadas.add(vizinha)
                            pilha.append(vizinha)
            componentes.append(componente)
        return componentes

    def _resumir(self, grafo: Grafo, componentes: list[list[Conta]]) -> ResumoComponentes:
        distribuicao: dict[int, int] = {}
        clusters: list[Cluster] = []
        for componente in componentes:
            tamanho = len(componente)
            distribuicao[tamanho] = distribuicao.get(tamanho, 0) + 1
            if tamanho >= self.tamanhoMin:
                clusters.append(self._analisarCluster(grafo, componente))
        return ResumoComponentes(
            totalComponentes=len(componentes),
            componentesMulticonta=len(componentes) - distribuicao.get(1, 0),
            tamanhoMaior=max(distribuicao, default=0),
            distribuicaoPorTamanho=distribuicao,
            clusters=clusters,
        )

    @staticmethod
    def _analisarCluster(grafo: Grafo, componente: list[Conta]) -> Cluster:
        membros = set(componente)
        numTransacoes = 0
        numRotuladas = 0
        numPares = 0
        valorTotal = 0.0
        valoresPorMoeda: dict[str, float] = {}
        for origem in componente:
            destinosDistintos: set[Conta] = set()
            for transacao in grafo.saidas(origem):
                destino = transacao.destino
                if destino not in membros:
                    continue
                numTransacoes += 1
                numRotuladas += transacao.rotuloLavagem
                valorTotal += transacao.valor
                moeda = transacao.moeda
                valoresPorMoeda[moeda] = valoresPorMoeda.get(moeda, 0.0) + transacao.valor
                if destino != origem:
                    destinosDistintos.add(destino)
            numPares += len(destinosDistintos)

        tamanho = len(componente)
        paresPossiveis = tamanho * (tamanho - 1)
        return Cluster(
            idsContas=[conta.id() for conta in componente],
            numTransacoes=numTransacoes,
            valorTotal=valorTotal,
            valoresPorMoeda=valoresPorMoeda,
            densidade=numPares / paresPossiveis if paresPossiveis else 0.0,
            numRotuladasLavagem=numRotuladas,
        )
