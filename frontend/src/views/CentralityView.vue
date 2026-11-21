<script setup>
import { ref, watch } from 'vue'
import { Info } from 'lucide-vue-next'
import GraphView from '../components/GraphView.vue'
import InterpretationNote from '../components/InterpretationNote.vue'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import Pagination from '../components/Pagination.vue'
import { url, useApi, useResultadoEmCalculo } from '../services/api'
import { num, score } from '../services/format'

const selecionada = ref('')
const destaque = ref('')
const pagina = ref(1)
const { dados, carregando, recarregar } = useApi(
  () => url('centralidade', { pagina: pagina.value }),
  0,
  false,
  true,
)
const { dados: rede, carregando: carregandoRede } = useApi(
  () => selecionada.value && url('centralidade/rede', { conta: selecionada.value }),
)
useResultadoEmCalculo(dados, recarregar, (atual) => atual.estado === 'calculando')

function selecionar(id) {
  selecionada.value = id
  destaque.value = id
}
watch(dados, (atual) => {
  selecionar(atual?.estado === 'pronto' ? atual.ranking[0]?.id || '' : '')
})
</script>

<template>
  <div class="page-title flex flex-wrap items-start justify-between gap-5">
    <div>
      <h1>{{ $route.meta.titulo }}</h1>
      <p>{{ $route.meta.descricao }}</p>
    </div>
    <span class="control">Centralidade de intermediação</span>
  </div>
  <div v-if="dados && !dados.estado" class="api-status" role="status">
    A API em execução está desatualizada. Reinicie o FastAPI deste projeto e tente novamente.
    <button type="button" class="control" @click="recarregar">Tentar novamente</button>
  </div>
  <div v-if="dados?.estado === 'calculando'" class="api-status" role="status">
    Calculando a centralidade.
  </div>
  <div v-if="dados?.estado === 'erro'" class="api-status" role="status">
    O cálculo da centralidade falhou.
  </div>
  <div
    v-if="(carregando && !dados) || dados?.estado === 'calculando'"
    class="split-panel with-aside"
  >
    <LoadingSkeleton tipo="grafo" />
    <LoadingSkeleton tipo="lista" />
  </div>
  <template v-if="dados?.estado === 'pronto'">
    <InterpretationNote>
      Contas com alta centralidade conectam diferentes regiões da rede e podem atuar como
      intermediárias.
      <template v-if="dados.modo?.exata">
        A busca partiu de todas as contas com ligações de saída.
      </template>
      <template v-if="dados.modo?.profundidade">
        A busca percorre até {{ num(dados.modo.profundidade) }} transferências por caminho.
      </template>
    </InterpretationNote>
    <section class="split-panel with-aside">
      <div class="min-w-0">
        <div class="map-header flex flex-wrap justify-between gap-3">
          <div>
            <div class="eyebrow">Mapa de centralidade</div>
            <h3>Intermediários da rede</h3>
          </div>
          <small class="scale">Menor <i></i><i></i><i></i> Maior</small>
        </div>
        <LoadingSkeleton v-if="carregandoRede && !rede" tipo="grafo" />
        <GraphView
          v-if="rede"
          :rede="rede"
          :selecionadas="[destaque]"
          :pontuacoes="rede.pontuacoes"
          :altura="625"
          disposicao="breadthfirst"
          controles
          rotulos
          @conta="destaque = $event"
        />
      </div>
      <aside class="panel-aside ranking">
        <div class="eyebrow">Ranking</div>
        <h3>Contas mais relevantes</h3>
        <button
          v-for="(conta, i) in dados.ranking"
          :key="conta.id"
          :class="{ chosen: selecionada === conta.id }"
          @click="selecionar(conta.id)"
        >
          <span class="rank-number">{{ (pagina - 1) * 6 + i + 1 }}</span>
          <span
            ><b>{{ conta.id }}</b
            ><small>Intermediação normalizada</small></span
          >
          <span class="mono ml-auto">{{ score(conta.valor) }}</span>
        </button>
        <Pagination v-model="pagina" :paginas="dados.paginas" />
      </aside>
    </section>
    <p v-if="dados.modo && !dados.modo.exata" class="info-line mt-7">
      <Info :size="15" aria-hidden="true" />
      Para estimar o ranking na rede de {{ num(dados.modo.contas) }} contas, o algoritmo
      sorteou {{ num(dados.modo.fontes) }} contas que enviaram transferências e usou cada uma
      como ponto de partida. Outras contas também podem pontuar se aparecerem como
      intermediárias nos caminhos encontrados.
    </p>
  </template>
</template>

<style scoped>
.map-header {
  padding: 24px 22px 19px;
}

.map-header h3,
.ranking h3 {
  margin-top: 10px;
}

.scale {
  white-space: nowrap;
}

.scale i {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #86a99b;
  margin: 0 2px;
  vertical-align: middle;
}

.scale i:nth-child(2) {
  width: 8px;
  height: 8px;
}

.scale i:nth-child(3) {
  width: 11px;
  height: 11px;
}

.ranking > button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 19px 8px;
  min-height: 79px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  font-size: 13px;
}

.ranking > button small {
  display: block;
  font-size: 10px;
  margin-top: 4px;
}

.ranking > button .mono {
  color: var(--blue);
}

.rank-number {
  flex: 0 0 29px;
  height: 29px;
  border-radius: 50%;
  background: #e9eef2;
  color: var(--blue);
  display: grid;
  place-items: center;
  font-size: 11px;
}

.ranking > button.chosen,
.ranking > button:hover {
  background: var(--selected);
}
</style>
