<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronRight, Filter } from 'lucide-vue-next'
import Pagination from '../components/Pagination.vue'
import GraphView from '../components/GraphView.vue'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import { url, useApi } from '../services/api'
import { codigo, duracao, num, valor, volume } from '../services/format'

const filtro = ref(false)
const minimo = ref(2)
const pagina = ref(1)
const selecionado = ref(null)
const { dados: lista, carregando: carregandoLista } = useApi(
  () =>
    url('ciclos', {
      minimo: minimo.value,
      pagina: pagina.value,
    }),
  150,
)
const { dados: ciclo, carregando: carregandoCiclo } = useApi(
  () => selecionado.value && url('ciclos/' + selecionado.value.id),
)
watch(minimo, () => {
  pagina.value = 1
})
watch(lista, (atual) => {
  selecionado.value = atual?.linhas[0] || null
})
const total = computed(() => (lista.value ? num(lista.value.total) : '—'))
</script>

<template>
  <div class="page-title flex flex-wrap items-start justify-between gap-5">
    <div>
      <h1>{{ $route.meta.titulo }}</h1>
      <p>{{ $route.meta.descricao }}</p>
    </div>
    <div class="cycle-counter">
      <strong>{{ total }}</strong><small>ciclos identificados</small>
    </div>
  </div>
  <div class="cycle-layout">
    <aside class="cycle-list">
      <div class="flex items-center gap-2">
        <button
          class="control"
          aria-label="Filtrar por tamanho"
          :aria-expanded="filtro"
          @click="filtro = !filtro"
        >
          <Filter :size="17" />
        </button>
      </div>
      <label v-if="filtro" class="flex items-center justify-between gap-2 mt-3"
        >Mínimo de contas
        <select v-model="minimo">
          <option v-for="n in [2, 3, 4, 5, 6]" :key="n" :value="n">{{ n }}</option>
        </select>
      </label>
      <div class="list-heading">
        <span>Ciclos recentes</span><span>{{ num(lista?.resultados) }} resultados</span>
      </div>
      <LoadingSkeleton v-if="carregandoLista && !lista" tipo="lista" />
      <button
        v-for="item in lista?.linhas"
        :key="item.id"
        class="cycle-item"
        :class="{ chosen: selecionado?.id === item.id }"
        @click="selecionado = item"
      >
        <span class="mono muted">{{ String(item.id).padStart(2, '0') }}</span>
        <span
          ><b>{{ codigo('CIC', item.id) }}</b
          ><small>{{ item.contas }} contas · {{ duracao(item.minutos) }}</small></span
        >
        <ChevronRight :size="17" />
      </button>
      <Pagination v-if="lista" v-model="pagina" :paginas="lista.paginas" />
    </aside>
    <section class="min-w-0">
      <LoadingSkeleton v-if="(carregandoLista || carregandoCiclo) && !ciclo" tipo="grafo" />
      <template v-else-if="selecionado && ciclo">
        <div class="cycle-header flex flex-wrap justify-between gap-4">
          <div>
            <div class="eyebrow">Estrutura do ciclo</div>
            <h3>{{ codigo('CIC', selecionado.id) }}</h3>
          </div>
          <dl class="inline-metrics flex flex-wrap">
            <div>
              <dt>Contas</dt>
              <dd>{{ selecionado.contas }}</dd>
            </div>
            <div>
              <dt>Volume</dt>
              <dd>{{ volume(ciclo.valores) }}</dd>
            </div>
            <div>
              <dt>Duração</dt>
              <dd>{{ duracao(selecionado.minutos) }}</dd>
            </div>
          </dl>
        </div>
        <GraphView :rede="ciclo.rede" :selecionadas="ciclo.contas" />
        <h4 class="mt-6 mb-3">Transferências do ciclo</h4>
        <ol class="cycle-transfers">
          <li v-for="(t, i) in ciclo.transferencias" :key="i">
            <small>{{ i + 1 }}</small><b>{{ t.origem }}</b
            ><span>→</span><b>{{ t.destino }}</b
            ><b>{{ valor(t.valor, t.moeda) }}</b>
          </li>
        </ol>
      </template>
      <div v-else-if="lista && lista.total === 0" class="api-status flex-col items-start">
        <h3>Nenhum ciclo encontrado na base analisada</h3>
        <p v-if="lista.transacoesAnalisadas != null">
          O detector analisou {{ num(lista.transacoesAnalisadas) }} transações em busca de
          ciclos de 2 a 6 contas com transferências em ordem cronológica.
        </p>
        <p v-if="lista.limiteBase">
          Apague o valor de <b>Limite</b> no cabeçalho e saia do campo para analisar a base
          inteira.
        </p>
      </div>
      <div v-else-if="lista && lista.resultados === 0" class="api-status">
        Nenhum ciclo atende ao tamanho mínimo selecionado.
      </div>
    </section>
  </div>
</template>

<style scoped>
.cycle-counter {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px 8px 20px;
  border-left: 2px solid #a4b9d0;
}

.cycle-counter strong {
  font-size: 30px;
  color: #385b84;
}

.cycle-layout {
  display: grid;
  grid-template-columns: minmax(225px, 20%) minmax(0, 1fr);
  gap: 25px;
}

.cycle-list {
  border-right: 1px solid var(--border);
}

.cycle-list > .flex {
  margin-right: 20px;
}

.list-heading {
  display: flex;
  justify-content: space-between;
  padding: 13px 20px 13px 0;
  border-block: 1px solid var(--border);
  margin-top: 17px;
  text-transform: uppercase;
  font-size: 10px;
  color: var(--muted);
}

.cycle-item {
  width: 100%;
  display: grid;
  grid-template-columns: 32px 1fr 16px;
  align-items: center;
  gap: 12px;
  padding: 18px 20px 18px 0;
  min-height: 72px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.cycle-item small {
  display: block;
  margin-top: 4px;
}

.cycle-item.chosen {
  box-shadow: inset 3px 0 #557dad;
}

.cycle-header {
  padding-bottom: 16px;
}

.cycle-header h3 {
  margin-top: 9px;
}

.inline-metrics div {
  border-left: 1px solid var(--border);
  padding: 0 16px;
}

.inline-metrics dt {
  color: var(--muted);
  font-size: 10px;
}

.inline-metrics dd {
  margin-top: 5px;
  font-weight: 650;
}

.cycle-transfers li {
  display: grid;
  grid-template-columns: 22px 1fr 18px 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 14px 4px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.cycle-item.chosen,
.cycle-item:hover {
  background: var(--selected);
}

@media (max-width: 900px) {
  .cycle-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .cycle-list {
    border-right: 0;
  }

  .cycle-list > .flex {
    margin-right: 0;
  }

  .cycle-item {
    min-height: 48px;
    padding-block: 8px;
  }
}
</style>
