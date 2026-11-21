<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import { use, init } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import DetailDialog from '../components/DetailDialog.vue'
import Pagination from '../components/Pagination.vue'
import GraphView from '../components/GraphView.vue'
import InterpretationNote from '../components/InterpretationNote.vue'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import { url, useApi } from '../services/api'
import { codigo, num, pct } from '../services/format'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const tipo = ref('fracos')
const outroTipo = computed(() => (tipo.value === 'fracos' ? 'fortes' : 'fracos'))
const ordem = ref('contas')
const minimoInformado = ref(1)
const ocultarUnitarios = ref(false)
const minimoVertices = computed(() => {
  const minimo = minimoInformado.value
  return Number.isSafeInteger(minimo) && minimo > 0 ? minimo : 1
})
const pagina = ref(1)
const paginaContas = ref(1)
const selecionado = ref(null)
const totais = ref({})

const { dados, carregando } = useApi(() => {
  return url('componentes/' + tipo.value, {
    ordem: ordem.value,
    pagina: pagina.value,
    minimo_vertices: minimoVertices.value,
    ocultar_unitarios: ocultarUnitarios.value,
  })
})

const { dados: outraParticao } = useApi(() => url('componentes/' + outroTipo.value))

const {
  dados: cluster,
  erro: erroCluster,
  carregando: carregandoCluster,
  recarregar: recarregarCluster,
} = useApi(urlCluster, 0, true)

const {
  dados: contasCluster,
  erro: erroContas,
  carregando: carregandoContas,
  recarregar: recarregarContas,
} = useApi(
  () => {
    if (!selecionado.value) return null

    return url(caminhoCluster() + '/contas', { pagina: paginaContas.value })
  },
  0,
  true,
)

function caminhoCluster() {
  return 'componentes/' + tipo.value + '/' + selecionado.value.id
}

function urlCluster() {
  return selecionado.value ? url(caminhoCluster()) : null
}

watch([tipo, ordem, minimoVertices, ocultarUnitarios], () => {
  pagina.value = 1
})

watch(selecionado, () => {
  paginaContas.value = 1
})

watch(dados, (atual) => {
  if (atual) {
    totais.value[tipo.value] = atual.total
  }
})

watch(outraParticao, (atual) => {
  if (atual) {
    totais.value[outroTipo.value] = atual.total
  }
})

function taxa(linha) {
  if (!linha.transacoes) return 0

  return linha.rotuladas / linha.transacoes
}

const metricas = computed(() => {
  if (!dados.value) return []

  const { total, multiconta, maior } = dados.value
  const proporcaoMulticonta = total ? multiconta / total : 0

  return [
    ['Total de componentes', total, 'Em toda a rede analisada'],
    ['Com mais de uma conta', multiconta, pct(proporcaoMulticonta) + ' dos componentes'],
    ['Maior componente', maior, 'contas conectadas'],
  ]
})

const grafico = ref()
let chart
let observer

function desenhar() {
  const limitesDasFaixas = [1, 2, 5, 10, 20, 50]
  const componentesPorFaixa = limitesDasFaixas.map(() => 0)

  for (const [tamanho, quantidade] of Object.entries(dados.value.distribuicao)) {
    const faixa = limitesDasFaixas.findLastIndex((inicio) => Number(tamanho) >= inicio)
    componentesPorFaixa[faixa] += quantidade
  }

  chart?.setOption({
    grid: {
      top: 5,
      right: 0,
      bottom: 17,
      left: 0,
    },
    tooltip: {
      trigger: 'axis',
      valueFormatter: num,
    },
    xAxis: {
      type: 'category',
      data: ['1 conta', '2–4', '5–9', '10–19', '20–49', '50+ contas'],
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: {
        color: '#75869a',
        fontSize: 9,
        interval: 0,
        hideOverlap: true,
      },
    },
    yAxis: {
      type: 'value',
      show: false,
    },
    series: [
      {
        name: 'Componentes',
        type: 'bar',
        data: componentesPorFaixa,
        itemStyle: {
          color: '#9aafc6',
          borderRadius: [2, 2, 0, 0],
        },
        barWidth: '88%',
      },
    ],
  })
}

watch(grafico, montarGrafico, { flush: 'post' })

function montarGrafico(elemento) {
  liberarGrafico()
  if (!elemento) return

  chart = init(elemento)
  desenhar()

  observer = new ResizeObserver(() => chart.resize())
  observer.observe(elemento)
}

function liberarGrafico() {
  observer?.disconnect()
  chart?.dispose()
  observer = null
  chart = null
}

onBeforeUnmount(liberarGrafico)
</script>

<template>
  <div class="page-title">
    <h1>{{ $route.meta.titulo }}</h1>
    <p>{{ $route.meta.descricao }}</p>
  </div>
  <div class="partition-tabs flex flex-wrap" aria-label="Tipos de componentes">
    <button
      v-for="(label, chave) in {
        fracos: 'Componentes fracamente conexos',
        fortes: 'Componentes fortemente conexos',
      }"
      :key="chave"
      :class="{ active: tipo === chave }"
      :aria-pressed="tipo === chave"
      @click="tipo = chave"
    >
      {{ label }} <span class="pill">{{ num(totais[chave]) }}</span>
    </button>
  </div>
  <template v-if="carregando && !dados">
    <LoadingSkeleton tipo="metricas" class="my-6" />
  </template>
  <template v-else-if="dados">
    <InterpretationNote class="mt-6">
      A densidade indica a proporção de conexões direcionadas existentes em relação às
      possíveis.
    </InterpretationNote>
    <section class="partition-metrics">
      <div v-for="[label, quantidade, detalhe] in metricas" :key="label">
        <span>{{ label }}</span><strong>{{ num(quantidade) }}</strong
        ><small>{{ detalhe }}</small>
      </div>
      <div>
        <div class="eyebrow mb-3">Distribuição por tamanho</div>
        <div
          ref="grafico"
          class="h-[82px] w-full"
          role="img"
          aria-label="Distribuição de componentes por número de contas"
        ></div>
      </div>
    </section>
  </template>
  <div class="table-toolbar cluster-toolbar flex flex-wrap items-start justify-between gap-4">
    <div>
      <div class="eyebrow">Maiores componentes</div>
      <h3>Clusters identificados</h3>
    </div>
    <div class="flex flex-wrap items-center gap-3">
      <label class="flex items-center gap-2">
        <span>Mínimo de vértices</span>
        <input
          v-model.lazy.number="minimoInformado"
          class="control w-20"
          type="number"
          min="1"
        />
      </label>
      <label class="flex items-center gap-2">
        <input v-model="ocultarUnitarios" type="checkbox" />
        <span>Ocultar componentes unitários</span>
      </label>
      <label class="flex items-center gap-3">
        <span>Ordenar por</span>
        <select v-model="ordem">
          <option value="contas">Tamanho</option>
          <option value="transacoes">Transações</option>
          <option value="densidade">Densidade</option>
          <option value="rotuladas">Rotuladas</option>
        </select>
      </label>
    </div>
  </div>
  <LoadingSkeleton v-if="carregando && !dados" />
  <template v-else-if="dados">
    <div class="table-wrap">
      <table class="cluster-table">
        <thead>
          <tr>
            <th>Cluster</th>
            <th>Contas</th>
            <th>Transações internas</th>
            <th>Densidade</th>
            <th>Rotuladas</th>
            <th>% rotuladas</th>
            <th><span class="sr-only">Detalhes</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(linha, i) in dados.linhas"
            :key="linha.id"
            :class="{ chosen: i === 0 }"
            @click="selecionado = linha"
          >
            <td class="mono"><i class="cluster-dot"></i>{{ codigo('CL', linha.id) }}</td>
            <td>{{ num(linha.contas) }}</td>
            <td>{{ num(linha.transacoes) }}</td>
            <td>
              <span class="density-bar"
                ><i :style="{ width: linha.densidade * 100 + '%' }"></i></span
              >{{ pct(linha.densidade) }}
            </td>
            <td>{{ num(linha.rotuladas) }}</td>
            <td>
              <span class="pill">{{ pct(taxa(linha)) }}</span>
            </td>
            <td>
              <button
                class="text-link"
                :aria-label="'Visualizar ' + codigo('CL', linha.id)"
                @click.stop="selecionado = linha"
              >
                Visualizar <ChevronRight :size="15" />
              </button>
            </td>
          </tr>
          <tr v-if="!dados.linhas.length">
            <td colspan="7">Nenhum componente atende aos filtros selecionados.</td>
          </tr>
        </tbody>
      </table>
    </div>
    <Pagination v-model="pagina" :paginas="dados.paginas" />
  </template>
  <DetailDialog
    v-if="selecionado"
    amplo
    :titulo="codigo('CL', selecionado.id)"
    legenda="Componente selecionado"
    descricao="Contas e conexões internas do componente."
    @fechar="selecionado = null"
  >
    <div class="dialog-metrics compact grid grid-cols-4">
      <div>
        <small>Contas</small><strong>{{ num(selecionado.contas) }}</strong>
      </div>
      <div>
        <small>Transações internas</small><strong>{{ num(selecionado.transacoes) }}</strong>
      </div>
      <div>
        <small>Densidade</small><strong>{{ pct(selecionado.densidade) }}</strong>
      </div>
      <div>
        <small>Transações rotuladas</small
        ><strong
          >{{ num(selecionado.rotuladas) }}
          <small>({{ pct(taxa(selecionado)) }})</small></strong
        >
      </div>
    </div>
    <div v-if="erroCluster" class="api-status" role="status">
      <span>{{ erroCluster }}</span>
      <button v-if="erroCluster" class="control" @click="recarregarCluster">
        Tentar novamente
      </button>
    </div>
    <LoadingSkeleton v-if="carregandoCluster && !cluster" tipo="grafo" />
    <div v-if="cluster" class="split-panel with-aside dialog-split">
      <GraphView
        :rede="cluster.rede"
        :altura="485"
        disposicao="breadthfirst"
        controles
        interativo
      />
      <aside class="panel-aside">
        <h4>Contas nesta página</h4>
        <LoadingSkeleton v-if="carregandoContas" tipo="lista" class="mt-3" />
        <div v-else-if="erroContas" class="mt-3" role="status">
          <p>{{ erroContas }}</p>
          <button class="control mt-2" @click="recarregarContas">Tentar novamente</button>
        </div>
        <template v-else-if="contasCluster">
          <ul class="cluster-accounts">
            <li v-for="conta in contasCluster.linhas" :key="conta.id">
              <b>{{ conta.id }}</b>
              <small>{{ num(conta.entrada) }} entradas · {{ num(conta.saida) }} saídas</small>
            </li>
          </ul>
          <Pagination v-model="paginaContas" :paginas="contasCluster.paginas" />
          <small
            >Exibindo {{ num(contasCluster.linhas.length) }} de
            {{ num(cluster.contas) }} contas</small
          >
        </template>
      </aside>
    </div>
  </DetailDialog>
</template>

<style scoped>
.cluster-table td {
  height: 50px;
}

.density-bar {
  display: inline-flex;
  width: 80px;
  height: 4px;
  vertical-align: middle;
  margin-right: 8px;
}

.partition-tabs {
  border-bottom: 1px solid var(--border);
}

.partition-tabs button {
  border-bottom: 2px solid transparent;
  padding: 10px 22px 14px;
  color: var(--muted);
  font-size: 13px;
}

.partition-tabs button.active {
  color: #3d6694;
  border-color: #527aaf;
}

.partition-tabs .pill {
  margin-left: 8px;
}

.partition-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr) 1.35fr;
  margin-top: 24px;
  border-bottom: 1px solid var(--border);
}

.partition-metrics > div {
  padding: 17px 22px;
  min-height: 141px;
  color: var(--muted);
  font-size: 13px;
}

.partition-metrics > div + div {
  border-left: 1px solid var(--border);
}

.partition-metrics strong {
  display: block;
  color: var(--ink);
  margin-top: 16px;
  font-size: 29px;
  font-weight: 620;
}

.cluster-toolbar h3 {
  margin-top: 9px;
}

.cluster-dot {
  display: inline-block;
  border-radius: 50%;
  width: 9px;
  height: 9px;
  background: #87aa9b;
  border: 0;
  margin-right: 9px;
}

.chosen .cluster-dot {
  background: #7893b4;
}

.dialog-split {
  border: 0;
  grid-template-columns: minmax(0, 1fr) minmax(235px, 23%) !important;
}

.cluster-accounts {
  margin: 12px 0 17px;
}

.cluster-accounts li {
  border-bottom: 1px solid var(--border);
  padding: 14px 0;
  font-size: 12px;
}

.density-bar {
  background: #e9edf0;
}

.density-bar i {
  background: #7893b4;
}

.cluster-table .chosen {
  background: var(--selected);
}

.cluster-accounts small {
  display: block;
  font-size: 10px;
}

@media (max-width: 900px) {
  .partition-metrics {
    grid-template-columns: repeat(3, 1fr);
  }

  .partition-metrics > div:last-child {
    grid-column: 1 / -1;
    padding-top: 14px;
    border-left: none;
  }

  .dialog-split {
    grid-template-columns: minmax(0, 1fr) !important;
  }
}

@media (max-width: 560px) {
  .partition-metrics strong {
    font-size: 22px;
  }

  .partition-metrics > div {
    padding-inline: 9px;
  }

  .partition-tabs button {
    padding-inline: 6px;
  }
}
</style>
