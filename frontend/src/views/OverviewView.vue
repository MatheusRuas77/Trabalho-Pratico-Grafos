<script setup>
import { computed } from 'vue'
import {
  ChartNoAxesColumnIncreasing,
  ChevronRight,
  RotateCw,
  Target,
  Waypoints,
} from 'lucide-vue-next'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import { url, useApi, useResultadoEmCalculo } from '../services/api'
import { num, score } from '../services/format'

const {
  dados: resumo,
  carregando: carregandoResumo,
  recarregar,
} = useApi(() => url('resumo'), 0, false, true)
useResultadoEmCalculo(resumo, recarregar, (r) => r.estadoCentralidade === 'calculando')
const cards = computed(() => {
  const r = resumo.value
  return [
    {
      link: '/ciclos',
      icon: RotateCw,
      label: 'Ciclos direcionados',
      valor: num(r?.ciclos),
      detalhe: r && num(r.ciclosLongos) + ' ciclos encontrados envolvem quatro ou mais contas',
    },
    {
      link: '/grau',
      icon: ChartNoAxesColumnIncreasing,
      label: 'Maior grau total',
      valor: num(r?.grau?.total),
      detalhe:
        r?.grau &&
        r.grau.id +
          ' · ' +
          num(r.grau.entrada) +
          ' entradas e ' +
          num(r.grau.saida) +
          ' saídas',
    },
    {
      link: '/centralidade',
      icon: Target,
      label: 'Maior centralidade',
      valor:
        { calculando: 'Calculando…', erro: 'Indisponível' }[r?.estadoCentralidade] ||
        score(r?.centralidade?.valor),
      detalhe:
        r?.centralidade &&
        r.centralidade.id +
          (r.modoCentralidade && !r.modoCentralidade.exata
            ? ' · centralidade de intermediação estimada'
            : ' · centralidade de intermediação normalizada'),
    },
    {
      link: '/componentes',
      icon: Waypoints,
      label: 'Componentes conexos',
      detalhe: r && 'Maior componente fracamente conexo: ' + num(r.maiorFraco) + ' contas',
    },
  ]
})
</script>

<template>
  <div class="page-title">
    <h1>{{ $route.meta.titulo }}</h1>
    <p>{{ $route.meta.descricao }}</p>
  </div>
  <LoadingSkeleton v-if="carregandoResumo && !resumo" tipo="metricas" />
  <section v-else-if="resumo" class="overview-metrics">
    <div>
      <span class="eyebrow">BASE ANALISADA</span><strong>{{ num(resumo?.contas) }}</strong
      ><small>contas</small>
    </div>
    <div>
      <strong>{{ num(resumo?.transacoes) }}</strong><small>transações direcionadas</small>
    </div>
    <div>
      <strong>{{ num(resumo?.rotuladas) }}</strong><small
        >transações previamente rotuladas</small
      >
    </div>
  </section>
  <section v-if="resumo || carregandoResumo" class="overview-results">
    <div class="eyebrow">Resultados dos algoritmos</div>
    <h2>Estrutura da rede</h2>
    <LoadingSkeleton v-if="!resumo" class="mt-5" />
    <div v-else class="overview-cards">
      <RouterLink v-for="card in cards" :key="card.link" :to="card.link" class="overview-card">
        <span class="round-icon"><component :is="card.icon" :size="20" /></span>
        <span>
          <small>{{ card.label }}</small>
          <strong v-if="card.valor">{{ card.valor }}</strong>
          <strong v-else
            >{{ num(resumo?.fracos) }} <small>WCC</small> · {{ num(resumo?.fortes) }}
            <small>SCC</small></strong
          >
          <small>{{ card.detalhe }}</small>
        </span>
        <ChevronRight :size="17" class="card-arrow" />
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.overview-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  align-items: end;
  border-block: 1px solid var(--border);
  padding: 26px 0;
  min-height: 147px;
}

.overview-metrics > div {
  position: relative;
  min-height: 93px;
  display: flex;
  flex-direction: column;
  justify-content: end;
  border-right: 1px solid var(--border);
  padding-left: 35px;
}

.overview-metrics > div:first-child {
  padding-left: 0;
}

.overview-metrics > div:nth-child(3) {
  border-right: none;
}

.overview-metrics .eyebrow {
  position: absolute;
  top: 0;
  font-size: 10px;
  letter-spacing: 0.12em;
}

.overview-metrics strong {
  display: block;
  font-size: 34px;
  font-weight: 570;
  margin-bottom: 4px;
}

.overview-results {
  margin-top: 40px;
}

.overview-results h2 {
  margin-top: 12px;
}

.overview-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  margin-top: 22px;
  border-top: 1px solid var(--border);
}

.overview-card {
  display: grid;
  grid-template-columns: 48px 1fr 16px;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid var(--border);
  padding: 21px 34px 21px 27px;
  min-height: 142px;
}

.overview-card:nth-child(odd) {
  border-right: 1px solid var(--border);
}

.overview-card:hover {
  background: #eef3f8;
}

.round-icon {
  display: grid;
  place-items: center;
  width: 47px;
  height: 47px;
  border-radius: 50%;
  color: var(--blue);
  border: 1px solid #c8d8eb;
}

.overview-card strong {
  display: block;
  font-size: 26px;
  margin: 4px 0;
  font-weight: 560;
}

.overview-card strong small,
.overview-card strong + small {
  font-size: 10px;
}

.card-arrow {
  color: #8498ad;
}

@media (max-width: 1120px) {
  .overview-metrics > div {
    padding-left: 20px;
  }
}

@media (max-width: 560px) {
  .overview-cards {
    grid-template-columns: 1fr;
  }

  .overview-card:nth-child(odd) {
    border-right: none;
  }

  .overview-card {
    min-height: 100px;
    padding: 10px 12px;
  }

  .overview-metrics > div {
    padding-left: 8px;
  }

  .overview-metrics strong {
    font-size: 22px;
  }
}
</style>
