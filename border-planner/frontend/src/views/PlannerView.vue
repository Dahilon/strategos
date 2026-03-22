<template>
  <div class="planner">
    <!-- Top bar -->
    <header class="planner-top">
      <div class="top-left">
        <router-link to="/" class="back-link">← SCENARIOS</router-link>
        <span class="divider">/</span>
        <span class="scenario-name">{{ scenario?.name || scenarioId }}</span>
      </div>
      <div class="top-right">
        <span class="status-pill" :class="runStatus">{{ runStatusLabel }}</span>
      </div>
    </header>

    <!-- Main split panel -->
    <div class="split-panel">
      <!-- LEFT: district map -->
      <div class="panel-left">
        <div class="panel-heading">
          <span class="panel-label">DISTRICT MAP</span>
          <span class="panel-sub">{{ currentPlanLabel }}</span>
        </div>
        <DistrictMap
          :districts="districts"
          :timeline="currentTimeline"
          :plan="currentPlan"
          :timeStep="timeStep"
        />
        <div class="time-controls" v-if="currentTimeline.length">
          <button class="time-btn" @click="timeStep = Math.max(0, timeStep - 1)" :disabled="timeStep === 0">◀</button>
          <span class="time-label mono">T+{{ currentTimeline[timeStep]?.hour ?? 0 }}h</span>
          <input
            type="range"
            min="0"
            :max="currentTimeline.length - 1"
            v-model.number="timeStep"
            class="time-slider"
          />
          <button class="time-btn" @click="timeStep = Math.min(currentTimeline.length - 1, timeStep + 1)" :disabled="timeStep >= currentTimeline.length - 1">▶</button>
        </div>
      </div>

      <!-- RIGHT: controls + results -->
      <div class="panel-right">
        <!-- Scenario info -->
        <div class="section-card">
          <div class="section-head">SCENARIO BRIEFING</div>
          <p class="brief-text">{{ scenario?.description }}</p>
          <div class="brief-meta">
            <span>Intensity: <strong>{{ scenario?.intensity }}</strong></span>
            <span>Duration: <strong>{{ scenario?.time_horizon_hours }}h</strong></span>
            <span>Origin: <strong>{{ (scenario?.injection_districts || []).join(', ') }}</strong></span>
          </div>
        </div>

        <!-- Plan selector -->
        <div class="section-card">
          <div class="section-head">DEPLOYMENT PLAN</div>
          <div class="plan-chips">
            <button
              v-for="(pl, pid) in plans"
              :key="pid"
              class="plan-chip"
              :class="{ active: selectedPlan === pid, simulated: simulatedPlans.has(pid) }"
              @click="selectPlan(pid)"
            >
              {{ pl.label }}
            </button>
          </div>
          <div class="plan-detail" v-if="currentPlan">
            <span class="mono">PKU: {{ currentPlan.peacekeepers?.join(', ') || 'none' }}</span>
            <span class="mono">Sensors: {{ currentPlan.sensors?.join(', ') || 'none' }}</span>
          </div>
        </div>

        <!-- Agent manifest -->
        <div class="section-card" v-if="agentManifest.length">
          <div class="section-head">ACTIVE AGENTS ({{ agentManifest.length }})</div>
          <div class="agent-summary">
            <span v-for="(count, type) in agentCounts" :key="type" class="agent-badge">
              {{ agentTypeIcon(type) }} {{ type }}: {{ count }}
            </span>
          </div>
        </div>

        <!-- Simulation insights -->
        <div class="section-card" v-if="currentSimulation">
          <div class="section-head">SIMULATION INSIGHTS</div>
          <div class="score-grid" v-if="currentScores">
            <div class="score-cell">
              <span class="score-label">GLOBAL RISK</span>
              <span class="score-value" :class="riskClass(currentScores.global_risk)">{{ fmt(currentScores.global_risk) }}</span>
            </div>
            <div class="score-cell">
              <span class="score-label">AVG STRESS</span>
              <span class="score-value">{{ fmt(currentScores.avg_stress) }}</span>
            </div>
            <div class="score-cell">
              <span class="score-label">CRITICAL DISTRICTS</span>
              <span class="score-value">{{ currentScores.critical_count ?? 0 }}</span>
            </div>
            <div class="score-cell">
              <span class="score-label">CASCADES</span>
              <span class="score-value">{{ currentScores.cascade_count ?? 0 }}</span>
            </div>
          </div>
          <p class="insight-narrative" v-if="currentSimulation?.final_summary?.narrative">
            {{ currentSimulation.final_summary.narrative }}
          </p>
          <div class="cascade-list" v-if="(currentSimulation?.cascades || []).length">
            <div class="cascade-item" v-for="(c, i) in currentSimulation.cascades.slice(0, 8)" :key="i">
              <span class="mono">T+{{ c.hour }}h</span>
              <span>{{ c.from_district }} → {{ c.to_district }}</span>
              <span class="mono">{{ c.mechanism }}</span>
            </div>
          </div>
        </div>

        <!-- Incident feed -->
        <div class="section-card" v-if="incidentFeed.length">
          <div class="section-head">INCIDENT FEED ({{ incidentFeed.length }})</div>
          <div class="incident-feed">
            <div class="incident-item" v-for="(inc, i) in incidentFeed" :key="i">
              <div class="incident-top">
                <span class="mono">T+{{ inc.hour }}h</span>
                <span class="incident-agent">{{ inc.agent_name }}</span>
                <span class="incident-type">{{ inc.agent_type }}</span>
              </div>
              <div class="incident-body">{{ inc.summary || actionLabel(inc.action_type) }}</div>
              <div class="incident-meta">
                <span>{{ inc.district_name || inc.district_id }}</span>
                <span class="mono">{{ inc.action_type }}</span>
                <span class="mono" :class="escalationClass(inc.escalation)">{{ inc.escalation }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Action buttons -->
        <div class="action-row">
          <button class="btn btn-primary" @click="simulate" :disabled="running">
            {{ running ? 'SIMULATING…' : 'RUN SIMULATION' }}
          </button>
          <button class="btn btn-secondary" @click="runFullMatrix" :disabled="matrixRunning">
            {{ matrixRunning ? 'RUNNING MATRIX…' : 'COMPARE ALL PLANS' }}
          </button>
        </div>

        <!-- Comparison table -->
        <PlanComparison v-if="comparison" :comparison="comparison" @select="selectPlan" />

        <!-- Recommendation -->
        <Recommendation v-if="comparison" :comparison="comparison" />

        <!-- System log -->
        <SystemLog :logs="logs" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getConfig, runSimulation, runMatrix } from '../api/planner'
import DistrictMap from '../components/DistrictMap.vue'
import PlanComparison from '../components/PlanComparison.vue'
import Recommendation from '../components/Recommendation.vue'
import SystemLog from '../components/SystemLog.vue'

const props = defineProps({ scenarioId: String })

const districts = ref([])
const scenarios = ref({})
const plans = ref({})
const selectedPlan = ref('baseline')

const toDict = (arr) => Object.fromEntries(arr.map(item => [item.id, item]))
const agentManifest = ref([])
const agentTypes = ref({})
const timeStep = ref(0)
const running = ref(false)
const matrixRunning = ref(false)
const comparison = ref(null)
const logs = ref([])

// Stores simulation results keyed by plan_id
const simResults = ref({})
const simScores = ref({})
const simulatedPlans = computed(() => new Set(Object.keys(simResults.value)))

const scenario = computed(() => scenarios.value[props.scenarioId])
const currentPlan = computed(() => plans.value[selectedPlan.value])
const currentPlanLabel = computed(() => currentPlan.value?.label || selectedPlan.value)
const currentTimeline = computed(() => simResults.value[selectedPlan.value]?.timeline || [])
const currentSimulation = computed(() => simResults.value[selectedPlan.value] || null)
const currentScores = computed(() => simScores.value[selectedPlan.value] || null)
const incidentFeed = computed(() => {
  const incidents = currentSimulation.value?.incident_log || []
  return [...incidents].sort((a, b) => b.hour - a.hour).slice(0, 40)
})

const agentCounts = computed(() => {
  const counts = {}
  for (const a of agentManifest.value) {
    counts[a.type] = (counts[a.type] || 0) + 1
  }
  return counts
})

function agentTypeIcon(type) {
  return agentTypes.value[type]?.icon || '👤'
}

function fmt(v) {
  return v != null ? Number(v).toFixed(2) : '—'
}

function riskClass(v) {
  if (v == null) return ''
  if (v < 0.3) return 'risk-low'
  if (v < 0.6) return 'risk-med'
  return 'risk-high'
}

function escalationClass(level) {
  if (level === 'clashing' || level === 'protesting') return 'risk-high'
  if (level === 'organizing' || level === 'grumbling') return 'risk-med'
  return 'risk-low'
}

function actionLabel(actionType) {
  const labels = {
    post: 'Public statement issued',
    organize: 'Collective action organized',
    patrol: 'Security patrol activity',
  }
  return labels[actionType] || 'Field action reported'
}

const runStatus = computed(() => {
  if (running.value || matrixRunning.value) return 'running'
  if (comparison.value) return 'done'
  return 'idle'
})
const runStatusLabel = computed(() => {
  if (running.value) return 'SIMULATING'
  if (matrixRunning.value) return 'MATRIX RUN'
  if (comparison.value) return 'ANALYSIS COMPLETE'
  return 'READY'
})

function log(msg) {
  logs.value.push({ time: new Date().toISOString().slice(11, 19), msg })
}

function selectPlan(pid) {
  selectedPlan.value = pid
  timeStep.value = 0
}

watch(() => props.scenarioId, () => {
  simResults.value = {}
  simScores.value = {}
  comparison.value = null
  timeStep.value = 0
  selectedPlan.value = 'baseline'
  logs.value = []
})

async function simulate() {
  running.value = true
  timeStep.value = 0
  log(`Running multi-agent simulation: ${props.scenarioId} × ${selectedPlan.value}`)
  try {
    const data = await runSimulation(props.scenarioId, selectedPlan.value, 'agents')
    simResults.value[selectedPlan.value] = data.simulation
    simScores.value[selectedPlan.value] = data.scores
    if (data.simulation?.agent_manifest) {
      agentManifest.value = data.simulation.agent_manifest
    }
    log(`Simulation complete — Global Risk: ${data.scores?.global_risk?.toFixed(2)} [agents]`)
  } catch (e) {
    log(`ERROR: ${e.message}`)
  } finally {
    running.value = false
  }
}

async function runFullMatrix() {
  matrixRunning.value = true
  log(`Running full matrix for ${props.scenarioId} [agents]`)
  try {
    const data = await runMatrix(props.scenarioId, 2, 'agents')
    comparison.value = data.ranked_plans || data.comparison
    log(`Matrix complete — Best plan: ${comparison.value?.[0]?.plan_id}`)
  } catch (e) {
    log(`ERROR: ${e.message}`)
  } finally {
    matrixRunning.value = false
  }
}

onMounted(async () => {
  log('Loading configuration…')
  try {
    const data = await getConfig()
    districts.value = data.districts
    scenarios.value = toDict(data.scenarios)
    plans.value = toDict(data.plans)
    agentTypes.value = data.agent_types || {}
    log(`Loaded ${data.districts.length} districts, ${Object.keys(data.scenarios).length} scenarios, ${Object.keys(data.plans).length} plans`)
  } catch (e) {
    log(`ERROR loading config: ${e.message}`)
  }
})
</script>

<style scoped>
.planner {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.planner-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.8rem 1.5rem;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
  flex-shrink: 0;
}
.top-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.back-link {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: var(--accent);
  text-decoration: none;
}
.back-link:hover { text-decoration: underline; }
.divider {
  color: var(--text-muted);
  font-size: 0.85rem;
}
.scenario-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.status-pill {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  padding: 0.25rem 0.7rem;
  border-radius: 3px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-muted);
}
.status-pill.running {
  color: var(--warning);
  border-color: var(--warning);
  animation: pulse 1.5s infinite;
}
.status-pill.done {
  color: var(--accent);
  border-color: var(--accent);
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.split-panel {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.panel-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--bg-primary);
}
.panel-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1.2rem;
  border-bottom: 1px solid var(--border);
}
.panel-label {
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
}
.panel-sub {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-secondary);
}

.time-controls {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.6rem 1.2rem;
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
}
.time-btn {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 0.3rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
}
.time-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.time-label {
  font-size: 0.8rem;
  color: var(--accent);
  min-width: 48px;
  text-align: center;
}
.time-slider {
  flex: 1;
  accent-color: var(--accent);
  height: 4px;
}

.panel-right {
  width: 460px;
  min-width: 460px;
  overflow-y: auto;
  padding: 1rem 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: var(--bg-secondary);
}

.section-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1rem;
}
.section-head {
  font-size: 0.65rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  margin-bottom: 0.6rem;
}
.brief-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 0.6rem;
}
.brief-meta {
  display: flex;
  gap: 1.2rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}
.brief-meta strong { color: var(--text-primary); }

.plan-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
}
.plan-chip {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  padding: 0.3rem 0.6rem;
  border-radius: 3px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  transition: all 0.15s;
}
.plan-chip:hover { border-color: var(--text-muted); }
.plan-chip.active {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(0, 232, 123, 0.08);
}
.plan-chip.simulated::after {
  content: ' ✓';
  color: var(--accent);
}
.plan-detail {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.action-row {
  display: flex;
  gap: 0.6rem;
}
.btn {
  flex: 1;
  padding: 0.7rem;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary {
  background: var(--accent);
  color: var(--bg-primary);
  font-weight: 600;
}
.btn-primary:hover:not(:disabled) { background: var(--accent-dim); }
.btn-secondary {
  background: var(--bg-surface);
  border-color: var(--border);
  color: var(--text-secondary);
}
.btn-secondary:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }

.agent-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.agent-badge {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-bottom: 0.6rem;
}

.score-cell {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.45rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.score-label {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  color: var(--text-muted);
  letter-spacing: 0.1em;
}

.score-value {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  color: var(--text-primary);
}

.insight-narrative {
  font-size: 0.78rem;
  color: var(--text-secondary);
  line-height: 1.45;
  margin-bottom: 0.5rem;
}

.cascade-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.cascade-item {
  display: grid;
  grid-template-columns: 58px 1fr auto;
  gap: 0.4rem;
  font-size: 0.68rem;
  color: var(--text-secondary);
}

.incident-feed {
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.incident-item {
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  border-radius: 4px;
  padding: 0.45rem 0.5rem;
}

.incident-top {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.2rem;
}

.incident-agent {
  font-size: 0.72rem;
  color: var(--text-primary);
  font-weight: 600;
}

.incident-type {
  font-family: var(--font-mono);
  font-size: 0.58rem;
  color: var(--accent);
  border: 1px solid var(--border-light);
  border-radius: 3px;
  padding: 0.1rem 0.3rem;
}

.incident-body {
  font-size: 0.72rem;
  color: var(--text-secondary);
  line-height: 1.35;
  margin-bottom: 0.2rem;
}

.incident-meta {
  display: flex;
  justify-content: space-between;
  gap: 0.4rem;
  font-size: 0.62rem;
  color: var(--text-muted);
}

.risk-low {
  color: #22c55e;
}

.risk-med {
  color: #eab308;
}

.risk-high {
  color: #ef4444;
}

.mono { font-family: var(--font-mono); }
</style>
