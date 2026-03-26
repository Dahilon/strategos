<template>
  <div class="explain-panel section-card" v-if="data">
    <div class="section-head">
      DECISION EXPLAINABILITY
      <button class="export-btn" @click="exportSnapshot" title="Export briefing snapshot">📋 EXPORT</button>
    </div>

    <!-- Narrative summary -->
    <p class="explain-narrative">{{ data.narrative }}</p>

    <!-- Counterfactual comparison -->
    <div class="cf-section" v-if="data.counterfactual">
      <div class="cf-title">COUNTERFACTUAL: {{ recLabel }} vs {{ baseLabel }}</div>
      <div class="cf-bars">
        <div class="cf-row" v-for="m in cfMetrics" :key="m.key">
          <span class="cf-metric-label">{{ m.label }}</span>
          <div class="cf-bar-pair">
            <div class="cf-bar-track">
              <div class="cf-bar base-bar" :style="{ width: barWidth(data.counterfactual.baseline[m.key], m.max) }"></div>
              <span class="cf-bar-val">{{ fmtMetric(data.counterfactual.baseline[m.key], m.key) }}</span>
            </div>
            <div class="cf-bar-track">
              <div class="cf-bar rec-bar" :style="{ width: barWidth(data.counterfactual.recommended[m.key], m.max) }"></div>
              <span class="cf-bar-val">{{ fmtMetric(data.counterfactual.recommended[m.key], m.key) }}</span>
            </div>
          </div>
          <span class="cf-delta" :class="{ positive: data.counterfactual.deltas[m.key] > 0 }">
            {{ data.counterfactual.deltas[m.key] > 0 ? '↓' : '↑' }}{{ Math.abs(data.counterfactual.deltas[m.key]).toFixed(2) }}
          </span>
        </div>
        <div class="cf-legend">
          <span class="cf-legend-item"><span class="cf-dot base-dot"></span>{{ baseLabel }}</span>
          <span class="cf-legend-item"><span class="cf-dot rec-dot"></span>{{ recLabel }}</span>
        </div>
      </div>

      <!-- Per-district delta table -->
      <div class="cf-districts" v-if="districtDeltas.length">
        <div class="cf-dist-title">PER-DISTRICT STRESS CHANGE</div>
        <div class="cf-dist-row" v-for="d in districtDeltas" :key="d.id">
          <span class="cf-dist-name">{{ d.id }}</span>
          <div class="cf-dist-bar-track">
            <div
              class="cf-dist-bar"
              :class="{ improved: d.delta > 0, worsened: d.delta < 0 }"
              :style="{ width: Math.min(Math.abs(d.delta) * 200, 100) + '%' }"
            ></div>
          </div>
          <span class="cf-dist-val" :class="{ improved: d.delta > 0, worsened: d.delta < 0 }">
            {{ d.delta > 0 ? '−' : '+' }}{{ Math.abs(d.delta).toFixed(2) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Evidence: Why this plan -->
    <div class="evidence-section" v-if="data.evidence?.length">
      <div class="ev-title">WHY THIS PLAN</div>
      <div class="ev-item" v-for="(ev, i) in data.evidence" :key="i" :class="'ev-' + ev.severity">
        <span class="ev-icon">{{ evIcon(ev.type) }}</span>
        <span class="ev-text">{{ ev.summary }}</span>
      </div>
    </div>

    <!-- Confidence bands -->
    <div class="conf-section" v-if="confEntries.length">
      <div class="conf-title">CONFIDENCE BANDS ({{ confEntries[0]?.n || '?' }} runs)</div>
      <table class="conf-table">
        <thead>
          <tr>
            <th>Plan</th>
            <th>Risk (μ ± σ)</th>
            <th>Stress (μ ± σ)</th>
            <th>Cascades (μ ± σ)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in confEntries" :key="c.plan_id" :class="{ 'conf-rec': c.plan_id === data.recommended_plan }">
            <td class="conf-plan">{{ c.label }}</td>
            <td>{{ c.risk_mean }} <span class="conf-pm">± {{ c.risk_std }}</span></td>
            <td>{{ c.stress_mean }} <span class="conf-pm">± {{ c.stress_std }}</span></td>
            <td>{{ c.cascade_mean }} <span class="conf-pm">± {{ c.cascade_std }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, default: null },
  planLabels: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['export'])

const recLabel = computed(() =>
  props.data?.counterfactual?.recommended?.label || props.data?.recommended_label || 'Recommended'
)
const baseLabel = computed(() =>
  props.data?.counterfactual?.baseline?.label || 'Baseline'
)

const cfMetrics = [
  { key: 'global_risk', label: 'Global Risk', max: 1 },
  { key: 'avg_stress', label: 'Avg Stress', max: 1 },
  { key: 'cascade_count', label: 'Cascades', max: 10 },
  { key: 'critical_count', label: 'Critical Districts', max: 8 },
]

function barWidth(val, max) {
  return Math.min((val / max) * 100, 100) + '%'
}

function fmtMetric(val, key) {
  if (val == null) return '—'
  if (key === 'cascade_count' || key === 'critical_count') return Number(val).toFixed(1)
  return Number(val).toFixed(2)
}

const districtDeltas = computed(() => {
  const dd = props.data?.counterfactual?.district_deltas
  if (!dd) return []
  return Object.entries(dd)
    .map(([id, delta]) => ({ id, delta }))
    .filter(d => Math.abs(d.delta) >= 0.02)
    .sort((a, b) => b.delta - a.delta)
})

function evIcon(type) {
  if (type === 'cascade_prevented') return '🛡'
  if (type === 'district_improvement') return '📉'
  if (type === 'peacekeeper_coverage') return '🎯'
  return '📋'
}

const confEntries = computed(() => {
  if (!props.data?.confidence) return []
  return Object.entries(props.data.confidence).map(([pid, bands]) => ({
    plan_id: pid,
    label: props.planLabels[pid] || pid,
    n: bands.global_risk?.n || 0,
    risk_mean: bands.global_risk?.mean?.toFixed(2) ?? '—',
    risk_std: bands.global_risk?.std?.toFixed(2) ?? '—',
    stress_mean: bands.avg_stress?.mean?.toFixed(2) ?? '—',
    stress_std: bands.avg_stress?.std?.toFixed(2) ?? '—',
    cascade_mean: bands.cascade_count?.mean?.toFixed(1) ?? '—',
    cascade_std: bands.cascade_count?.std?.toFixed(1) ?? '—',
  }))
})

function exportSnapshot() {
  if (!props.data?.export_summary) return
  const json = JSON.stringify(props.data.export_summary, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `briefing-${props.data.recommended_plan || 'snapshot'}-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  emit('export')
}
</script>

<style scoped>
.explain-panel {
  border-color: rgba(161, 139, 250, 0.35);
  background: rgba(161, 139, 250, 0.04);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.65rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  margin-bottom: 0.6rem;
}

.export-btn {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.08em;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  border: 1px solid rgba(161, 139, 250, 0.45);
  background: rgba(161, 139, 250, 0.1);
  color: #c4b5fd;
  cursor: pointer;
}
.export-btn:hover {
  background: rgba(161, 139, 250, 0.22);
}

.explain-narrative {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 0.8rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--border);
}

/* Counterfactual bars */
.cf-section { margin-bottom: 0.8rem; }
.cf-title, .cf-dist-title, .ev-title, .conf-title {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
}

.cf-bars { display: flex; flex-direction: column; gap: 0.5rem; }
.cf-row {
  display: grid;
  grid-template-columns: 100px 1fr 50px;
  align-items: center;
  gap: 0.5rem;
}
.cf-metric-label {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.cf-bar-pair {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.cf-bar-track {
  height: 10px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}
.cf-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.base-bar { background: rgba(239, 68, 68, 0.55); }
.rec-bar { background: rgba(34, 197, 94, 0.6); }
.cf-bar-val {
  position: absolute;
  right: 4px;
  top: -1px;
  font-family: var(--font-mono);
  font-size: 0.52rem;
  color: var(--text-primary);
  line-height: 12px;
}
.cf-delta {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  color: #ef4444;
  text-align: right;
}
.cf-delta.positive { color: #22c55e; }

.cf-legend {
  display: flex;
  gap: 1rem;
  margin-top: 0.3rem;
}
.cf-legend-item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.58rem;
  color: var(--text-muted);
}
.cf-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.base-dot { background: rgba(239, 68, 68, 0.6); }
.rec-dot { background: rgba(34, 197, 94, 0.65); }

/* District deltas */
.cf-districts { margin-top: 0.6rem; }
.cf-dist-row {
  display: grid;
  grid-template-columns: 110px 1fr 48px;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.25rem;
}
.cf-dist-name {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cf-dist-bar-track {
  height: 7px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
}
.cf-dist-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}
.cf-dist-bar.improved { background: rgba(34, 197, 94, 0.55); }
.cf-dist-bar.worsened { background: rgba(239, 68, 68, 0.5); }
.cf-dist-val {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  text-align: right;
}
.cf-dist-val.improved { color: #22c55e; }
.cf-dist-val.worsened { color: #ef4444; }

/* Evidence */
.evidence-section {
  margin-bottom: 0.8rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border);
}
.ev-item {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  padding: 0.35rem 0.45rem;
  margin-bottom: 0.3rem;
  border-radius: 4px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  font-size: 0.7rem;
  color: var(--text-secondary);
  line-height: 1.4;
}
.ev-icon { flex-shrink: 0; font-size: 0.75rem; }
.ev-high { border-color: rgba(239, 68, 68, 0.3); }
.ev-medium { border-color: rgba(234, 179, 8, 0.3); }

/* Confidence table */
.conf-section {
  padding-top: 0.6rem;
  border-top: 1px solid var(--border);
}
.conf-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 0.65rem;
}
.conf-table th {
  text-align: left;
  padding: 0.35rem 0.4rem;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
  font-weight: 500;
  font-size: 0.56rem;
  letter-spacing: 0.1em;
}
.conf-table td {
  padding: 0.35rem 0.4rem;
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
}
.conf-rec td {
  color: var(--accent);
  font-weight: 600;
}
.conf-plan { white-space: nowrap; }
.conf-pm { color: var(--text-muted); font-size: 0.55rem; }
</style>
