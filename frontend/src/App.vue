<script setup>
import { computed, ref, watch } from 'vue'
import LoadingSkeleton from './components/LoadingSkeleton.vue'
import { Waypoints } from 'lucide-vue-next'
import { paginas } from './router'
import { requisicoes, url, useApi } from './services/api'

const {
  dados: base,
  erro: erroStatus,
  recarregar: consultarBase,
} = useApi(() => url('base'), 0, true, true)

const BASE_INTEIRA = 'Base inteira'
const limite = ref('')
const enviando = ref(false)
const erroAlteracao = ref('')

watch(
  () => base.value?.limite,
  (atual) => {
    if (atual != null) limite.value = atual === 0 ? BASE_INTEIRA : String(atual)
  },
)

watch(base, (atual, _, onCleanup) => {
  if (!atual) return
  const intervalo = atual.estado === 'carregando' ? 5000 : 60000
  const timer = setTimeout(consultarBase, intervalo)
  onCleanup(() => clearTimeout(timer))
})

function restaurarBaseAoLimpar() {
  if (!limite.value.trim()) aplicarLimite()
}

async function aplicarLimite() {
  if (enviando.value || !base.value || base.value.estado === 'carregando') return

  erroAlteracao.value = ''
  const texto = limite.value.trim()
  const baseInteira = !texto || texto.toLowerCase() === BASE_INTEIRA.toLowerCase()
  const quantidade = baseInteira ? 0 : Number(texto)

  if ((!baseInteira && !/^\d+$/.test(texto)) || !Number.isSafeInteger(quantidade)) {
    erroAlteracao.value =
      'Digite um número inteiro ou deixe o campo vazio para usar a base inteira.'
    return
  }

  limite.value = quantidade === 0 ? BASE_INTEIRA : String(quantidade)
  if (base.value.estado === 'pronta' && quantidade === base.value.limite) return

  enviando.value = true
  try {
    const resposta = await fetch(url('base'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ limite: quantidade }),
    })
    if (!resposta.ok) {
      const json = await resposta.json().catch(() => null)
      throw new Error(
        typeof json?.detail === 'string' ? json.detail : 'Não foi possível alterar a base.',
      )
    }
    base.value = await resposta.json()
  } catch (error) {
    erroAlteracao.value = error.message
    consultarBase()
  } finally {
    enviando.value = false
  }
}

const falhas = computed(() =>
  [...requisicoes.values()].filter((requisicao) => requisicao.erro),
)
function recarregar() {
  falhas.value.forEach((requisicao) => requisicao.recarregar())
}
</script>

<template>
  <header class="topbar">
    <div class="shell topbar-inner flex items-center">
      <RouterLink class="brand flex items-center gap-3" to="/">
        <span class="brand-icon"><Waypoints :size="18" /></span>
        <span><strong>GRAFOS</strong><small>Análise de redes financeiras</small></span>
      </RouterLink>
      <nav aria-label="Navegação principal" class="flex items-stretch">
        <RouterLink v-for="pagina in paginas" :key="pagina.path" :to="pagina.path">{{
          pagina.nome
        }}</RouterLink>
      </nav>
      <form
        class="limite-base ml-auto flex shrink-0 items-center gap-2"
        @submit.prevent="aplicarLimite"
      >
        <label for="limite-transacoes">Limite</label>
        <input
          id="limite-transacoes"
          v-model="limite"
          type="text"
          class="control w-30"
          :placeholder="base ? BASE_INTEIRA : 'Carregando…'"
          autocomplete="off"
          :disabled="enviando || !base || base.estado === 'carregando'"
          aria-describedby="limite-ajuda"
          @focus="$event.target.select()"
          @blur="restaurarBaseAoLimpar"
        />
        <small id="limite-ajuda" class="sr-only"
          >Pressione Enter para aplicar. Apague o valor para voltar à base inteira.</small
        >
      </form>
    </div>
  </header>
  <main class="shell page">
    <div v-if="falhas.length" class="api-status app-status" role="status">
      <span>{{ falhas[0]?.erro }}</span>
      <button v-if="falhas.length" class="control" @click="recarregar">
        Tentar novamente
      </button>
    </div>
    <div v-if="erroStatus || erroAlteracao" class="api-status" role="status">
      <span>{{ erroStatus || erroAlteracao }}</span>
      <button v-if="erroStatus" type="button" class="control" @click="consultarBase">
        Tentar novamente
      </button>
    </div>
    <div v-if="base?.estado === 'erro'" class="api-status" role="status">
      Falha ao carregar a base. Escolha um limite e tente novamente.
    </div>
    <div
      v-if="!erroStatus && (!base || base.estado === 'carregando')"
      class="api-status"
      role="status"
    >
      {{
        base?.limite === 0
          ? 'Carregando a base inteira e calculando as análises…'
          : 'Carregando a base e calculando as análises…'
      }}
    </div>
    <template v-if="!erroStatus && (!base || base.estado === 'carregando')">
      <div class="page-title">
        <h1>{{ $route.meta.titulo }}</h1>
        <p>{{ $route.meta.descricao }}</p>
      </div>
      <LoadingSkeleton
        v-if="['/', '/componentes'].includes($route.path)"
        tipo="metricas"
        class="mb-5"
      />
      <LoadingSkeleton
        :tipo="
          ['/rede', '/ciclos', '/centralidade'].includes($route.path) ? 'grafo' : 'tabela'
        "
      />
    </template>
    <RouterView v-if="base?.estado === 'pronta'" :key="base.versao" />
  </main>
</template>

<style scoped>
.shell {
  width: 91%;
  max-width: 1800px;
  margin-inline: auto;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--white);
  border-bottom: 1px solid var(--border);
}

.topbar-inner {
  min-height: 81px;
}

.brand {
  width: 300px;
  flex: 0 0 300px;
  color: var(--ink);
}

.brand-icon {
  display: grid;
  place-items: center;
  width: 39px;
  height: 39px;
  color: var(--blue);
  border: 1px solid #9eb3ce;
  border-radius: 4px;
}

.brand strong {
  display: block;
  font-size: 17px;
  line-height: 1.2;
  letter-spacing: 0.16em;
}

.brand small {
  display: block;
  margin-top: 1px;
  font-size: 10px;
}

nav {
  gap: clamp(18px, 2.25vw, 43px);
  align-self: stretch;
  overflow-x: auto;
}

nav a {
  display: flex;
  align-items: center;
  color: #687a8f;
  border-bottom: 1px solid transparent;
  white-space: nowrap;
}

nav a:hover,
nav a.router-link-exact-active {
  color: #375f91;
  border-bottom-color: #527aaf;
}

.page {
  padding-block: 32px 72px;
}

.app-status {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 6;
  max-width: calc(100vw - 32px);
  background: white;
  box-shadow: 0 4px 16px #24364d18;
}

@media (max-width: 1280px) {
  .brand {
    width: 210px;
    flex-basis: 210px;
  }
}

@media (max-width: 900px) {
  .topbar-inner {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 4px 8px;
    padding-top: 10px;
  }

  .brand {
    width: auto;
  }

  .limite-base {
    grid-column: 2;
    grid-row: 1;
  }

  nav {
    grid-column: 1 / -1;
    min-height: 45px;
  }

  .page {
    padding-top: 20px;
  }
}

@media (max-width: 420px) {
  .brand small {
    display: none;
  }

  .limite-base input {
    width: 100px;
    padding-inline: 8px;
  }
}
</style>
