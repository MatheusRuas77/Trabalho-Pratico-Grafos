<script setup>
import { ref, watch } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import DetailDialog from '../components/DetailDialog.vue'
import Pagination from '../components/Pagination.vue'
import GraphView from '../components/GraphView.vue'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import { url, useApi } from '../services/api'
import { num } from '../services/format'

const campos = { total: 'Grau total', entrada: 'Grau de entrada', saida: 'Grau de saída' }
const ordem = ref('total')
const pagina = ref(1)
const selecionada = ref(null)
const { dados: graus, carregando: carregandoGraus } = useApi(
  () => url('graus', { ordem: ordem.value, pagina: pagina.value }),
  150,
)
const {
  dados: rede,
  erro: erroRede,
  carregando: carregandoRede,
  recarregar: recarregarRede,
} = useApi(
  () => selecionada.value && url('graus/rede', { conta: selecionada.value.id }),
  0,
  true,
)
watch(ordem, () => {
  pagina.value = 1
})
</script>

<template>
  <div class="page-title">
    <h1>{{ $route.meta.titulo }}</h1>
    <p>{{ $route.meta.descricao }}</p>
  </div>
  <div class="table-toolbar flex flex-wrap items-start justify-between gap-4">
    <div>
      <h3>Contas por conectividade</h3>
      <small>Ordenadas por {{ campos[ordem].toLowerCase() }}.</small>
    </div>
    <div class="flex flex-wrap gap-2">
      <select v-model="ordem" aria-label="Ordenar contas">
        <option v-for="(label, campo) in campos" :key="campo" :value="campo">
          {{ label }}
        </option>
      </select>
    </div>
  </div>
  <LoadingSkeleton v-if="carregandoGraus && !graus" />
  <template v-else-if="graus">
    <div class="table-wrap">
      <table class="degree-table">
        <thead>
          <tr>
            <th>Conta</th>
            <th>Banco</th>
            <th>Grau de entrada</th>
            <th>Grau de saída</th>
            <th>Grau total</th>
            <th>Relação entrada / saída</th>
            <th><span class="sr-only">Detalhes</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="linha in graus.linhas" :key="linha.id" @click="selecionada = linha">
            <td class="mono">{{ linha.id }}</td>
            <td>{{ linha.banco }}</td>
            <td>{{ num(linha.entrada) }}</td>
            <td>{{ num(linha.saida) }}</td>
            <td>
              <b>{{ num(linha.total) }}</b>
            </td>
            <td>
              <div
                class="ratio"
                role="img"
                :aria-label="linha.entrada + ' entradas e ' + linha.saida + ' saídas'"
              >
                <span
                  :style="{
                    width: (80 * linha.entrada) / (graus.lideres.total?.total || 1) + '%',
                  }"
                ></span
                ><span
                  :style="{
                    width: (80 * linha.saida) / (graus.lideres.total?.total || 1) + '%',
                  }"
                ></span>
              </div>
            </td>
            <td>
              <button
                class="row-button"
                :aria-label="'Detalhar conta ' + linha.id"
                @click.stop="selecionada = linha"
              >
                <ChevronRight :size="16" />
              </button>
            </td>
          </tr>
          <tr v-if="!graus.linhas.length">
            <td colspan="7">Nenhuma conta encontrada.</td>
          </tr>
        </tbody>
      </table>
    </div>
    <Pagination v-model="pagina" :paginas="graus.paginas" />
    <div class="table-foot flex flex-wrap gap-x-10 gap-y-3">
      <small v-for="campo in ['entrada', 'saida']" :key="campo"
        ><b>Maior grau de {{ campo === 'saida' ? 'saída' : campo }}</b
        >　{{ graus.lideres[campo]?.id }} ·
        {{ num(graus.lideres[campo]?.[campo]) }} conexões</small
      >
    </div>
  </template>
  <DetailDialog
    v-if="selecionada"
    class="degree-dialog"
    :titulo="selecionada.id"
    legenda="Detalhamento de conectividade"
    :descricao="selecionada.banco + ' · conexões direcionadas da conta'"
    @fechar="selecionada = null"
  >
    <div class="dialog-metrics grid grid-cols-3">
      <div v-for="campo in ['entrada', 'saida', 'total']" :key="campo">
        <small>{{ campos[campo] }}</small><strong>{{ num(selecionada[campo]) }}</strong
        ><small>{{
          {
            entrada: 'transferências recebidas',
            saida: 'transferências enviadas',
            total: 'transferências incidentes na conta',
          }[campo]
        }}</small>
      </div>
    </div>
    <div class="dialog-section flex flex-wrap items-end justify-between gap-2">
      <div>
        <h4>Vizinhança da conta</h4>
        <small
          >Cada linha representa uma transferência direta. Clique em uma linha para ver seus
          dados.</small
        >
      </div>
      <small
        ><i class="edge-line entrada"></i> Entrada　
        <i class="edge-line saida"></i> Saída</small
      >
    </div>
    <div v-if="erroRede" class="api-status" role="status">
      <span>{{ erroRede }}</span>
      <button v-if="erroRede" class="control" @click="recarregarRede">Tentar novamente</button>
    </div>
    <LoadingSkeleton v-if="carregandoRede && !rede" tipo="grafo" />
    <p v-if="rede" class="px-5 py-2 text-xs text-(--muted)">
      {{ num(rede.contas.length) }} contas · {{ num(rede.totalTransferencias) }} transferências
    </p>
    <GraphView
      v-if="rede"
      :rede="rede"
      :selecionadas="[selecionada.id]"
      :conta-centro="selecionada.id"
      :altura="485"
      controles
      interativo
    />
  </DetailDialog>
</template>

<style scoped>
.edge-line.entrada {
  background: #7895b5;
  height: 3px;
}

.edge-line.saida {
  background: #87aa9b;
  height: 3px;
}

.degree-table td {
  height: 68px;
}

.ratio span:last-child {
  background: #98b4a8;
}

.row-button {
  min-width: 36px;
  min-height: 32px;
  display: grid;
  place-items: center;
}

.table-foot {
  padding-top: 20px;
}

.table-foot b {
  color: #334e6c;
}

.edge-line {
  display: inline-block;
  vertical-align: middle;
  width: 23px;
}

.ratio {
  display: flex;
  width: 125px;
  height: 6px;
  background: #e9edf0;
}

.ratio span:first-child {
  background: #7893b4;
}

.degree-dialog {
  --dialog-padding-y: 11px;
  --dialog-title-size: 20px;
  --dialog-title-margin: 2px;
  --dialog-title-line: 1.2;
  --dialog-close-size: 32px;
  --dialog-value-size: 23px;
  --dialog-value-margin: 1px;
  --dialog-value-line: 1.2;
}

.dialog-section {
  padding: 11px 29px;
  border-bottom: 1px solid var(--border);
}

@media (max-width: 560px) {
  .dialog-section {
    padding-inline: 12px;
  }
}
</style>
