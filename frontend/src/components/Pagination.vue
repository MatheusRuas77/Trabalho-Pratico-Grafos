<script setup>
import { ref, watch } from 'vue'
import { num } from '../services/format'

const props = defineProps({ paginas: Number })
const pagina = defineModel({ type: Number, required: true })
const destino = ref(pagina.value)
watch(pagina, (atual) => {
  destino.value = atual
})

function navegar() {
  pagina.value = Math.min(props.paginas, Math.max(1, destino.value || pagina.value))
}
</script>

<template>
  <form
    v-if="paginas > 1"
    class="pagination flex flex-wrap items-center gap-1.5 pt-3"
    @submit.prevent="navegar"
  >
    <button type="button" class="control" :disabled="pagina === 1" @click="pagina--">
      Anterior
    </button>
    <input
      v-model.number="destino"
      class="control w-23"
      type="number"
      :max="paginas"
      min="1"
      aria-label="Número da página"
      title="Pressione Enter para ir à página"
      required
    />
    <small>de {{ num(paginas) }}</small>
    <button type="button" class="control" :disabled="pagina >= paginas" @click="pagina++">
      Próxima
    </button>
  </form>
</template>

<style scoped>
.pagination .control {
  min-height: 30px;
  padding: 0 9px;
  font-size: 11px;
}
</style>
