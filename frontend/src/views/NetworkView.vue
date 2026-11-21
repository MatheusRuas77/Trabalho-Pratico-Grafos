<script setup>
import { ref, watch } from 'vue'
import { ArrowDown, ArrowUp, Filter, Info, X } from 'lucide-vue-next'
import Pagination from '../components/Pagination.vue'
import GraphView from '../components/GraphView.vue'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import { url, useApi } from '../services/api'
import { instante, num, valor, volume } from '../services/format'

const saltos = ref(0)
const paginaRede = ref(1)
const raioEditado = ref(0)
const selecionada = ref('')
const todas = ref(false)
const pagina = ref(1)
const filtro = ref(false)
const { dados: rede, carregando: carregandoRede } = useApi(() =>
  url('rede', { saltos: saltos.value, pagina: paginaRede.value, por_pagina: 150 }),
)
const { dados: conta, carregando: carregandoConta } = useApi(
  () => selecionada.value && url('conta', { id: selecionada.value, pagina: pagina.value }),
)

function alternarTransferencias() {
  todas.value = !todas.value
  pagina.value = 1
}

function selecionar(id) {
  selecionada.value = id
  pagina.value = 1
  todas.value = false
}
watch(rede, (atual) => {
  if (atual) selecionar(atual.selecionada)
})
function aplicarRaio() {
  saltos.value = raioEditado.value ?? 0
  paginaRede.value = 1
  filtro.value = false
}
</script>

<template>
  <div class="page-title">
    <h1>{{ $route.meta.titulo }}</h1>
    <p>{{ $route.meta.descricao }}</p>
  </div>
  <div class="toolbar network-toolbar flex flex-wrap items-center gap-3">
    <button type="button" class="control" :aria-expanded="filtro" @click="filtro = !filtro">
      <Filter :size="17" /> Limitar vizinhança <span class="pill">{{ saltos }}</span>
    </button>
    <form v-if="filtro" class="flex items-center gap-2" @submit.prevent="aplicarRaio">
      <label for="raio">Saltos (0 para toda a rede)</label>
      <input
        id="raio"
        v-model.number="raioEditado"
        class="control w-20"
        type="number"
        min="0"
        required
      />
      <button class="control">Aplicar</button>
    </form>
    <small v-if="rede" class="ml-auto"
      ><b>{{ num(rede.contas.length) }} contas</b>　·　{{
        num(rede.transferencias.length)
      }}
      transações exibidas</small
    >
  </div>
  <Pagination v-if="rede" v-model="paginaRede" :paginas="rede.paginas" />
  <LoadingSkeleton v-if="carregandoRede && !rede" tipo="grafo" />
  <section v-else-if="rede" class="split-panel" :class="{ 'with-aside': selecionada }">
    <div class="min-w-0">
      <div class="legend">
        <span><i class="node-dot"></i> Conta</span
        ><span><i class="node-dot active-dot"></i> Selecionada</span
        ><span><i class="edge-line"></i> Transferência</span>
      </div>
      <GraphView
        :rede="rede"
        :selecionadas="[selecionada]"
        :altura="690"
        rotulos
        controles
        interativo
        @conta="selecionar"
        @limpar="selecionar('')"
      />
    </div>
    <aside v-if="selecionada" class="panel-aside account-panel">
      <header class="flex items-center gap-3">
        <div class="account-icon">A</div>
        <div class="min-w-0">
          <small>Conta selecionada</small>
          <h3 class="mono break-all">{{ selecionada }}</h3>
        </div>
        <button
          type="button"
          class="icon-button ml-auto"
          aria-label="Fechar conta"
          @click="selecionar('')"
        >
          <X :size="16" />
        </button>
      </header>
      <LoadingSkeleton v-if="carregandoConta && !conta" tipo="lista" class="mt-4" />
      <template v-else-if="conta">
        <div class="account-stats grid grid-cols-2">
          <div>
            <small>Entradas</small><b>{{ num(conta.entrada) }}</b>
          </div>
          <div>
            <small>Saídas</small><b>{{ num(conta.saida) }}</b>
          </div>
          <div class="col-span-2">
            <small>Volume por moeda</small><b>{{ volume(conta.valores) }}</b>
          </div>
        </div>
        <h4>Informações</h4>
        <dl class="account-info">
          <div>
            <dt>Banco</dt>
            <dd>{{ conta.banco }}</dd>
          </div>
          <div>
            <dt>Primeira atividade</dt>
            <dd>{{ instante(conta.primeira) }}</dd>
          </div>
          <div>
            <dt>Última atividade</dt>
            <dd>{{ instante(conta.ultima) }}</dd>
          </div>
        </dl>
        <div class="flex items-center justify-between mt-7 gap-2">
          <h4>{{ todas ? 'Transferências' : 'Transações recentes' }}</h4>
          <button class="text-link" @click="alternarTransferencias">
            {{ todas ? 'Ver recentes' : 'Ver todas' }}
          </button>
        </div>
        <ul class="transaction-list">
          <li
            v-for="(t, i) in todas ? conta.transferencias : conta.transferencias.slice(0, 3)"
            :key="i"
          >
            <span class="tx-icon" :class="{ in: t.destino === selecionada }"
              ><ArrowDown v-if="t.destino === selecionada" :size="15" /><ArrowUp
                v-else
                :size="15"
            /></span>
            <span
              ><b>{{ t.destino === selecionada ? t.origem : t.destino }}</b
              ><small
                >{{ t.destino === selecionada ? 'Entrada' : 'Saída' }} ·
                {{ instante(t.instante) }}</small
              ></span
            >
            <b>{{ valor(t.valor, t.moeda) }}</b>
          </li>
        </ul>
        <div
          v-if="todas && conta.totalTransferencias > 20"
          class="flex flex-wrap gap-1.5 pt-3"
        >
          <button
            class="control !min-h-[30px] !px-[9px] !text-[11px]"
            :disabled="pagina === 1"
            @click="pagina--"
          >
            Anterior
          </button>
          <button
            class="control !min-h-[30px] !px-[9px] !text-[11px]"
            :disabled="pagina * 20 >= conta.totalTransferencias"
            @click="pagina++"
          >
            Próxima
          </button>
        </div>
        <p class="info-line mt-5">
          <Info :size="14" /> Os dados apoiam a análise investigativa.
        </p>
      </template>
    </aside>
  </section>
</template>

<style scoped>
.network-toolbar {
  padding: 5px 0 16px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 15px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 22px;
  padding: 18px 20px;
  color: var(--muted);
  background: var(--panel);
  font-size: 12px;
}

.legend span {
  display: flex;
  align-items: center;
  gap: 9px;
}

.node-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 1px solid #6c87a7;
  border-radius: 50%;
  background: #dfe8f3;
}

.active-dot {
  background: #5579a4;
  border-color: #345578;
}

.edge-line {
  display: inline-block;
  vertical-align: middle;
  width: 23px;
  height: 1px;
  background: #9babbc;
}

.account-icon {
  flex: 0 0 48px;
  height: 48px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: #dfe8f4;
  color: var(--blue);
  font-size: 20px;
  font-weight: 700;
}

.account-panel header .icon-button {
  background: transparent;
  border-color: transparent;
}

.account-panel h4 {
  color: #688198;
  font-size: 13px;
}

.account-stats {
  margin: 20px 0;
  padding: 12px 14px;
  gap: 10px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.account-stats b {
  display: block;
  font-size: 13px;
  margin-top: 3px;
  overflow-wrap: anywhere;
}

.account-info {
  margin-top: 12px;
  font-size: 12px;
}

.account-info div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 11px;
}

.account-info dt {
  color: var(--muted);
}

.account-info dd {
  text-align: right;
}

.transaction-list {
  margin-top: 10px;
}

.transaction-list li {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid var(--border);
  padding: 9px 0;
  font-size: 10px;
  overflow-wrap: anywhere;
}

.transaction-list small {
  display: block;
  font-size: 10px;
}

.tx-icon {
  width: 29px;
  height: 29px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #e8eef4;
  color: var(--blue);
}

.tx-icon.in {
  background: #e4efea;
  color: #628679;
}
</style>
