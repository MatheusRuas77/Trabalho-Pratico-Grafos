"""API REST para explorar a base HI-Small com os algoritmos do trabalho."""

import csv
import logging
import os
from collections import Counter, deque
from contextlib import asynccontextmanager
from functools import cached_property
from pathlib import Path
from threading import Lock, Thread
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from entrada_saida.LeitorDados import LeitorDados
from grafo.AnaliseGrau import analisar_graus_contas
from grafo.DetectorCentralidade import DetectorCentralidade
from grafo.DetectorCiclos import DetectorCiclos
from grafo.DetectorComponentes import DetectorComponentes

DADOS = Path(__file__).resolve().parents[1] / "dados"
TOTAL_TRANSACOES_HI_SMALL = 5_078_345
LIMITE_INICIAL = TOTAL_TRANSACOES_HI_SMALL * 5 // 100
logger = logging.getLogger(__name__)


@asynccontextmanager
async def preparar_base(_app):
    bases.carregar(int(os.getenv("GRAFOS_LIMITE_TRANSACOES", str(LIMITE_INICIAL))))
    yield


app = FastAPI(title="Análise de redes financeiras", lifespan=preparar_base)


def transferencia(t):
    return {
        "origem": t.origem.id(),
        "destino": t.destino.id(),
        "valor": t.valor,
        "moeda": t.moeda,
        "instante": t.instante.isoformat(),
        "formato": t.formatoPagamento,
        "rotulada": t.rotuloLavagem,
    }


def valores(transacoes):
    totais = Counter()
    for t in transacoes:
        totais[t.moeda] += t.valor
    return dict(totais)


class Base:
    def __init__(self, limite: int = 0):
        self.limite = limite

    @cached_property
    def transacoes(self):
        return LeitorDados().carregarTransacoes(
            DADOS / "HI-Small_Trans.csv", limite=self.limite
        )

    @cached_property
    def grafo(self):
        return LeitorDados().construirGrafo(self.transacoes)

    @cached_property
    def contas(self):
        return {conta.id(): conta for conta in self.grafo.contas()}

    @cached_property
    def metadados(self):
        contas = {(c.banco.lstrip("0"), c.numero): c.id() for c in self.contas.values()}
        resultado = {}
        with (DADOS / "HI-Small_accounts.csv").open(
            encoding="utf-8-sig", newline=""
        ) as arquivo:
            for linha in csv.DictReader(arquivo):
                conta = contas.get((linha["Bank ID"].lstrip("0"), linha["Account Number"]))
                if conta:
                    resultado[conta] = linha["Bank Name"]
        return resultado

    @cached_property
    def graus(self):
        graus = analisar_graus_contas(self.grafo)
        return [
            {
                "id": id_,
                "banco": self.metadados.get(id_, conta.banco),
                "entrada": graus["in_degree"][id_],
                "saida": graus["out_degree"][id_],
                "total": graus["in_degree"][id_] + graus["out_degree"][id_],
            }
            for id_, conta in self.contas.items()
        ]

    @cached_property
    def grau_por_conta(self):
        return {linha["id"]: linha for linha in self.graus}

    @cached_property
    def ciclos(self):
        return sorted(
            DetectorCiclos().detectar(self.grafo),
            key=lambda c: c.transacoes[-1].instante,
            reverse=True,
        )

    @cached_property
    def componentes(self):
        resultado = DetectorComponentes().detectar(self.grafo)
        return {
            tipo: (resumo, sorted(resumo.clusters, key=lambda c: c.numContas, reverse=True))
            for tipo, resumo in (("fracos", resultado.fracos), ("fortes", resultado.fortes))
        }

    def vizinhanca(self, sementes, saltos):
        vistos = dict.fromkeys(sementes)
        fila = deque((c, 0) for c in sementes)
        while fila:
            conta, distancia = fila.popleft()
            if distancia >= saltos:
                continue
            vizinhas = (
                (self.grafo.saidas(conta), "destino"),
                (self.grafo.entradas(conta), "origem"),
            )
            for transacoes, atributo in vizinhas:
                for t in transacoes:
                    outra = getattr(t, atributo)
                    if outra not in vistos:
                        vistos[outra] = None
                        fila.append((outra, distancia + 1))
        return vistos

    def incidentes(self, conta):
        yield from self.grafo.entradas(conta)
        yield from (t for t in self.grafo.saidas(conta) if t.destino != conta)

    def internas(self, contas):
        return (t for conta in contas for t in self.grafo.saidas(conta) if t.destino in contas)

    def rede(self, transacoes, pagina=1, sementes=(), prioritarias=(), por_pagina=60):
        inicio = (pagina - 1) * por_pagina
        fim = inicio + por_pagina
        if isinstance(transacoes, list):
            total = len(transacoes)
            janela = transacoes[inicio:fim]
        else:
            janela = []
            total = 0
            for total, t in enumerate(transacoes, 1):
                if inicio < total <= fim:
                    janela.append(t)
        destaques = {id(t) for t in prioritarias}
        contas = dict.fromkeys(sementes)
        for t in janela:
            contas[t.origem] = contas[t.destino] = None
        return {
            "contas": [c.id() for c in contas],
            "transferencias": [
                {**transferencia(t), "destaque": id(t) in destaques} for t in janela
            ],
            "paginas": (total + por_pagina - 1) // por_pagina,
            "totalTransferencias": total,
        }

    def rede_completa(self, transacoes, contas):
        arestas = [transferencia(t) for t in transacoes]
        return {
            "contas": [c.id() for c in contas],
            "transferencias": arestas,
            "totalTransferencias": len(arestas),
        }

    @cached_property
    def lideres(self):
        return {
            campo: max(self.graus, key=lambda c: c[campo], default=None)
            for campo in ("entrada", "saida", "total")
        }

    estado_centralidade = "calculando"
    ranking_centralidade = ()
    pontuacoes_centralidade = {}
    modo_centralidade = None

    def calcular_centralidade(self):
        try:
            detector = DetectorCentralidade()
            resultado = detector.detectar(self.grafo)
            pontuacoes = {
                conta.id(): valor for conta, valor in resultado.centralidades.items()
            }
            self.modo_centralidade = {
                "exata": resultado.calculoExato,
                "fontes": resultado.fontesAmostradas,
                "contas": resultado.totalContasAnalisadas,
                "profundidade": detector.profundidadeMax,
            }
            self.ranking_centralidade = sorted(pontuacoes, key=lambda c: (-pontuacoes[c], c))
            self.pontuacoes_centralidade = pontuacoes
            self.estado_centralidade = "pronto"
        except Exception:
            logger.exception("Erro no cálculo da centralidade da rede inteira")
            self.estado_centralidade = "erro"

    @cached_property
    def ranking_grau(self):
        return {
            campo: sorted(self.graus, key=lambda c: c[campo], reverse=True)
            for campo in self.lideres
        }

    @cached_property
    def resumo(self):
        ciclos = self.ciclos
        return {
            "contas": len(self.contas),
            "transacoes": len(self.transacoes),
            "rotuladas": sum(t.rotuloLavagem for t in self.transacoes),
            "ciclos": len(ciclos),
            "ciclosLongos": sum(c.tamanho() >= 4 for c in ciclos),
            "grau": self.lideres["total"],
            "fracos": self.componentes["fracos"][0].totalComponentes,
            "fortes": self.componentes["fortes"][0].totalComponentes,
            "maiorFraco": self.componentes["fracos"][0].tamanhoMaior,
        }


class BaseAtiva:
    def __init__(self):
        self._estado = Lock()
        self._processamento = Lock()
        self._base = None
        self._limite = 0
        self._versao = 0
        self._situacao = "pendente"

    def _status(self):
        return {
            "estado": self._situacao,
            "limite": self._limite,
            "versao": self._versao,
            "transacoes": len(self._base.transacoes) if self._base is not None else None,
        }

    def status(self):
        with self._estado:
            return self._status()

    def obter(self):
        with self._estado:
            if self._base is None:
                raise HTTPException(503, "A base de transações ainda não está disponível.")
            return self._base

    def carregar(self, limite):
        if limite < 0:
            raise ValueError("O limite de transações deve ser maior ou igual a zero.")
        with self._estado:
            if self._situacao == "carregando":
                if limite != self._limite:
                    raise HTTPException(409, "Já existe um carregamento em andamento.")
                return self._status()
            if self._base is not None and self._limite == limite:
                return self._status()
            self._limite = limite
            self._situacao = "carregando"
            self._base = None
            Thread(target=self._processar, args=(limite,), daemon=True).start()
            return self._status()

    def _processar(self, limite):
        with self._processamento:
            try:
                nova_base = Base(limite)
                nova_base.resumo
            except Exception:
                logger.exception("Erro ao carregar a base de transações")
                with self._estado:
                    self._situacao = "erro"
                return

            with self._estado:
                self._base = nova_base
                self._versao += 1
                self._situacao = "pronta"
            nova_base.calcular_centralidade()


bases = BaseAtiva()
BaseAtual = Annotated[Base, Depends(bases.obter)]


class ConfiguracaoBase(BaseModel):
    limite: int = Field(ge=0, le=2**53 - 1, strict=True)


@app.get("/api/base")
def consultar_base():
    return bases.status()


@app.put("/api/base")
def atualizar_base(configuracao: ConfiguracaoBase):
    return bases.carregar(configuracao.limite)


def obter_conta(base, id_):
    if id_ not in base.contas:
        raise HTTPException(404, "Conta não encontrada na base analisada.")
    return base.contas[id_]


@app.get("/api/resumo")
def resumo(base: BaseAtual):
    estado = base.estado_centralidade
    lider = next(iter(base.ranking_centralidade), None) if estado == "pronto" else None
    return {
        **base.resumo,
        "estadoCentralidade": estado,
        "modoCentralidade": base.modo_centralidade if estado == "pronto" else None,
        "centralidade": (
            {"id": lider, "valor": base.pontuacoes_centralidade[lider]} if lider else None
        ),
    }


@app.get("/api/rede")
def rede(
    base: BaseAtual,
    conta: str = "",
    saltos: int = Query(0, ge=0),
    pagina: int = Query(1, ge=1),
    diretas: bool = False,
    por_pagina: int = Query(60, ge=1),
):
    centro = obter_conta(base, conta) if conta else None
    if diretas:
        if centro is None:
            raise HTTPException(
                422, "Informe a conta para consultar suas transferências diretas."
            )
        transacoes = base.incidentes(centro)
    elif saltos:
        if centro is None and base.lideres["total"]:
            centro = obter_conta(base, base.lideres["total"]["id"])
        transacoes = base.internas(base.vizinhanca([centro], saltos)) if centro else []
    else:
        transacoes = base.transacoes
    return {
        "selecionada": centro.id() if centro else "",
        **base.rede(transacoes, pagina, [centro] if centro else [], por_pagina=por_pagina),
    }


@app.get("/api/conta")
def conta(base: BaseAtual, id: str, pagina: int = Query(1, ge=1)):
    alvo = obter_conta(base, id)
    ordenadas = sorted(base.incidentes(alvo), key=lambda t: t.instante, reverse=True)
    inicio = (pagina - 1) * 20
    return {
        **base.grau_por_conta[id],
        "valores": valores(ordenadas),
        "primeira": ordenadas[-1].instante.isoformat(),
        "ultima": ordenadas[0].instante.isoformat(),
        "totalTransferencias": len(ordenadas),
        "transferencias": [transferencia(t) for t in ordenadas[inicio : inicio + 20]],
    }


@app.get("/api/graus")
def graus(
    base: BaseAtual,
    pagina: int = Query(1, ge=1),
    ordem: str = Query("total", pattern="^(total|entrada|saida)$"),
):
    inicio = (pagina - 1) * 6
    return {
        "linhas": base.ranking_grau[ordem][inicio : inicio + 6],
        "paginas": (len(base.graus) + 5) // 6,
        "lideres": base.lideres,
    }


@app.get("/api/graus/rede")
def rede_grau(base: BaseAtual, conta: str):
    centro = obter_conta(base, conta)
    contas = {centro: None}
    transacoes = []
    for t in base.incidentes(centro):
        contas[t.origem] = contas[t.destino] = None
        transacoes.append(transferencia(t))

    return {
        "contas": [c.id() for c in contas],
        "transferencias": transacoes,
        "totalTransferencias": len(transacoes),
    }


@app.get("/api/ciclos")
def ciclos(base: BaseAtual, minimo: int = Query(2, ge=2, le=6), pagina: int = Query(1, ge=1)):
    itens = base.ciclos
    filtrados = [(i, c) for i, c in enumerate(itens, 1) if c.tamanho() >= minimo]
    inicio = (pagina - 1) * 12
    return {
        "total": len(itens),
        "limiteBase": base.limite,
        "transacoesAnalisadas": len(base.transacoes),
        "resultados": len(filtrados),
        "paginas": (len(filtrados) + 11) // 12,
        "linhas": [
            {
                "id": i,
                "contas": c.tamanho(),
                "minutos": int(
                    (c.transacoes[-1].instante - c.transacoes[0].instante).total_seconds() / 60
                ),
            }
            for i, c in filtrados[inicio : inicio + 12]
        ],
    }


@app.get("/api/ciclos/{id}")
def ciclo(base: BaseAtual, id: int):
    itens = base.ciclos
    if not 1 <= id <= len(itens):
        raise HTTPException(404, "Ciclo não encontrado.")
    c = itens[id - 1]
    return {
        "contas": [conta.id() for conta in c.contas],
        "valores": valores(c.transacoes),
        "transferencias": [transferencia(t) for t in c.transacoes],
        "rede": base.rede(c.transacoes, sementes=c.contas, prioritarias=c.transacoes),
    }


@app.get("/api/centralidade")
def centralidade(base: BaseAtual, pagina: int = Query(1, ge=1)):
    estado = base.estado_centralidade
    if estado != "pronto":
        return {"estado": estado}
    inicio = (pagina - 1) * 6
    ranking = base.ranking_centralidade[inicio : inicio + 6]
    return {
        "estado": estado,
        "paginas": (len(base.ranking_centralidade) + 5) // 6,
        "modo": base.modo_centralidade,
        "ranking": [
            {"id": id_, "valor": base.pontuacoes_centralidade[id_]} for id_ in ranking
        ],
    }


@app.get("/api/centralidade/rede")
def rede_centralidade(base: BaseAtual, conta: str):
    if base.estado_centralidade != "pronto":
        raise HTTPException(409, "O ranking está sendo calculado.")
    alvo = obter_conta(base, conta)
    vizinhanca = base.vizinhanca([alvo], 1)
    resultado = base.rede_completa(base.internas(vizinhanca), vizinhanca)
    return {
        **resultado,
        "pontuacoes": {c: base.pontuacoes_centralidade[c] for c in resultado["contas"]},
    }


def dados_cluster(id_, cluster):
    return {
        "id": id_,
        "contas": cluster.numContas,
        "transacoes": cluster.numTransacoes,
        "densidade": cluster.densidade,
        "rotuladas": cluster.numRotuladasLavagem,
    }


def particao(base, tipo):
    if tipo not in ("fracos", "fortes"):
        raise HTTPException(404, "Tipo de componente desconhecido.")
    return base.componentes[tipo]


@app.get("/api/componentes/{tipo}")
def componentes(
    base: BaseAtual,
    tipo: str,
    pagina: int = Query(1, ge=1),
    minimo_vertices: int = Query(1, ge=1),
    ocultar_unitarios: bool = False,
    ordem: str = Query("contas", pattern="^(contas|transacoes|densidade|rotuladas)$"),
):
    dados, clusters = particao(base, tipo)
    campos = {
        "contas": "numContas",
        "transacoes": "numTransacoes",
        "densidade": "densidade",
        "rotuladas": "numRotuladasLavagem",
    }
    minimo = max(minimo_vertices, 2) if ocultar_unitarios else minimo_vertices
    filtrados = (
        (id_, cluster)
        for id_, cluster in enumerate(clusters, 1)
        if cluster.numContas >= minimo
    )
    linhas = sorted(filtrados, key=lambda item: getattr(item[1], campos[ordem]), reverse=True)
    inicio = (pagina - 1) * 5
    return {
        "total": dados.totalComponentes,
        "multiconta": dados.componentesMulticonta,
        "maior": dados.tamanhoMaior,
        "distribuicao": dados.distribuicaoPorTamanho,
        "paginas": (len(linhas) + 4) // 5,
        "linhas": [dados_cluster(i, c) for i, c in linhas[inicio : inicio + 5]],
    }


def obter_cluster(base, tipo, id):
    _, clusters = particao(base, tipo)
    if not 1 <= id <= len(clusters):
        raise HTTPException(404, "Componente não encontrado.")
    return clusters[id - 1]


@app.get("/api/componentes/{tipo}/{id}")
def componente(base: BaseAtual, tipo: str, id: int):
    cluster = obter_cluster(base, tipo, id)
    membros = dict.fromkeys(base.contas[c] for c in cluster.idsContas)
    return {
        **dados_cluster(id, cluster),
        "rede": base.rede_completa(base.internas(membros), membros),
    }


@app.get("/api/componentes/{tipo}/{id}/contas")
def contas_componente(base: BaseAtual, tipo: str, id: int, pagina: int = Query(1, ge=1)):
    cluster = obter_cluster(base, tipo, id)
    inicio = (pagina - 1) * 5
    return {
        "paginas": (cluster.numContas + 4) // 5,
        "linhas": [base.grau_por_conta[c] for c in cluster.idsContas[inicio : inicio + 5]],
    }
