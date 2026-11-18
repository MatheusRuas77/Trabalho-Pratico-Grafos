from entrada_saida.LeitorDados import LeitorDados

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

if __name__ == "__main__":
    main()
