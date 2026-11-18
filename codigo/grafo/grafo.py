from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Conta:
    banco: str
    numero: str
    def id(self) -> str:
        return f"{self.banco}:{self.numero}"

@dataclass
class Transacao:
    origem: Conta
    destino: Conta
    valor: float
    moeda: str
    instante: datetime
    formatoPagamento: str
    rotuloLavagem: bool

@dataclass
class PadraoReal:
    tipo: str
    transacoes: list[Transacao]

class Grafo:
    def __init__(self):
        self.adjacencia: dict[Conta, list[Transacao]] = {}
        self.adjacenciaTransposta: dict[Conta, list[Transacao]] = {}

    def adicionarTransacao(self, t: Transacao):
        self.adjacencia.setdefault(t.origem, []).append(t)
        self.adjacencia.setdefault(t.destino, [])
        self.adjacenciaTransposta.setdefault(t.destino, []).append(t)
        self.adjacenciaTransposta.setdefault(t.origem, [])

    def contas(self) -> list[Conta]:
        return list(self.adjacencia)

    def saidas(self, c: Conta) -> list[Transacao]:
        return self.adjacencia.get(c, [])

    def entradas(self, c: Conta) -> list[Transacao]:
        return self.adjacenciaTransposta.get(c, [])

    def grauSaida(self, c: Conta) -> int:
        return len({t.destino for t in self.saidas(c)})

    def grauEntrada(self, c: Conta) -> int:
        return len({t.origem for t in self.entradas(c)})

    def subgrafo(self, contas: set[Conta]) -> "Grafo":
        resultado = Grafo()
        for c in contas:
            resultado.adjacencia.setdefault(c, [])
            resultado.adjacenciaTransposta.setdefault(c, [])
        for c in contas:
            for t in self.saidas(c):
                if t.destino in contas:
                    resultado.adicionarTransacao(t)
        return resultado

    def numVertices(self) -> int:
        return len(self.adjacencia)

    def numArestas(self) -> int:
        return sum(len(ts) for ts in self.adjacencia.values())
