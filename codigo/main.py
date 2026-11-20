import time
from entrada_saida.LeitorDados import LeitorDados
from grafo.DetectorCiclos import DetectorCiclos
from grafo.AnaliseGrau import analisar_graus_contas  # Importação da sua parte 

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

# -------------------------------------------#
#          Análise de Grau                   #
# -------------------------------------------#
    print("\n-------------------------------------------")
    print("Executando Análise de Grau (Fan-In / Fan-Out)...")
    inicio_grau = time.time()
    
    # Limite pode ser ajustado conforme aensibilidade desejada para a base da IBM
    resultados_grau = analisar_graus_contas(grafo, limite_fan_in=20, limite_fan_out=20)
    
    print(f"Análise de grau concluída em {time.time() - inicio_grau:.1f}s")
    print(f"Contas Fan-In atípicas identificadas: {len(resultados_grau['fan_in']):,}")
    print(f"Contas Fan-Out atípicas identificadas: {len(resultados_grau['fan_out']):,}")
    
    # Exibe alguns exemplos se houver contas atípicas encontradas
    if resultados_grau['fan_in']:
        ex_fan_in = list(resultados_grau['fan_in'].items())[:3]
        print(f"  Exemplos Fan-In (Entradas elevadas): {ex_fan_in}")
        
    if resultados_grau['fan_out']:
        ex_fan_out = list(resultados_grau['fan_out'].items())[:3]
        print(f"  Exemplos Fan-Out (Saídas elevadas): {ex_fan_out}")


if __name__ == "__main__":
    main()