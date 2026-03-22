<template>
  <div class="home">
    <header class="home-header">
      <div class="brand">
        <div class="brand-icon">◈</div>
        <div>
          <h1>BORDER STABILITY PLANNER</h1>
          <p class="subtitle">Kharaba Border Zone — Peacekeeping Unit Pre-Positioning</p>
        </div>
      </div>
      <div class="status-badge" :class="{ ready: configLoaded, error: configError }">
        {{ configError ? 'OFFLINE' : configLoaded ? 'SYSTEM READY' : 'LOADING…' }}
      </div>
    </header>

    <section class="overview">
      <div class="stat-row">
        <div class="stat-card">
          <span class="stat-value">{{ districts.length }}</span>
          <span class="stat-label">DISTRICTS</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ Object.keys(scenarios).length }}</span>
          <span class="stat-label">SCENARIOS</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ Object.keys(plans).length }}</span>
          <span class="stat-label">DEPLOYMENT PLANS</span>
        </div>
      </div>
    </section>

    <section class="scenarios-section">
      <h2>SELECT THREAT SCENARIO</h2>
      <div class="scenario-grid">
        <div
          v-for="(sc, id) in scenarios"
          :key="id"
          class="scenario-card"
          @click="$router.push({ name: 'Planner', params: { scenarioId: id } })"
        >
          <div class="scenario-header">
            <span class="scenario-tag">{{ sc.intensity?.toUpperCase() || 'UNKNOWN' }}</span>
            <span class="scenario-duration">{{ sc.time_horizon_hours }}h</span>
          </div>
          <h3>{{ sc.name }}</h3>
          <p>{{ sc.description }}</p>
          <div class="scenario-meta">
            <span>Origin: <strong>{{ (sc.injection_districts || []).join(', ') || '—' }}</strong></span>
          </div>
          <div class="scenario-enter">ANALYZE →</div>
        </div>
      </div>
    </section>

    <footer class="home-footer">
      <span class="mono">BSP v1.0</span>
      <span class="mono">LLM-as-Simulator Engine</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getConfig } from '../api/planner'

const districts = ref([])
const scenarios = ref({})
const plans = ref({})
const configLoaded = ref(false)
const configError = ref(false)

const toDict = (arr) => Object.fromEntries(arr.map(item => [item.id, item]))

onMounted(async () => {
  try {
    const data = await getConfig()
    districts.value = data.districts
    scenarios.value = toDict(data.scenarios)
    plans.value = toDict(data.plans)
    configLoaded.value = true
  } catch (e) {
    configError.value = true
    console.error('Failed to load config', e)
  }
})
</script>

<style scoped>
.home {
  min-height: 100vh;
  padding: 2rem 3rem;
  max-width: 1400px;
  margin: 0 auto;
}

.home-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
}
.brand {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.brand-icon {
  font-size: 2.5rem;
  color: var(--accent);
  line-height: 1;
}
.brand h1 {
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: var(--text-primary);
}
.subtitle {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 0.2rem;
}

.status-badge {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  padding: 0.35rem 0.8rem;
  border-radius: 4px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-muted);
  letter-spacing: 0.1em;
}
.status-badge.ready {
  color: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(0, 232, 123, 0.15);
}
.status-badge.error {
  color: var(--danger);
  border-color: var(--danger);
}

.overview { margin-bottom: 2.5rem; }
.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}
.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.stat-value {
  font-size: 2.4rem;
  font-weight: 700;
  color: var(--accent);
  font-family: var(--font-mono);
}
.stat-label {
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
}

.scenarios-section h2 {
  font-size: 0.9rem;
  letter-spacing: 0.15em;
  color: var(--text-secondary);
  margin-bottom: 1.2rem;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 1.5rem;
}
.scenario-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
}
.scenario-card:hover {
  border-color: var(--accent);
  box-shadow: 0 0 20px rgba(0, 232, 123, 0.08);
  transform: translateY(-2px);
}
.scenario-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.8rem;
}
.scenario-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  letter-spacing: 0.12em;
  padding: 0.2rem 0.6rem;
  border-radius: 3px;
  background: rgba(0, 232, 123, 0.1);
  color: var(--accent);
  border: 1px solid rgba(0, 232, 123, 0.2);
}
.scenario-duration {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}
.scenario-card h3 {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 0.6rem;
  color: var(--text-primary);
}
.scenario-card p {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 1rem;
}
.scenario-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
}
.scenario-meta strong {
  color: var(--text-primary);
}
.scenario-enter {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  color: var(--accent);
  opacity: 0;
  transition: opacity 0.2s;
}
.scenario-card:hover .scenario-enter {
  opacity: 1;
}

.home-footer {
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
}
.mono {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 0.08em;
}
</style>
