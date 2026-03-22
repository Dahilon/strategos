<template>
  <div class="recommendation section-card" v-if="best">
    <div class="section-head">RECOMMENDATION</div>
    <div class="rec-body">
      <div class="rec-badge">◈ BEST PLAN</div>
      <h3 class="rec-plan">{{ best.plan_id }}</h3>
      <div class="rec-stats">
        <span>Global Risk: <strong :class="riskClass(best.global_risk)">{{ best.global_risk?.toFixed(2) }}</strong></span>
        <span>Risk Reduction: <strong class="accent">{{ best.risk_reduction_pct?.toFixed(1) }}%</strong></span>
      </div>
      <p class="rec-note">
        This deployment plan achieves the lowest composite risk score across all simulated runs.
        Pre-position peacekeeping units and sensors as specified to minimize cascade escalation.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ comparison: { type: Array, default: () => [] } })
const best = computed(() => props.comparison?.[0] || null)
const riskClass = (v) => {
  if (v < 0.3) return 'low'
  if (v < 0.6) return 'med'
  return 'high'
}
</script>

<style scoped>
.rec-body { display: flex; flex-direction: column; gap: 0.5rem; }
.rec-badge {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  letter-spacing: 0.15em;
  color: var(--accent);
}
.rec-plan {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-primary);
  text-transform: uppercase;
}
.rec-stats {
  display: flex;
  gap: 1.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
}
.rec-stats strong { color: var(--text-primary); }
.low { color: #22c55e !important; }
.med { color: #eab308 !important; }
.high { color: #ef4444 !important; }
.accent { color: var(--accent) !important; }
.rec-note {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
