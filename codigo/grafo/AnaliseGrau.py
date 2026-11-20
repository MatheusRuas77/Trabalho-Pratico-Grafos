def analisar_graus_contas(grafo, limite_fan_in=20, limite_fan_out=20):
    """
    Calcula o grau de entrada (Fan-In) e o grau de saída (Fan-Out) de cada conta
    utilizando a estrutura de objetos do multigrafo.
    """
    in_degree = {}
    out_degree = {}
    
    # Inicializa os contadores para todas as contas conhecidas no grafo
    for conta in grafo.contas():
        id_conta = conta.id()
        in_degree[id_conta] = 0
        out_degree[id_conta] = 0

    # Percorre as adjacências do grafo
    for origem_conta, arestas in grafo.adjacencia.items():
        id_origem = origem_conta.id() if hasattr(origem_conta, 'id') else str(origem_conta)
        
        for aresta in arestas:
            # Identifica o destino dependendo se a aresta é um objeto Transacao ou dicionário
            if hasattr(aresta, 'destino'):
                destino_conta = aresta.destino
            elif isinstance(aresta, dict) and 'destino' in aresta:
                destino_conta = aresta['destino']
            else:
                continue
                
            id_destino = destino_conta.id() if hasattr(destino_conta, 'id') else str(destino_conta)
            
            # Incrementa o grau de saída da origem
            out_degree[id_origem] = out_degree.get(id_origem, 0) + 1
            
            # Incrementa o grau de entrada do destino
            if id_destino not in in_degree:
                in_degree[id_destino] = 0
            in_degree[id_destino] += 1
            if id_destino not in out_degree:
                out_degree[id_destino] = 0

    # Identificação de contas atípicas (Fan-In e Fan-Out)
    contas_fan_in = {conta: grau for conta, grau in in_degree.items() if grau >= limite_fan_in}
    contas_fan_out = {conta: grau for conta, grau in out_degree.items() if grau >= limite_fan_out}

    return {
        "in_degree": in_degree,
        "out_degree": out_degree,
        "fan_in": contas_fan_in,
        "fan_out": contas_fan_out
    }