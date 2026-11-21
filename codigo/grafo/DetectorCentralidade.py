from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from heapq import nlargest
import random

from grafo.grafo import Conta, Grafo, Transacao


def _construirAdjacenciaDirecionada(
    grafo: Grafo,
) -> tuple[list[Conta], dict[Conta, int], list[list[int]]]:
    """Constrói lista de adjacência direcionada simples indexada por inteiros.

    Ignora laços (u == v) e colapsa múltiplas transações u -> v em uma única
    aresta direcionada, pois caminhos mínimos dependem apenas da existência de
    fluxo entre contas distintas.
    """
    contas = grafo.contas()
    indice = {conta: i for i, conta in enumerate(contas)}
    adjacencia: list[list[int]] = []

    for i, conta in enumerate(contas):
        destinos: set[int] = set()
        for transacao in grafo.saidas(conta):
            j = indice[transacao.destino]
            if j != i:
                destinos.add(j)
        adjacencia.append(list(destinos))

    return contas, indice, adjacencia


def _construirAdjacenciaNaoDirecionadaDeDirecionada(
    adjDir: list[list[int]],
) -> list[list[int]]:
    """Deriva o grafo simples não-direcionado subjacente a partir da adjacência direcionada."""
    n = len(adjDir)
    conjuntos: list[set[int]] = [set() for _ in range(n)]
    for u, destinos in enumerate(adjDir):
        conjU = conjuntos[u]
        for v in destinos:
            conjU.add(v)
            conjuntos[v].add(u)
    return [list(viz) for viz in conjuntos]


def _construirAdjacenciaNaoDirecionada(
    grafo: Grafo,
) -> tuple[list[Conta], list[list[int]]]:
    """Constrói grafo simples não-direcionado subjacente indexado por inteiros.

    Duas contas distintas são adjacentes se houver ao menos uma transação em
    qualquer direção entre elas. Laços são ignorados.
    """
    contas, _, adjDir = _construirAdjacenciaDirecionada(grafo)
    return contas, _construirAdjacenciaNaoDirecionadaDeDirecionada(adjDir)


def centralidadeIntermediacao(
    grafo: Grafo,
    amostraFontes: int = 0,
    profundidadeMax: int = 0,
    normalizar: bool = True,
    semente: int = 42,
) -> dict[Conta, float]:
    """Calcula a centralidade de intermediação (Betweenness Centrality) direcionada.

    Implementação própria do algoritmo de Brandes (2001) para grafos direcionados
    não-ponderados, sem bibliotecas prontas de grafos:
      - Para cada vértice-fonte s, executa BFS para calcular distâncias mínimas,
        contagem de caminhos mínimos (sigma) e lista de predecessores (P).
      - Na volta (ordem inversa da pilha da BFS), acumula as dependências delta
        de cada vértice intermediário.

    Quando `amostraFontes > 0` e menor que o número de fontes elegíveis (contas
    com ao menos uma saída para outra conta), aplica a estimativa por amostragem
    de pivôs de Brandes & Pich (2007), escalando os valores por `n_elegiveis / k`.
    Quando `profundidadeMax > 0`, limita os caminhos mínimos a no máximo
    `profundidadeMax` saltos (k-betweenness centrality).

    Complexidade:
      - Exato (`amostraFontes == 0`): O(|V| * (|V| + |E|)) em tempo, O(|V| + |E|) em espaço.
      - Amostrado (`k` fontes): O(k * (|V| + |E|)) em tempo, O(|V| + |E|) em espaço.
    """
    if amostraFontes < 0:
        raise ValueError("amostraFontes deve ser >= 0 (0 = cálculo exato).")
    if profundidadeMax < 0:
        raise ValueError("profundidadeMax deve ser >= 0 (0 = sem limite).")

    contas, _, adj = _construirAdjacenciaDirecionada(grafo)
    n = len(contas)
    if n == 0:
        return {}

    pontuacao, _, _ = _executarBrandes(
        contas=contas,
        adj=adj,
        amostraFontes=amostraFontes,
        profundidadeMax=profundidadeMax,
        normalizar=normalizar,
        semente=semente,
    )
    return {contas[i]: pontuacao[i] for i in range(n)}


def _executarBrandes(
    contas: list[Conta],
    adj: list[list[int]],
    amostraFontes: int,
    profundidadeMax: int,
    normalizar: bool,
    semente: int,
) -> tuple[list[float], int, bool]:
    """Núcleo iterativo de Brandes operando sobre índices inteiros."""
    n = len(contas)
    centralidade = [0.0] * n
    if n <= 2:
        return centralidade, 0, True

    # Contas sem saída não iniciam caminhos mínimos (contribuem 0 para todos os nós).
    elegiveis = [i for i in range(n) if adj[i]]
    totalElegiveis = len(elegiveis)
    if totalElegiveis == 0:
        return centralidade, 0, True

    if amostraFontes == 0 or amostraFontes >= totalElegiveis:
        fontes = elegiveis
        calculoExato = True
    else:
        elegiveisOrdenadas = sorted(elegiveis, key=lambda i: contas[i].id())
        rng = random.Random(semente)
        fontes = rng.sample(elegiveisOrdenadas, amostraFontes)
        calculoExato = False

    # Vetores reutilizados entre BFSs; apenas os vértices visitados são limpos.
    dist = [-1] * n
    sigma = [0] * n
    delta = [0.0] * n
    pred: list[list[int]] = [[] for _ in range(n)]
    pilha: list[int] = []
    fila: deque[int] = deque()

    for s in fontes:
        dist[s] = 0
        sigma[s] = 1
        fila.append(s)
        pilha.clear()

        while fila:
            v = fila.popleft()
            pilha.append(v)
            dv = dist[v]
            if profundidadeMax > 0 and dv >= profundidadeMax:
                continue
            proxDist = dv + 1
            sigV = sigma[v]
            for w in adj[v]:
                dw = dist[w]
                if dw < 0:
                    dist[w] = proxDist
                    fila.append(w)
                    sigma[w] = sigV
                    pred[w].append(v)
                elif dw == proxDist:
                    sigma[w] += sigV
                    pred[w].append(v)

        for w in reversed(pilha):
            fator = (1.0 + delta[w]) / sigma[w]
            for v in pred[w]:
                delta[v] += sigma[v] * fator
            if w != s:
                centralidade[w] += delta[w]

        for v in pilha:
            dist[v] = -1
            sigma[v] = 0
            delta[v] = 0.0
            pred[v].clear()

    escala = 1.0
    if not calculoExato:
        escala *= totalElegiveis / len(fontes)
    if normalizar:
        escala /= (n - 1) * (n - 2)

    if escala != 1.0:
        for i in range(n):
            if centralidade[i] > 0.0:
                centralidade[i] *= escala

    return centralidade, len(fontes), calculoExato


def encontrarPontesEArticulacoes(
    grafo: Grafo,
) -> tuple[list[tuple[Conta, Conta, int, int]], dict[Conta, int]]:
    """Encontra pontes (arestas de corte) e pontos de articulação com Tarjan iterativo.

    Opera sobre o grafo simples não-direcionado subjacente ao grafo de transações:
      - Uma ponte {u, v} é uma ligação única cuja remoção desconecta dois grupos
        de contas (tamanhos `tamanhoLadoA` e `tamanhoLadoB`).
      - Um ponto de articulação v é uma conta cuja remoção fragmenta seu
        componente conexo em `numComponentesAoRemover` (>= 2) partes.

    A implementação é totalmente iterativa para evitar estouro da pilha de
    recursão em redes financeiras de grande porte.

    Complexidade: O(|V| + |E|) em tempo e O(|V| + |E|) em espaço.
    """
    contas, adj = _construirAdjacenciaNaoDirecionada(grafo)
    return _executarTarjanPontesEArticulacoes(contas, adj)


def _executarTarjanPontesEArticulacoes(
    contas: list[Conta],
    adj: list[list[int]],
) -> tuple[list[tuple[Conta, Conta, int, int]], dict[Conta, int]]:
    """Núcleo iterativo de Tarjan para pontes e pontos de articulação."""
    n = len(contas)
    if n == 0:
        return [], {}

    disc = [-1] * n
    low = [0] * n
    pai = [-1] * n
    subarvore = [0] * n
    blocosArticulacao = [0] * n

    pontes: list[tuple[Conta, Conta, int, int]] = []
    articulacoes: dict[Conta, int] = {}
    tempo = 0

    for raiz in range(n):
        if disc[raiz] != -1:
            continue

        disc[raiz] = low[raiz] = tempo
        tempo += 1
        subarvore[raiz] = 1
        filhosRaiz = 0
        ordemComp = [raiz]
        pontesComp: list[tuple[int, int, int]] = []

        # Cada quadro na pilha guarda [vertice, proximo_indice_vizinho].
        pilha: list[list[int]] = [[raiz, 0]]

        while pilha:
            topo = pilha[-1]
            v = topo[0]
            idx = topo[1]
            vizinhos = adj[v]

            if idx < len(vizinhos):
                topo[1] = idx + 1
                w = vizinhos[idx]
                if disc[w] == -1:
                    pai[w] = v
                    disc[w] = low[w] = tempo
                    tempo += 1
                    subarvore[w] = 1
                    ordemComp.append(w)
                    if v == raiz:
                        filhosRaiz += 1
                    pilha.append([w, 0])
                elif w != pai[v]:
                    if disc[w] < low[v]:
                        low[v] = disc[w]
            else:
                pilha.pop()
                p = pai[v]
                if p != -1:
                    subarvore[p] += subarvore[v]
                    if low[v] < low[p]:
                        low[p] = low[v]
                    if p != raiz and low[v] >= disc[p]:
                        blocosArticulacao[p] += 1
                    if low[v] > disc[p]:
                        pontesComp.append((p, v, subarvore[v]))

        tamanhoComp = len(ordemComp)
        if filhosRaiz >= 2:
            articulacoes[contas[raiz]] = filhosRaiz
        for v in ordemComp:
            if v != raiz and blocosArticulacao[v] >= 1:
                articulacoes[contas[v]] = 1 + blocosArticulacao[v]

        for u, v, tamV in pontesComp:
            pontes.append((contas[u], contas[v], tamanhoComp - tamV, tamV))

    return pontes, articulacoes


@dataclass
class PassagemRapida:
    """Evidência temporal de repasse rápido (pass-through) em uma conta.

    Identifica contas que recebem valores e os repassam na mesma moeda dentro de
    uma janela temporal curta (`intervaloMaximo`) com razão mínima compatível
    (`razaoMinima`), comportamento característico de contas "laranjas".
    """

    conta: Conta
    numEventos: int
    melhorRazao: float
    menorIntervalo: timedelta
    valoresPorMoeda: dict[str, float]
    numRotuladasLavagem: int
    centralidade: float = 0.0
    ehPontoArticulacao: bool = False

    @property
    def idConta(self) -> str:
        return self.conta.id()

    def possuiRotuloLavagem(self) -> bool:
        return self.numRotuladasLavagem > 0


def _analisarPassagemRapidaConta(
    grafo: Grafo,
    conta: Conta,
    intervaloMaximo: timedelta,
    razaoMinima: float,
) -> PassagemRapida | None:
    """Analisa passagem rápida por janela deslizante O((d_in + d_out) log d) por moeda."""
    entradas = grafo.entradas(conta)
    saidas = grafo.saidas(conta)
    if not entradas or not saidas:
        return None

    entradasPorMoeda: dict[str, list[Transacao]] = {}
    for transacao in entradas:
        if transacao.origem != conta:
            entradasPorMoeda.setdefault(transacao.moeda, []).append(transacao)
    if not entradasPorMoeda:
        return None

    saidasPorMoeda: dict[str, list[Transacao]] = {}
    for transacao in saidas:
        if transacao.destino != conta and transacao.moeda in entradasPorMoeda:
            saidasPorMoeda.setdefault(transacao.moeda, []).append(transacao)
    if not saidasPorMoeda:
        return None

    numEventos = 0
    melhorRazao = 0.0
    menorIntervalo: timedelta | None = None
    valoresPorMoeda: dict[str, float] = {}

    for moeda, listaSaidas in saidasPorMoeda.items():
        listaEntradas = entradasPorMoeda[moeda]
        listaEntradas.sort(key=lambda t: t.instante)
        listaSaidas.sort(key=lambda t: t.instante)

        mIn = len(listaEntradas)
        mOut = len(listaSaidas)

        prefIn = [0.0] * (mIn + 1)
        for idx, transacao in enumerate(listaEntradas):
            prefIn[idx + 1] = prefIn[idx] + transacao.valor

        prefOut = [0.0] * (mOut + 1)
        for idx, transacao in enumerate(listaSaidas):
            prefOut[idx + 1] = prefOut[idx] + transacao.valor

        esq = 0
        dirOut = 0
        inFim = 0

        for i, tIn in enumerate(listaEntradas):
            t0 = tIn.instante
            limite = t0 + intervaloMaximo

            while dirOut < mOut and listaSaidas[dirOut].instante <= limite:
                dirOut += 1
            while esq < dirOut and listaSaidas[esq].instante < t0:
                esq += 1
            if esq == dirOut:
                continue

            tUltimoOut = listaSaidas[dirOut - 1].instante
            if inFim < i:
                inFim = i
            while inFim < mIn and listaEntradas[inFim].instante <= tUltimoOut:
                inFim += 1

            somaIn = prefIn[inFim] - prefIn[i]
            somaOut = prefOut[dirOut] - prefOut[esq]
            maiorJanela = somaIn if somaIn >= somaOut else somaOut
            razaoJanela = (
                (somaOut if somaIn >= somaOut else somaIn) / maiorJanela
                if maiorJanela > 0.0
                else 0.0
            )

            valIn = tIn.valor
            valParOut = listaSaidas[esq].valor
            maiorPar = valIn if valIn >= valParOut else valParOut
            razaoPar = (
                (valParOut if valIn >= valParOut else valIn) / maiorPar
                if maiorPar > 0.0
                else 0.0
            )

            razao = razaoJanela if razaoJanela >= razaoPar else razaoPar
            if razao >= razaoMinima:
                numEventos += 1
                if razao > melhorRazao:
                    melhorRazao = razao
                deltaT = listaSaidas[esq].instante - t0
                if menorIntervalo is None or deltaT < menorIntervalo:
                    menorIntervalo = deltaT
                valoresPorMoeda[moeda] = valoresPorMoeda.get(moeda, 0.0) + valIn

    if numEventos == 0 or menorIntervalo is None:
        return None

    lavagemEntrada = sum(1 for t in entradas if t.origem != conta and t.rotuloLavagem)
    lavagemSaida = sum(1 for t in saidas if t.rotuloLavagem)

    return PassagemRapida(
        conta=conta,
        numEventos=numEventos,
        melhorRazao=melhorRazao,
        menorIntervalo=menorIntervalo,
        valoresPorMoeda=valoresPorMoeda,
        numRotuladasLavagem=lavagemEntrada + lavagemSaida,
    )


def detectarPassagemRapida(
    grafo: Grafo,
    intervaloMaximo: timedelta = timedelta(hours=24),
    razaoMinima: float = 0.8,
) -> dict[Conta, PassagemRapida]:
    """Detecta contas com repasse rápido (pass-through) em janela temporal.

    Para cada conta e cada moeda movimentada em entrada e saída, usa ponteiros
    deslizantes com somas de prefixo para verificar se os valores recebidos são
    repassados em até `intervaloMaximo` com simetria mínima `razaoMinima`.

    Complexidade: O(|V| + |E| log d_max) em tempo e O(|V| + |E|) em espaço.
    """
    if intervaloMaximo < timedelta(0):
        raise ValueError("intervaloMaximo deve ser >= 0.")
    if not (0.0 < razaoMinima <= 1.0):
        raise ValueError("razaoMinima deve estar no intervalo (0, 1].")

    resultado: dict[Conta, PassagemRapida] = {}
    for conta in grafo.contas():
        evidencia = _analisarPassagemRapidaConta(
            grafo=grafo,
            conta=conta,
            intervaloMaximo=intervaloMaximo,
            razaoMinima=razaoMinima,
        )
        if evidencia is not None:
            resultado[conta] = evidencia
    return resultado


@dataclass
class ContaIntermediaria:
    """Conta identificada como intermediária nos fluxos financeiros (possível laranja).

    `razaoRepassePorMoeda` calcula `min(entrada, saída) / max(entrada, saída)` para
    cada moeda movimentada sem misturar câmbios distintos; `razaoRepasse` é a média
    dessas razões entre as moedas presentes na conta (igual à razão exata quando a
    conta opera em uma única moeda).
    """

    conta: Conta
    centralidade: float
    ehPontoArticulacao: bool
    numComponentesAoRemover: int
    grauEntrada: int
    grauSaida: int
    numTransacoesEntrada: int
    numTransacoesSaida: int
    valorEntrada: float
    valorSaida: float
    valoresEntradaPorMoeda: dict[str, float]
    valoresSaidaPorMoeda: dict[str, float]
    razaoRepassePorMoeda: dict[str, float]
    razaoRepasse: float
    numRotuladasLavagem: int
    numPassagensRapidas: int = 0
    melhorRazaoPassagemRapida: float = 0.0
    menorIntervaloRepasse: timedelta | None = None

    @property
    def idConta(self) -> str:
        return self.conta.id()

    def possuiRotuloLavagem(self) -> bool:
        return self.numRotuladasLavagem > 0


@dataclass
class PontoArticulacao:
    """Vértice de corte cuja remoção fragmenta a rede de transações."""

    conta: Conta
    numComponentesAoRemover: int
    grauEntrada: int
    grauSaida: int
    centralidade: float
    numRotuladasLavagem: int

    @property
    def idConta(self) -> str:
        return self.conta.id()

    def possuiRotuloLavagem(self) -> bool:
        return self.numRotuladasLavagem > 0


@dataclass
class PonteFluxo:
    """Ligação crítica (aresta de corte) entre duas sub-redes de contas."""

    contaA: Conta
    contaB: Conta
    tamanhoLadoA: int
    tamanhoLadoB: int
    numTransacoes: int
    valorTotal: float
    valoresPorMoeda: dict[str, float]
    numRotuladasLavagem: int
    direcional: str

    @property
    def menorLado(self) -> int:
        return min(self.tamanhoLadoA, self.tamanhoLadoB)

    def possuiRotuloLavagem(self) -> bool:
        return self.numRotuladasLavagem > 0

    def __str__(self) -> str:
        return f"{self.contaA.id()} {self.direcional} {self.contaB.id()}"


@dataclass
class ResultadoCentralidade:
    """Resultado consolidado da análise de centralidade, pontes e passagem rápida."""

    totalContasAnalisadas: int
    fontesAmostradas: int
    calculoExato: bool
    contasComIntermediacao: int
    totalPontosArticulacao: int
    totalPontes: int
    totalPontesEntreGrupos: int
    intervaloMaximo: timedelta | None
    razaoMinimaRepasse: float
    totalContasPassagemRapida: int
    intermediarias: list[ContaIntermediaria]
    pontosArticulacao: list[PontoArticulacao]
    pontes: list[PonteFluxo]
    passagensRapidas: list[PassagemRapida]
    centralidades: dict[Conta, float]

    def principaisIntermediarias(self, limite: int = 10) -> list[ContaIntermediaria]:
        return self.intermediarias[:limite]

    def principaisArticulacoes(self, limite: int = 10) -> list[PontoArticulacao]:
        return self.pontosArticulacao[:limite]

    def principaisPontes(self, limite: int = 10) -> list[PonteFluxo]:
        return self.pontes[:limite]

    def principaisPassagensRapidas(self, limite: int = 10) -> list[PassagemRapida]:
        return self.passagensRapidas[:limite]


class DetectorCentralidade:
    """Identifica contas intermediárias ("laranjas"), vértices de corte e pontes.

    Combina três abordagens complementares de Teoria dos Grafos e análise temporal:
      1. Centralidade de Intermediação (Brandes / Brandes-Pich) no grafo
         direcionado, destacando contas que concentram caminhos mínimos de
         escoamento financeiro entre outras contas.
      2. Algoritmo de Tarjan iterativo no grafo não-direcionado subjacente para
         localizar pontes (canais únicos entre sub-redes) e pontos de
         articulação (contas gargalo cuja remoção desconecta a rede).
      3. Análise de passagem rápida em janela temporal (`intervaloMaximo` e
         `razaoMinimaRepasse`), identificando contas que recebem e repassam
         valores rapidamente na mesma moeda.
    """

    def __init__(
        self,
        amostraFontes: int = 1000,
        profundidadeMax: int = 6,
        normalizar: bool = True,
        tamanhoMinLadoPonte: int = 2,
        exigirEntradaESaida: bool = True,
        intervaloMaximo: timedelta | None = timedelta(hours=24),
        razaoMinimaRepasse: float = 0.8,
        limiteResultados: int = 20,
        semente: int = 42,
    ):
        if amostraFontes < 0:
            raise ValueError("amostraFontes deve ser >= 0.")
        if profundidadeMax < 0:
            raise ValueError("profundidadeMax deve ser >= 0.")
        if tamanhoMinLadoPonte < 1:
            raise ValueError("tamanhoMinLadoPonte deve ser >= 1.")
        if intervaloMaximo is not None and intervaloMaximo < timedelta(0):
            raise ValueError("intervaloMaximo deve ser >= 0 ou None.")
        if not (0.0 < razaoMinimaRepasse <= 1.0):
            raise ValueError("razaoMinimaRepasse deve estar no intervalo (0, 1].")
        if limiteResultados < 0:
            raise ValueError("limiteResultados deve ser >= 0.")

        self.amostraFontes = amostraFontes
        self.profundidadeMax = profundidadeMax
        self.normalizar = normalizar
        self.tamanhoMinLadoPonte = tamanhoMinLadoPonte
        self.exigirEntradaESaida = exigirEntradaESaida
        self.intervaloMaximo = intervaloMaximo
        self.razaoMinimaRepasse = razaoMinimaRepasse
        self.limiteResultados = limiteResultados
        self.semente = semente

    def detectar(self, grafo: Grafo) -> ResultadoCentralidade:
        contas, indiceConta, adjDir = _construirAdjacenciaDirecionada(grafo)
        n = len(contas)

        grausSaida = [len(adjDir[i]) for i in range(n)]
        grausEntrada = [0] * n
        for u in range(n):
            for v in adjDir[u]:
                grausEntrada[v] += 1

        pontuacoes, fontesAmostradas, calculoExato = _executarBrandes(
            contas=contas,
            adj=adjDir,
            amostraFontes=self.amostraFontes,
            profundidadeMax=self.profundidadeMax,
            normalizar=self.normalizar,
            semente=self.semente,
        )
        centralidades = {contas[i]: pontuacoes[i] for i in range(n)}

        adjNaoDir = _construirAdjacenciaNaoDirecionadaDeDirecionada(adjDir)
        pontesBrutas, articulacoesBrutas = _executarTarjanPontesEArticulacoes(
            contas, adjNaoDir
        )

        # 0. Passagem rápida em janela temporal (opcional)
        passagensMapa: dict[Conta, PassagemRapida] = {}
        if self.intervaloMaximo is not None:
            passagensMapa = detectarPassagemRapida(
                grafo=grafo,
                intervaloMaximo=self.intervaloMaximo,
                razaoMinima=self.razaoMinimaRepasse,
            )
            for conta, evidencia in passagensMapa.items():
                evidencia.centralidade = centralidades.get(conta, 0.0)
                evidencia.ehPontoArticulacao = conta in articulacoesBrutas

        # 1. Contas intermediárias (centralidade > 0)
        candidatasIndices = [i for i in range(n) if pontuacoes[i] > 0.0]
        if self.exigirEntradaESaida:
            candidatasIndices = [
                i
                for i in candidatasIndices
                if grausEntrada[i] > 0 and grausSaida[i] > 0
            ]
        contasComIntermediacao = len(candidatasIndices)

        if self.limiteResultados > 0 and len(candidatasIndices) > self.limiteResultados:
            selecionadasInterm = nlargest(
                self.limiteResultados,
                candidatasIndices,
                key=lambda i: (
                    pontuacoes[i],
                    contas[i] in articulacoesBrutas,
                    grausEntrada[i] + grausSaida[i],
                ),
            )
        else:
            selecionadasInterm = sorted(
                candidatasIndices,
                key=lambda i: (
                    pontuacoes[i],
                    contas[i] in articulacoesBrutas,
                    grausEntrada[i] + grausSaida[i],
                ),
                reverse=True,
            )

        intermediarias = [
            self._construirContaIntermediaria(
                grafo=grafo,
                conta=contas[i],
                centralidade=pontuacoes[i],
                numComponentes=articulacoesBrutas.get(contas[i], 1),
                grauEntrada=grausEntrada[i],
                grauSaida=grausSaida[i],
                passagemRapida=passagensMapa.get(contas[i]),
            )
            for i in selecionadasInterm
        ]

        # 2. Pontos de articulação (vértices de corte)
        itensArtic = list(articulacoesBrutas.items())
        if self.limiteResultados > 0 and len(itensArtic) > self.limiteResultados:
            selecionadasArtic = nlargest(
                self.limiteResultados,
                itensArtic,
                key=lambda item: (
                    item[1],
                    centralidades[item[0]],
                    grausEntrada[indiceConta[item[0]]] + grausSaida[indiceConta[item[0]]],
                ),
            )
        else:
            selecionadasArtic = sorted(
                itensArtic,
                key=lambda item: (
                    item[1],
                    centralidades[item[0]],
                    grausEntrada[indiceConta[item[0]]] + grausSaida[indiceConta[item[0]]],
                ),
                reverse=True,
            )

        pontosArticulacao = [
            self._construirPontoArticulacao(
                grafo=grafo,
                conta=conta,
                numComponentes=numComp,
                centralidade=centralidades[conta],
                grauEntrada=grausEntrada[indiceConta[conta]],
                grauSaida=grausSaida[indiceConta[conta]],
            )
            for conta, numComp in selecionadasArtic
        ]

        # 3. Pontes estruturais nos fluxos financeiros
        pontesFiltradas = [
            p
            for p in pontesBrutas
            if min(p[2], p[3]) >= self.tamanhoMinLadoPonte
        ]
        pontesAnalisadas = self._construirPontesFluxo(grafo, pontesFiltradas)
        if self.limiteResultados > 0 and len(pontesAnalisadas) > self.limiteResultados:
            pontesRanking = nlargest(
                self.limiteResultados,
                pontesAnalisadas,
                key=lambda p: (p.menorLado, p.numTransacoes, p.valorTotal),
            )
        else:
            pontesRanking = sorted(
                pontesAnalisadas,
                key=lambda p: (p.menorLado, p.numTransacoes, p.valorTotal),
                reverse=True,
            )

        # 4. Ranking de contas com passagem rápida (priorizando interseção com centralidade/corte)
        listaPassagens = list(passagensMapa.values())
        if self.limiteResultados > 0 and len(listaPassagens) > self.limiteResultados:
            passagensRanking = nlargest(
                self.limiteResultados,
                listaPassagens,
                key=lambda p: (
                    p.centralidade > 0.0,
                    p.ehPontoArticulacao,
                    p.centralidade,
                    p.numEventos,
                    p.melhorRazao,
                ),
            )
        else:
            passagensRanking = sorted(
                listaPassagens,
                key=lambda p: (
                    p.centralidade > 0.0,
                    p.ehPontoArticulacao,
                    p.centralidade,
                    p.numEventos,
                    p.melhorRazao,
                ),
                reverse=True,
            )

        return ResultadoCentralidade(
            totalContasAnalisadas=n,
            fontesAmostradas=fontesAmostradas,
            calculoExato=calculoExato,
            contasComIntermediacao=contasComIntermediacao,
            totalPontosArticulacao=len(articulacoesBrutas),
            totalPontes=len(pontesBrutas),
            totalPontesEntreGrupos=len(pontesFiltradas),
            intervaloMaximo=self.intervaloMaximo,
            razaoMinimaRepasse=self.razaoMinimaRepasse,
            totalContasPassagemRapida=len(passagensMapa),
            intermediarias=intermediarias,
            pontosArticulacao=pontosArticulacao,
            pontes=pontesRanking,
            passagensRapidas=passagensRanking,
            centralidades=centralidades,
        )

    @staticmethod
    def _construirContaIntermediaria(
        grafo: Grafo,
        conta: Conta,
        centralidade: float,
        numComponentes: int,
        grauEntrada: int,
        grauSaida: int,
        passagemRapida: PassagemRapida | None = None,
    ) -> ContaIntermediaria:
        entradas = grafo.entradas(conta)
        saidas = grafo.saidas(conta)

        valorEntrada = 0.0
        valoresEntradaPorMoeda: dict[str, float] = {}
        lavagemEntrada = 0
        for transacao in entradas:
            if transacao.origem == conta:
                continue
            valorEntrada += transacao.valor
            moeda = transacao.moeda
            valoresEntradaPorMoeda[moeda] = (
                valoresEntradaPorMoeda.get(moeda, 0.0) + transacao.valor
            )
            if transacao.rotuloLavagem:
                lavagemEntrada += 1

        valorSaida = 0.0
        valoresSaidaPorMoeda: dict[str, float] = {}
        lavagemSaida = 0
        for transacao in saidas:
            if transacao.rotuloLavagem:
                lavagemSaida += 1
            if transacao.destino == conta:
                continue
            valorSaida += transacao.valor
            moeda = transacao.moeda
            valoresSaidaPorMoeda[moeda] = (
                valoresSaidaPorMoeda.get(moeda, 0.0) + transacao.valor
            )

        moedas = set(valoresEntradaPorMoeda) | set(valoresSaidaPorMoeda)
        razaoRepassePorMoeda: dict[str, float] = {}
        for moeda in moedas:
            ve = valoresEntradaPorMoeda.get(moeda, 0.0)
            vs = valoresSaidaPorMoeda.get(moeda, 0.0)
            maior = max(ve, vs)
            razaoRepassePorMoeda[moeda] = min(ve, vs) / maior if maior > 0.0 else 0.0

        razaoRepasse = (
            sum(razaoRepassePorMoeda.values()) / len(razaoRepassePorMoeda)
            if razaoRepassePorMoeda
            else 0.0
        )

        return ContaIntermediaria(
            conta=conta,
            centralidade=centralidade,
            ehPontoArticulacao=numComponentes >= 2,
            numComponentesAoRemover=numComponentes,
            grauEntrada=grauEntrada,
            grauSaida=grauSaida,
            numTransacoesEntrada=len(entradas),
            numTransacoesSaida=len(saidas),
            valorEntrada=valorEntrada,
            valorSaida=valorSaida,
            valoresEntradaPorMoeda=valoresEntradaPorMoeda,
            valoresSaidaPorMoeda=valoresSaidaPorMoeda,
            razaoRepassePorMoeda=razaoRepassePorMoeda,
            razaoRepasse=razaoRepasse,
            numRotuladasLavagem=lavagemEntrada + lavagemSaida,
            numPassagensRapidas=passagemRapida.numEventos if passagemRapida else 0,
            melhorRazaoPassagemRapida=passagemRapida.melhorRazao if passagemRapida else 0.0,
            menorIntervaloRepasse=passagemRapida.menorIntervalo if passagemRapida else None,
        )

    @staticmethod
    def _construirPontoArticulacao(
        grafo: Grafo,
        conta: Conta,
        numComponentes: int,
        centralidade: float,
        grauEntrada: int,
        grauSaida: int,
    ) -> PontoArticulacao:
        entradas = grafo.entradas(conta)
        saidas = grafo.saidas(conta)
        lavagemEntrada = sum(1 for t in entradas if t.origem != conta and t.rotuloLavagem)
        lavagemSaida = sum(1 for t in saidas if t.rotuloLavagem)

        return PontoArticulacao(
            conta=conta,
            numComponentesAoRemover=numComponentes,
            grauEntrada=grauEntrada,
            grauSaida=grauSaida,
            centralidade=centralidade,
            numRotuladasLavagem=lavagemEntrada + lavagemSaida,
        )

    @staticmethod
    def _construirPontesFluxo(
        grafo: Grafo,
        pontesBrutas: list[tuple[Conta, Conta, int, int]],
    ) -> list[PonteFluxo]:
        """Agrega transações de todas as pontes em uma única passada por conta."""
        if not pontesBrutas:
            return []

        alvosPorOrigem: dict[Conta, set[Conta]] = {}
        for contaA, contaB, _, _ in pontesBrutas:
            alvosPorOrigem.setdefault(contaA, set()).add(contaB)
            alvosPorOrigem.setdefault(contaB, set()).add(contaA)

        # statsDir[(u, v)] = [numTransacoes, valorTotal, numRotuladasLavagem, valoresPorMoeda]
        statsDir: dict[tuple[Conta, Conta], list] = {}
        for origem, destinos in alvosPorOrigem.items():
            for transacao in grafo.saidas(origem):
                destino = transacao.destino
                if destino in destinos:
                    par = (origem, destino)
                    moeda = transacao.moeda
                    acc = statsDir.get(par)
                    if acc is None:
                        statsDir[par] = [
                            1,
                            transacao.valor,
                            1 if transacao.rotuloLavagem else 0,
                            {moeda: transacao.valor},
                        ]
                    else:
                        acc[0] += 1
                        acc[1] += transacao.valor
                        if transacao.rotuloLavagem:
                            acc[2] += 1
                        acc[3][moeda] = acc[3].get(moeda, 0.0) + transacao.valor

        resultado: list[PonteFluxo] = []
        for contaA, contaB, tamanhoLadoA, tamanhoLadoB in pontesBrutas:
            ida = statsDir.get((contaA, contaB))
            volta = statsDir.get((contaB, contaA))

            if ida and volta:
                direcional = "<->"
            elif ida:
                direcional = "->"
            else:
                direcional = "<-"

            valoresPorMoeda: dict[str, float] = {}
            for lado in (ida, volta):
                if lado is None:
                    continue
                for moeda, valor in lado[3].items():
                    valoresPorMoeda[moeda] = valoresPorMoeda.get(moeda, 0.0) + valor

            resultado.append(
                PonteFluxo(
                    contaA=contaA,
                    contaB=contaB,
                    tamanhoLadoA=tamanhoLadoA,
                    tamanhoLadoB=tamanhoLadoB,
                    numTransacoes=(ida[0] if ida else 0) + (volta[0] if volta else 0),
                    valorTotal=(ida[1] if ida else 0.0) + (volta[1] if volta else 0.0),
                    valoresPorMoeda=valoresPorMoeda,
                    numRotuladasLavagem=(ida[2] if ida else 0) + (volta[2] if volta else 0),
                    direcional=direcional,
                )
            )
        return resultado
