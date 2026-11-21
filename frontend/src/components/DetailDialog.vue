<script setup>
import { onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
defineProps({ titulo: String, legenda: String, descricao: String, amplo: Boolean })
defineEmits(['fechar'])
const dialog = ref()
onMounted(() => dialog.value.showModal())
</script>

<template>
  <dialog
    ref="dialog"
    :class="{ amplo }"
    aria-labelledby="detail-title"
    @cancel.prevent="$emit('fechar')"
    @click.self="$emit('fechar')"
  >
    <div>
      <header class="dialog-header">
        <button
          type="button"
          class="icon-button"
          aria-label="Fechar detalhes"
          @click="$emit('fechar')"
        >
          <X :size="17" />
        </button>
        <small>{{ legenda }}</small>
        <h2 id="detail-title" class="mono">{{ titulo }}</h2>
        <p>{{ descricao }}</p>
      </header>
      <slot />
    </div>
  </dialog>
</template>

<style scoped>
dialog {
  position: fixed;
  inset: 0;
  width: min(1124px, 94vw);
  max-height: 86vh;
  margin: auto;
  padding: 0;
  overflow: auto;
  border: 1px solid var(--border);
  background: #fff;
  color: var(--ink);
  box-shadow: 0 24px 68px #24364d30;
}

dialog.amplo {
  width: min(1225px, 94vw);
}

dialog::backdrop {
  background: #26354558;
  backdrop-filter: blur(2px);
}

.dialog-header p {
  color: var(--muted);
  font-size: 12px;
  margin-top: 3px;
}

.dialog-header {
  padding: var(--dialog-padding-y, 28px) var(--dialog-padding-x, 29px);
  border-bottom: 1px solid var(--border);
}

.dialog-header h2 {
  margin-top: var(--dialog-title-margin, 9px);
  font-size: var(--dialog-title-size, 23px);
  line-height: var(--dialog-title-line, inherit);
}

.dialog-header .icon-button {
  float: right;
  min-width: var(--dialog-close-size, 39px);
  min-height: var(--dialog-close-size, 39px);
}

dialog :deep(.dialog-metrics) {
  padding: var(--dialog-padding-y, 22px) var(--dialog-padding-x, 29px);
  border-bottom: 1px solid var(--border);
}

dialog :deep(.dialog-metrics > div) {
  border-left: 1px solid var(--border);
  padding-inline: var(--dialog-metric-padding, 18px);
}

dialog :deep(.dialog-metrics strong) {
  display: block;
  font-size: var(--dialog-value-size, 27px);
  margin-top: var(--dialog-value-margin, 5px);
  line-height: var(--dialog-value-line, inherit);
  font-weight: 520;
}

dialog :deep(.dialog-metrics.compact strong) {
  font-size: 18px;
}

@media (max-width: 560px) {
  dialog {
    --dialog-padding-x: 12px;
    --dialog-metric-padding: 6px;
  }

  .dialog-header,
  dialog :deep(.dialog-metrics) {
    padding-block: var(--dialog-padding-y, 12px);
  }
}
</style>
