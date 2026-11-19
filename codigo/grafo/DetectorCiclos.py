from dataclasses import dataclass
from grafo.grafo import Conta, Grafo, Transacao


@dataclass
class Ciclo:
    """Ciclo direcionado simples: contas[0] -> contas[1] -> ... -> contas[0].

    transacoes[i] é a transação que leva contas[i] a contas[(i+1) % n].
    """
    contas: list[Conta]
    transacoes: list[Transacao]

    def tamanho(self) -> int:
        return len(self.contas)

    def valorMinimo(self) -> float:
        return min(t.valor for t in self.transacoes)

    def possuiRotuloLavagem(self) -> bool:
        return any(t.rotuloLavagem for t in self.transacoes)

    def __str__(self) -> str:
        ids = [c.id() for c in self.contas] + [self.contas[0].id()]
        return " -> ".join(ids)


class DetectorCiclos:
    """Detecta ciclos direcionados (layering) usando busca em profundidade.

    Estratégia:
      1. Tarjan iterativo separa o grafo em componentes fortemente conexas (CFCs).
         Um ciclo só existe dentro de uma CFC, então o resto é descartado.
      2. Em cada CFC, uma DFS limitada por `tamanhoMax` parte de cada vértice
         `s` e só visita vértices com índice maior que o de `s`. Assim, cada
         ciclo é reportado uma única vez, a partir de seu menor vértice.
      3. Opcionalmente (`ordemTemporal`), as transações do ciclo precisam ocorrer
         em ordem cronológica, o que representa o dinheiro de fato circulando.
    """

    def __init__(self, tamanhoMin: int = 2, tamanhoMax: int = 6,
                 ordemTemporal: bool = True, limiteCiclos: int = 0):
        if tamanhoMin < 2:
            raise ValueError("tamanhoMin deve ser >= 2 (laços não são considerados).")
        if tamanhoMax < tamanhoMin:
            raise ValueError("tamanhoMax deve ser >= tamanhoMin.")
        self.tamanhoMin = tamanhoMin
        self.tamanhoMax = tamanhoMax
        self.ordemTemporal = ordemTemporal
        self.limiteCiclos = limiteCiclos  # 0 = sem limite

    def detectar(self, grafo: Grafo) -> list[Ciclo]:
        ciclos: list[Ciclo] = []
        for componente in self._componentesFortes(grafo):
            if len(componente) < self.tamanhoMin:
                continue
            self._ciclosNaComponente(grafo, componente, ciclos)
            if self._cheio(ciclos):
                break
        return ciclos

    def _cheio(self, ciclos: list[Ciclo]) -> bool:
        return self.limiteCiclos > 0 and len(ciclos) >= self.limiteCiclos

    def _ciclosNaComponente(self, grafo: Grafo, componente: list[Conta],
                            saida: list[Ciclo]) -> None:
        membros = set(componente)
        ordenadas = sorted(componente, key=Conta.id)
        indice = {c: i for i, c in enumerate(ordenadas)}

        # vizinhos[c][d] = transações c -> d (só dentro da CFC), em ordem de tempo
        vizinhos: dict[Conta, dict[Conta, list[Transacao]]] = {}
        for c in ordenadas:
            por_destino: dict[Conta, list[Transacao]] = {}
            for t in grafo.saidas(c):
                if t.destino in membros and t.destino != c:
                    por_destino.setdefault(t.destino, []).append(t)
            for lista in por_destino.values():
                lista.sort(key=lambda t: t.instante)
            vizinhos[c] = por_destino

        for inicio in ordenadas:
            self._dfsDesde(inicio, vizinhos, indice, saida)
            if self._cheio(saida):
                return

    def _dfsDesde(self, inicio: Conta, vizinhos: dict, indice: dict,
                  saida: list[Ciclo]) -> None:
        caminho = [inicio]
        transacoes: list[Transacao] = []
        naPilha = {inicio}

        def dfs(atual: Conta, instante) -> None:
            for destino, lista in vizinhos[atual].items():
                if self._cheio(saida):
                    return
                t = self._escolher(lista, instante)
                if t is None:
                    continue

                if destino == inicio:
                    if len(caminho) >= self.tamanhoMin:
                        saida.append(Ciclo(list(caminho), transacoes + [t]))
                    continue

                if indice[destino] < indice[inicio] or destino in naPilha:
                    continue
                if len(caminho) >= self.tamanhoMax:
                    continue

                caminho.append(destino)
                transacoes.append(t)
                naPilha.add(destino)
                dfs(destino, t.instante if self.ordemTemporal else None)
                naPilha.discard(destino)
                transacoes.pop()
                caminho.pop()

        dfs(inicio, None)

    def _escolher(self, lista: list[Transacao], instante):
        """Primeira transação (a mais antiga) compatível com a ordem temporal."""
        if not self.ordemTemporal or instante is None:
            return lista[0]
        for t in lista:
            if t.instante >= instante:
                return t
        return None

    def _componentesFortes(self, grafo: Grafo) -> list[list[Conta]]:
        indice: dict[Conta, int] = {}
        baixo: dict[Conta, int] = {}
        naPilha: set[Conta] = set()
        pilha: list[Conta] = []
        componentes: list[list[Conta]] = []
        contador = 0

        def sucessores(v: Conta):
            return iter([t.destino for t in grafo.saidas(v)])

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