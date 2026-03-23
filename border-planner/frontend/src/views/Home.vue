<template>
  <div class="home">
    <header class="home-header">
      <div class="brand">
        <div class="brand-icon">◈</div>
        <div>
          <h1>CRISIS SIMULATION PLATFORM</h1>
          <p class="subtitle">Multi-World Agent-Based Crisis Planning</p>
        </div>
      </div>
      <div class="status-badge" :class="{ ready: configLoaded, error: configError }">
        {{ configError ? 'OFFLINE' : configLoaded ? 'SYSTEM READY' : 'LOADING…' }}
      </div>
    </header>

    <div v-if="configLoaded">
      <!-- World selector -->
      <div class="worlds-list">
        <div
          v-for="world in worlds"
          :key="world.id"
          class="world-block"
          :class="{ active: selectedWorld === world.id }"
        >
          <!-- World header -->
          <div class="world-header" @click="selectedWorld = world.id">
            <div class="world-title-row">
              <span class="world-icon">{{ world.icon }}</span>
              <div>
                <h2 class="world-name">{{ world.name }}</h2>
                <p class="world-desc">{{ world.description }}</p>
              </div>
            </div>
            <span class="world-toggle">{{ selectedWorld === world.id ? '▲' : '▼' }}</span>
          </div>

          <!-- Scenarios for this world (shown when expanded) -->
          <div class="scenario-grid" v-if="selectedWorld === world.id">
            <div
              v-for="sc in world.scenarios"
              :key="sc.id"
              class="scenario-card"
              @click="$router.push({ name: 'Planner', params: { worldId: world.id, scenarioId: sc.id } })"
            >
              <div class="scenario-header">
                <span class="scenario-tag">{{ sc.intensity?.toUpperCase() || 'UNKNOWN' }}</span>
                <span class="scenario-duration">{{ sc.time_horizon_hours }}h</span>
              </div>
              <h3>{{ sc.name }}</h3>
              <p>{{ sc.description }}</p>
              <div class="scenario-enter">ANALYZE →</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="configError" class="error-block">
      Backend offline — start the Flask server on port 5002.
    </div>

    <footer class="home-footer">
      <span class="mono">CSP v2.0</span>
      <span class="mono">{{ worlds.length }} WORLD{{ worlds.length !== 1 ? 'S' : '' }} LOADED</span>
      <span class="mono">Multi-Agent LLM Engine</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getConfig } from '../api/planner'

const worlds = ref([])
const selectedWorld = ref(null)
const configLoaded = ref(false)
const configError = ref(false)

onMounted(async () => {
  try {
    const data = await getConfig()
    worlds.value = data.worlds || []
    // Auto-expand the default world
    const defaultWorld = worlds.value.find(w => w.is_default) || worlds.value[0]
    if (defaultWorld) selectedWorld.value = defaultWorld.id
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

/* Worlds */
.worlds-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.world-block {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s;
}
.world-block.active {
  border-color: var(--accent);
  box-shadow: 0 0 20px rgba(0, 232, 123, 0.06);
}

.world-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.4rem 1.8rem;
  cursor: pointer;
  user-select: none;
}
.world-header:hover { background: rgba(255,255,255,0.02); }

.world-title-row {
  display: flex;
  align-items: center;
  gap: 1.2rem;
}
.world-icon { font-size: 2rem; line-height: 1; }
.world-name {
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}
.world-desc {
  font-size: 0.82rem;
  color: var(--text-secondary);
  max-width: 700px;
  line-height: 1.4;
}
.world-toggle {
  font-size: 0.8rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

/* Scenarios inside a world */
.scenario-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.2rem;
  padding: 0 1.5rem 1.5rem;
  border-top: 1px solid var(--border);
  padding-top: 1.2rem;
}
.scenario-card {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.3rem;
  cursor: pointer;
  transition: all 0.2s;
}
.scenario-card:hover {
  border-color: var(--accent);
  box-shadow: 0 0 16px rgba(0, 232, 123, 0.08);
  transform: translateY(-2px);
}
.scenario-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.7rem;
}
.scenario-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  letter-spacing: 0.12em;
  padding: 0.2rem 0.6rem;
  border-radius: 3px;
  background: rgba(0, 232, 123, 0.08);
  color: var(--accent);
  border: 1px solid rgba(0, 232, 123, 0.2);
}
.scenario-duration {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}
.scenario-card h3 {
  font-size: 1.05rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}
.scenario-card p {
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 0.9rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.scenario-enter {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  color: var(--accent);
  opacity: 0;
  transition: opacity 0.2s;
}
.scenario-card:hover .scenario-enter { opacity: 1; }

.error-block {
  padding: 2rem;
  text-align: center;
  color: var(--danger);
  font-family: var(--font-mono);
  font-size: 0.85rem;
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
