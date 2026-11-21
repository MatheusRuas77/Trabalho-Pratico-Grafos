<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import cytoscape from 'cytoscape'
import { Focus, Minus, Plus, X } from 'lucide-vue-next'
import { instante, valor } from '../services/format'

const props = defineProps({
  rede: Object,
  selecionadas: { type: Array, default: () => [] },
  pontuacoes: Object,
  altura: { type: Number, default: 500 },
  rotulos: Boolean,
  controles: Boolean,
  contaCentro: String,
  disposicao: { type: String, default: 'cose' },
  interativo: Boolean,
})
const emit = defineEmits(['conta', 'limpar'])
const canvas = ref()
const transferencia = ref(null)
let cy
let observer

function ajustar() {
  cy?.resize()
  if (cy?.elements().length) {
    const elementos =
      props.contaCentro || props.disposicao === 'breadthfirst' ? cy.nodes() : cy.elements()
    cy.fit(elementos, Math.min(72, cy.width() * 0.1))
    if (cy.zoom() > 1.35) {
      cy.zoom(1.35)
      cy.center()
    }
  }
}

function destacar() {
  cy?.nodes().forEach((node) => {
    node.toggleClass('selected', props.selecionadas.includes(node.id()))
  })
}

function desenhar() {
  if (!cy) return
  transferencia.value = null
  const maior = Object.values(props.pontuacoes || {}).reduce(
    (maximo, valor) => Math.max(maximo, valor),
    0,
  )
  const nos = (props.rede?.contas || []).map((id) => {
    const destaque = maior ? (props.pontuacoes[id] || 0) / maior : 0
    return {
      data: { id, tamanho: 24 + 20 * Math.sqrt(destaque) },
      classes: destaque > 0 ? 'relevant' : '',
    }
  })
  const transacoes = props.rede?.transferencias || []
  const paralelas = new Map()
  if (props.contaCentro) {
    for (const t of transacoes) {
      const vizinha = t.origem === props.contaCentro ? t.destino : t.origem
      paralelas.set(vizinha, (paralelas.get(vizinha) || 0) + 1)
    }
  }

  const arestas = transacoes.map((t, i) => {
    const vizinha = t.origem === props.contaCentro ? t.destino : t.origem
    const repeticoes = paralelas.get(vizinha) || 1

    return {
      data: {
        id: 'transferencia-' + i,
        source: t.origem,
        target: t.destino,
        t,
        passoCurva: Math.min(32, 180 / repeticoes),
      },
      classes: [
        props.contaCentro && 'individual',
        t.destaque && 'highlight',
        props.contaCentro && t.origem === props.contaCentro && 'outgoing',
        props.contaCentro && t.destino === props.contaCentro && 'incoming',
      ]
        .filter(Boolean)
        .join(' '),
    }
  })
  cy.elements().remove()
  cy.add([...nos, ...arestas])
  destacar()
  if (props.contaCentro) {
    const anguloDourado = Math.PI * (3 - Math.sqrt(5))
    let indice = 0
    cy.nodes()
      .layout({
        name: 'preset',
        fit: false,
        positions(node) {
          if (node.id() === props.contaCentro) return { x: 0, y: 0 }

          indice += 1
          const raio = 46 * Math.sqrt(indice)
          const angulo = indice * anguloDourado
          return { x: raio * Math.cos(angulo), y: raio * Math.sin(angulo) }
        },
      })
      .run()
    ajustar()
    return
  }

  if (props.disposicao === 'breadthfirst') {
    cy.elements()
      .layout({
        name: 'breadthfirst',
        directed: false,
        roots: cy.nodes().first(),
        fit: false,
        maximal: false,
      })
      .run()
    ajustar()
    return
  }

  // Uma ligação por par orienta o layout, preservando as transferências no canvas.
  const pares = new Set()
  const layout = cy.elements().filter((element) => {
    if (element.isNode()) return true
    const { source, target } = element.data()
    const chave = [source, target].sort().join('|')
    if (source === target || pares.has(chave)) return false
    pares.add(chave)
    return true
  })
  layout
    .layout({
      name: 'cose',
      animate: false,
      randomize: true,
      fit: false,
      idealEdgeLength: 110,
      nodeRepulsion: 7500,
      componentSpacing: 90,
    })
    .run()
  ajustar()
}

onMounted(() => {
  cy = cytoscape({
    container: canvas.value,
    minZoom: props.contaCentro || props.disposicao === 'breadthfirst' ? 0.00001 : 0.12,
    maxZoom: 3,
    hideEdgesOnViewport: Boolean(props.contaCentro) || props.disposicao === 'breadthfirst',
    style: [
      {
        selector: 'node',
        style: {
          width: 'data(tamanho)',
          height: 'data(tamanho)',
          'background-color': '#dfe8f3',
          'border-width': 2.5,
          'border-color': '#6e88a7',
          label: props.rotulos ? 'data(id)' : '',
          color: '#344b65',
          'font-size': 11,
          'font-family': 'monospace',
          'text-valign': 'bottom',
          'text-margin-y': 8,
        },
      },
      {
        selector: 'node.relevant, node.selected',
        style: {
          'border-width': 3,
          label: 'data(id)',
          'background-color': '#8bad9e',
          'border-color': '#577e70',
          'underlay-color': '#7193ba',
          'underlay-opacity': 0.13,
          'underlay-padding': 9,
          'underlay-shape': 'ellipse',
        },
      },
      {
        selector: 'node.selected',
        style: {
          width: 38,
          height: 38,
          'background-color': '#5579a4',
          'border-color': '#345578',
        },
      },
      {
        selector: 'edge',
        style: {
          width: 1.2,
          opacity: 0.8,
          'line-color': '#9babbc',
          'target-arrow-color': '#9babbc',
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.65,
          'curve-style': 'bezier',
        },
      },
      {
        selector: 'edge.individual',
        style: { 'control-point-step-size': 'data(passoCurva)' },
      },
      {
        selector: 'edge.incoming',
        style: { 'line-color': '#7895b5', 'target-arrow-color': '#7895b5' },
      },
      {
        selector: 'edge.outgoing',
        style: { 'line-color': '#87aa9b', 'target-arrow-color': '#87aa9b' },
      },
      {
        selector: 'edge.highlight, edge:selected',
        style: {
          width: 2.5,
          opacity: 1,
          'line-color': '#5479a9',
          'target-arrow-color': '#5479a9',
        },
      },
    ],
  })
  cy.on('tap', 'node', (event) => {
    transferencia.value = null
    emit('conta', event.target.id())
  })
  cy.on('tap', 'edge', (event) => {
    if (props.interativo) transferencia.value = event.target.data('t')
  })
  cy.on('tap', (event) => {
    if (event.target === cy) {
      transferencia.value = null
      emit('limpar')
    }
  })
  desenhar()
  observer = new ResizeObserver(ajustar)
  observer.observe(canvas.value)
})
watch(() => props.rede, desenhar)
watch(() => props.selecionadas, destacar, { deep: true })
onBeforeUnmount(() => {
  observer?.disconnect()
  cy?.destroy()
})

function zoom(fator) {
  cy.zoom({
    level: cy.zoom() * fator,
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
  })
}
</script>

<template>
  <div class="graph" :style="{ '--graph-height': altura + 'px' }">
    <div ref="canvas" class="graph-canvas" aria-label="Grafo de contas e transferências"></div>
    <div v-if="controles" class="graph-controls">
      <button type="button" aria-label="Aproximar" @click="zoom(1.25)">
        <Plus :size="17" />
      </button>
      <button type="button" aria-label="Enquadrar grafo" @click="ajustar">
        <Focus :size="22" />
      </button>
      <button type="button" aria-label="Afastar" @click="zoom(0.8)">
        <Minus :size="17" />
      </button>
    </div>
    <div v-if="transferencia" class="edge-detail">
      <button
        class="icon-button"
        aria-label="Fechar transferência"
        @click="transferencia = null"
      >
        <X :size="16" />
      </button>
      <strong>{{ transferencia.origem }} → {{ transferencia.destino }}</strong>
      <p>
        {{ valor(transferencia.valor, transferencia.moeda) }} · {{ transferencia.formato }}
      </p>
      <small
        >{{ instante(transferencia.instante)
        }}{{ transferencia.rotulada ? ' · Rotulada' : '' }}</small
      >
    </div>
  </div>
</template>

<style scoped>
.graph {
  position: relative;
  height: var(--graph-height);
  border: 1px solid var(--border);
  background-color: #fff;
  background-image:
    linear-gradient(to right, #e6ebf17a 1px, transparent 1px),
    linear-gradient(to bottom, #e6ebf17a 1px, transparent 1px);
  background-size: 31px 31px;
}

.graph-canvas {
  position: absolute;
  inset: 0;
}

.graph-controls {
  position: absolute;
  bottom: 16px;
  left: 17px;
  display: grid;
  border: 1px solid #d5deea;
  border-radius: 6px;
  background: #fff;
  color: #60768e;
}

.graph-controls button {
  width: 39px;
  height: 38px;
  display: grid;
  place-items: center;
}

.graph-controls button + button {
  border-top: 1px solid var(--border);
}

.graph-controls button:hover {
  background: var(--selected);
}

.edge-detail {
  position: absolute;
  right: 16px;
  bottom: 16px;
  max-width: calc(100% - 84px);
  padding: 14px;
  border: 1px solid var(--border);
  background: white;
  box-shadow: 0 8px 24px #354a6220;
  overflow-wrap: anywhere;
}

.edge-detail .icon-button {
  float: right;
  margin-left: 8px;
  min-width: 25px;
  min-height: 25px;
}

@media (max-width: 900px) {
  .graph {
    height: min(var(--graph-height), 60vh);
  }
}
</style>
