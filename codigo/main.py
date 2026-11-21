import time
from entrada_saida.LeitorDados import LeitorDados
from grafo.DetectorCiclos import DetectorCiclos
from grafo.DetectorComponentes import DetectorComponentes
from grafo.DetectorCentralidade import DetectorCentralidade
from grafo.AnaliseGrau import analisar_graus_contas  # Importação da sua parte 

def formatar_inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")

def formatar_valores_moeda(valores_por_moeda: dict[str, float]) -> str:
    if not valores_por_moeda:
        return "0,00"
    partes = []
    for moeda, valor in sorted(valores_por_moeda.items(), key=lambda item: item[1], reverse=True):
        valor_fmt = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        partes.append(f"{valor_fmt} {moeda}")
    return " + ".join(partes)

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

# -------------------------------------------#
#       Componentes Conexos (Clusters)       #
# -------------------------------------------#
    tamanhoMin = 2
    componentes = DetectorComponentes(tamanhoMin=tamanhoMin).detectar(grafo)
    print("\n-------------------------------------------")
    print("Componentes conexos da rede")
    for tipo, resumo in (
        ("Componentes fracamente conexos", componentes.fracos),
        ("Componentes fortemente conexos", componentes.fortes),
    ):
        print(f"\n{tipo}")
        print(f"  Total: {formatar_inteiro(resumo.totalComponentes)}")
        print(f"  Com mais de uma conta: {formatar_inteiro(resumo.componentesMulticonta)}")
        print(f"  Maior componente: {formatar_inteiro(resumo.tamanhoMaior)} contas")

        print(f"\n  {'Contas por componente':>21}  {'Quantidade':>10}")
        for tamanho, quantidade in sorted(resumo.distribuicaoPorTamanho.items()):
            print(f"  {formatar_inteiro(tamanho):>21}  {formatar_inteiro(quantidade):>10}")

        print(f"\n  Maiores clusters com pelo menos {tamanhoMin} contas")
        for cluster in resumo.maioresClusters():
            exemplos = ", ".join(cluster.idsContas[:5])
            if cluster.numContas > 5:
                exemplos += ", …"
            proporcao_rotuladas = (
                cluster.numRotuladasLavagem / cluster.numTransacoes
                if cluster.numTransacoes else 0.0
            )
            percentual_rotuladas = f"{proporcao_rotuladas:.2%}".replace(".", ",")
            densidade = f"{cluster.densidade:.4%}".replace(".", ",")
            print(f"\n  Cluster com {formatar_inteiro(cluster.numContas)} contas")
            print(f"    Transações internas: {formatar_inteiro(cluster.numTransacoes)}")
            print(f"    Densidade: {densidade}")
            print(
                f"    Rotuladas como lavagem: {formatar_inteiro(cluster.numRotuladasLavagem)} "
                f"({percentual_rotuladas})"
            )
            print(f"    Exemplos de contas: {exemplos}")

# -------------------------------------------#
#      Centralidade (Contas "Laranjas")      #
# -------------------------------------------#
    print("\n-------------------------------------------")
    print('Executando Análise de Centralidade (Contas "Laranjas")...')
    inicio_cent = time.time()
    detector_cent = DetectorCentralidade(
        amostraFontes=1000,
        profundidadeMax=6,
        tamanhoMinLadoPonte=2,
        limiteResultados=20,
    )
    res_cent = detector_cent.detectar(grafo)
    modo = (
        "exato"
        if res_cent.calculoExato
        else f"amostrado ({formatar_inteiro(res_cent.fontesAmostradas)} fontes)"
    )
    print(f"Análise de centralidade concluída em {time.time() - inicio_cent:.1f}s ({modo})")
    print(f"  Contas com intermediação (> 0): {formatar_inteiro(res_cent.contasComIntermediacao)}")
    print(
        f"  Pontos de articulação (vértices de corte): "
        f"{formatar_inteiro(res_cent.totalPontosArticulacao)}"
    )
    print(
        f"  Pontes estruturais: {formatar_inteiro(res_cent.totalPontes)} "
        f"({formatar_inteiro(res_cent.totalPontesEntreGrupos)} entre grupos com >= 2 contas)"
    )

    if res_cent.intermediarias:
        rotuladas_interm = sum(1 for c in res_cent.intermediarias if c.possuiRotuloLavagem())
        print(
            f"\n  Principais contas intermediárias (laranjas) — "
            f"{rotuladas_interm}/{len(res_cent.intermediarias)} com rótulo de lavagem:"
        )
        for conta_int in res_cent.principaisIntermediarias(5):
            tag_art = " | vértice de corte" if conta_int.ehPontoArticulacao else ""
            tag_lav = (
                f" | lavagem={conta_int.numRotuladasLavagem}"
                if conta_int.possuiRotuloLavagem()
                else ""
            )
            repasse = f"{conta_int.razaoRepasse:.1%}".replace(".", ",")
            moedas = len(conta_int.razaoRepassePorMoeda)
            tag_moedas = f" ({moedas} moedas)" if moedas > 1 else ""
            print(
                f"    {conta_int.idConta} | centralidade={conta_int.centralidade:.6e} "
                f"| in={conta_int.grauEntrada} out={conta_int.grauSaida} "
                f"| repasse={repasse}{tag_moedas}{tag_art}{tag_lav}"
            )

    if res_cent.pontosArticulacao:
        print("\n  Principais pontos de articulação (gargalos da rede):")
        for art in res_cent.principaisArticulacoes(5):
            tag_lav = (
                f" | lavagem={art.numRotuladasLavagem}"
                if art.possuiRotuloLavagem()
                else ""
            )
            print(
                f"    {art.idConta} | fragmenta em {formatar_inteiro(art.numComponentesAoRemover)} componentes "
                f"| in={art.grauEntrada} out={art.grauSaida} "
                f"| centralidade={art.centralidade:.6e}{tag_lav}"
            )

    if res_cent.pontes:
        rotuladas_pontes = sum(1 for p in res_cent.pontes if p.possuiRotuloLavagem())
        print(
            f"\n  Principais pontes nos fluxos financeiros — "
            f"{rotuladas_pontes}/{len(res_cent.pontes)} com rótulo de lavagem:"
        )
        for ponte in res_cent.principaisPontes(5):
            tag_lav = (
                f" | lavagem={ponte.numRotuladasLavagem}"
                if ponte.possuiRotuloLavagem()
                else ""
            )
            valores_fmt = formatar_valores_moeda(ponte.valoresPorMoeda)
            print(
                f"    {ponte} | lados=({formatar_inteiro(ponte.tamanhoLadoA)}, "
                f"{formatar_inteiro(ponte.tamanhoLadoB)}) "
                f"| tx={formatar_inteiro(ponte.numTransacoes)} "
                f"| valor={valores_fmt}{tag_lav}"
            )


if __name__ == "__main__":
    main()
