<script setup>
defineProps({
  tipo: {
    type: String,
    default: 'tabela',
  },
  mensagem: {
    type: String,
    default: 'Carregando dados…',
  },
})
</script>

<template>
  <div class="skeleton rounded border border-(--border) bg-(--white)" role="status">
    <span class="sr-only">{{ mensagem }}</span>
    <div
      v-if="tipo === 'metricas'"
      class="grid grid-cols-3 divide-x divide-(--border)"
      aria-hidden="true"
    >
      <div v-for="i in 3" :key="i" class="space-y-3 p-5">
        <div class="barra h-3 w-3/4 max-w-28"></div>
        <div class="barra h-8 w-2/3 max-w-24"></div>
        <div class="barra h-3 w-full max-w-40"></div>
      </div>
    </div>
    <div v-else-if="tipo === 'grafo'" aria-hidden="true">
      <div class="border-b border-(--border) px-5 py-4">
        <div class="barra h-3 w-28"></div>
      </div>
      <div class="flex h-48 items-center justify-center gap-6 sm:h-80">
        <div class="barra h-5 w-5 !rounded-full"></div>
        <div class="barra h-8 w-8 !rounded-full"></div>
        <div class="barra h-5 w-5 !rounded-full"></div>
      </div>
    </div>
    <div v-else-if="tipo === 'lista'" aria-hidden="true">
      <div
        v-for="i in 4"
        :key="i"
        class="space-y-2 border-b border-(--border) px-5 py-4 last:border-b-0"
      >
        <div class="barra h-3 w-3/5"></div>
        <div class="barra h-2.5 w-2/5"></div>
      </div>
    </div>
    <div v-else aria-hidden="true">
      <div
        v-for="i in 6"
        :key="i"
        class="grid grid-cols-3 gap-5 border-b border-(--border) px-5 py-4 last:border-b-0 sm:grid-cols-5"
      >
        <div
          v-for="coluna in 5"
          :key="coluna"
          class="barra h-3 w-4/5"
          :class="{ 'hidden sm:block': coluna > 3 }"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.barra {
  border-radius: 4px;
  background: #e3eaf2;
}

@media (prefers-reduced-motion: no-preference) {
  .barra {
    animation: carregar 1.6s ease-in-out infinite alternate;
  }
}

@keyframes carregar {
  to {
    opacity: 0.48;
  }
}
</style>
