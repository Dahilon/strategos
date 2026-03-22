<template>
  <div class="comparison section-card" v-if="comparison.length">
    <div class="section-head">PLAN COMPARISON — RANKED</div>
    <table class="comp-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Plan</th>
          <th>Risk</th>
          <th>Stress</th>
          <th>Cascades</th>
          <th>Δ Base</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, i) in comparison"
          :key="row.plan_id"
          :class="{ best: i === 0 }"
          @click="$emit('select', row.plan_id)"
        >
          <td class="rank">{{ i + 1 }}</td>
          <td class="plan-name">{{ row.plan_id }}</td>
          <td :class="riskClass(row.global_risk)">{{ fmt(row.global_risk) }}</td>
          <td>{{ fmt(row.avg_stress) }}</td>
          <td>{{ row.cascade_count?.toFixed(1) || '—' }}</td>
          <td class="delta" :class="{ positive: row.risk_reduction_pct > 0 }">
            {{ row.risk_reduction_pct != null ? (row.risk_reduction_pct > 0 ? '-' : '+') + Math.abs(row.risk_reduction_pct).toFixed(1) + '%' : '—' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({ comparison: { type: Array, default: () => [] } })
defineEmits(['select'])

const fmt = (v) => v != null ? v.toFixed(2) : '—'
const riskClass = (v) => {
  if (v == null) return ''
  if (v < 0.3) return 'low'
  if (v < 0.6) return 'med'
  return 'high'
}
</script>

<style scoped>
.comp-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 0.72rem;
}
.comp-table th {
  text-align: left;
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
  font-weight: 500;
  font-size: 0.62rem;
  letter-spacing: 0.1em;
}
.comp-table td {
  padding: 0.45rem 0.5rem;
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
  cursor: pointer;
}
.comp-table tr:hover td {
  background: var(--bg-elevated);
}
.comp-table tr.best td {
  color: var(--accent);
  font-weight: 600;
}
.rank { color: var(--text-muted); width: 24px; }
.plan-name { white-space: nowrap; }
.low { color: #22c55e; }
.med { color: #eab308; }
.high { color: #ef4444; }
.delta.positive { color: var(--accent); }
</style>
