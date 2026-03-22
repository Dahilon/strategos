<template>
  <div class="system-log section-card">
    <div class="section-head">SYSTEM LOG</div>
    <div class="log-container" ref="logContainer">
      <div v-if="!logs.length" class="log-empty mono">Awaiting operations…</div>
      <div v-for="(entry, i) in logs" :key="i" class="log-line">
        <span class="log-time">{{ entry.time }}</span>
        <span class="log-msg" :class="{ error: entry.msg.startsWith('ERROR') }">{{ entry.msg }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({ logs: { type: Array, default: () => [] } })
const logContainer = ref(null)

watch(() => props.logs.length, async () => {
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})
</script>

<style scoped>
.log-container {
  max-height: 160px;
  overflow-y: auto;
  background: var(--bg-primary);
  border-radius: 4px;
  padding: 0.6rem;
  font-family: var(--font-mono);
  font-size: 0.7rem;
}
.log-empty { color: var(--text-muted); }
.log-line {
  display: flex;
  gap: 0.8rem;
  padding: 0.15rem 0;
  line-height: 1.5;
}
.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}
.log-msg {
  color: var(--text-secondary);
}
.log-msg.error {
  color: var(--danger);
}
</style>
