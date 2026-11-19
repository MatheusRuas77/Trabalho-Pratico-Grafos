import time
from entrada_saida.LeitorDados import LeitorDados
from grafo.DetectorCiclos import DetectorCiclos

def main():
    leitor = LeitorDados()
    transacoes = leitor.carregarTransacoes("dados/HI-Small_Trans.csv", limite=0)
    grafo = leitor.construirGrafo(transacoes)

    print(f"Transações carregadas: {len(transacoes):,}")
    print(f"Vértices: {grafo.numVertices():,}")
    print(f"Arestas: {grafo.numArestas():,}")

    if grafo.contas():
        conta = grafo.contas()[0]
        print(f"Conta de exemplo: {conta.id()}")
        print(f"Grau de entrada: {grafo.grauEntrada(conta)}")
        print(f"Grau de saída: {grafo.grauSaida(conta)}")

# -------------------------------------------#
#             Detector de ciclos             #
# -------------------------------------------#
    detector = DetectorCiclos(tamanhoMin=2, tamanhoMax=6, ordemTemporal=True)
    inicio = time.time()
    ciclos = detector.detectar(grafo)
    print(f"\nCiclos encontrados: {len(ciclos):,} ({time.time() - inicio:.1f}s)")

    rotulados = sum(1 for c in ciclos if c.possuiRotuloLavagem())
    print(f"Ciclos com ao menos uma transação rotulada como lavagem: {rotulados:,}")

    for ciclo in ciclos[:5]:
        print(f"  [{ciclo.tamanho()} contas] {ciclo}")


if __name__ == "__main__":
    main()