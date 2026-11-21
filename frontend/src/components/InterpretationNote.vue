<script setup>
import { Info } from 'lucide-vue-next'
</script>

<template>
  <aside class="interpretation">
    <Info :size="19" aria-hidden="true" />
    <div>
      <b>Como interpretar este resultado?</b>
      <p><slot /></p>
    </div>
  </aside>
</template>

<style scoped>
.interpretation {
  display: flex;
  gap: 15px;
  align-items: flex-start;
  background: #eaf1f7;
  color: #406388;
  padding: 17px 22px;
  border-left: 3px solid #9ab1cc;
  margin-bottom: 24px;
  font-size: 13px;
}

.interpretation svg {
  flex: none;
}

.interpretation p {
  margin-top: 6px;
  color: #58738d;
  font-size: 12px;
}
</style>
