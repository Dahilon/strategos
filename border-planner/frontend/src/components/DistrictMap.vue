<template>
  <div ref="container" class="district-map">
    <!-- Agent detail tooltip -->
    <div
      v-if="selectedDistrict"
      class="district-tooltip"
      :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
    >
      <div class="tt-header">
        <span class="tt-name">{{ selectedDistrictName }}</span>
        <span class="tt-status" :style="{ color: statusColor(selectedInfo?.status) }">{{ selectedInfo?.status || '—' }}</span>
        <button class="tt-close" @click="selectedDistrict = null">✕</button>
      </div>
      <div v-if="selectedGroups.length" class="tt-groups">
        <div v-for="g in selectedGroups" :key="g.group" class="tt-group-row">
          <span class="tt-group-name">{{ g.group }}</span>
          <div class="tt-bar-bg">
            <div
              class="tt-bar-fill"
              :style="{
                width: Math.abs(g.sentiment) * 100 + '%',
                background: g.sentiment < -0.3 ? '#ef4444' : g.sentiment < 0 ? '#f97316' : g.sentiment < 0.3 ? '#eab308' : '#22c55e'
              }"
            ></div>
          </div>
          <span class="tt-sentiment">{{ g.sentiment > 0 ? '+' : '' }}{{ g.sentiment.toFixed(1) }}</span>
          <span class="tt-esc" :class="g.escalation_level">{{ g.escalation_level }}</span>
        </div>
      </div>
      <div v-else class="tt-empty">No active agents</div>
      <div v-if="selectedPosts.length" class="tt-posts">
        <div v-for="(post, i) in selectedPosts" :key="i" class="tt-post">"{{ post }}"</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  districts: { type: Array, default: () => [] },
  timeline: { type: Array, default: () => [] },
  plan: { type: Object, default: null },
  timeStep: { type: Number, default: 0 }
})

const container = ref(null)
const selectedDistrict = ref(null)
const tooltipPos = ref({ x: 0, y: 0 })
let svg = null
let simulation = null
let resizeObserver = null

const selectedDistrictName = computed(() => {
  if (!selectedDistrict.value) return ''
  const d = props.districts.find(d => d.id === selectedDistrict.value)
  return d?.name || selectedDistrict.value
})

const selectedInfo = computed(() => {
  if (!selectedDistrict.value || !props.timeline.length) return null
  const step = props.timeline[props.timeStep]
  return step?.districts?.[selectedDistrict.value] || null
})

const selectedGroups = computed(() => selectedInfo.value?.groups || [])

const selectedPosts = computed(() => {
  const posts = []
  for (const g of selectedGroups.value) {
    for (const p of (g.sample_posts || [])) {
      if (p) posts.push(p.length > 120 ? p.slice(0, 117) + '…' : p)
    }
  }
  return posts.slice(0, 3)
})

const STATUS_COLORS = {
  CALM: '#22c55e',
  TENSE: '#eab308',
  PROTEST: '#f97316',
  CRITICAL: '#ef4444'
}

function getDistrictStatus(districtId) {
  if (!props.timeline.length) return null
  const step = props.timeline[props.timeStep]
  if (!step?.districts) return null
  return step.districts[districtId] || null
}

function statusColor(status) {
  return STATUS_COLORS[status] || '#555570'
}

function render() {
  if (!container.value || !props.districts.length) return

  const rect = container.value.getBoundingClientRect()
  const width = rect.width || 800
  const height = rect.height || 600

  d3.select(container.value).selectAll('*').remove()

  svg = d3.select(container.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)

  // Build nodes from districts
  const nodes = props.districts.map(d => ({
    id: d.id,
    name: d.name,
    x: (d.map_position?.x || 0.5) * width,
    y: (d.map_position?.y || 0.5) * height,
    population: d.population,
    fx: (d.map_position?.x || 0.5) * width,
    fy: (d.map_position?.y || 0.5) * height
  }))

  // Build links from connections
  const links = []
  const nodeIds = new Set(nodes.map(n => n.id))
  for (const d of props.districts) {
    for (const c of (d.connections || [])) {
      if (nodeIds.has(c) && d.id < c) {
        links.push({ source: d.id, target: c })
      }
    }
  }

  // Draw links
  svg.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('class', 'link')
    .attr('x1', l => nodes.find(n => n.id === l.source)?.x || 0)
    .attr('y1', l => nodes.find(n => n.id === l.source)?.y || 0)
    .attr('x2', l => nodes.find(n => n.id === l.target)?.x || 0)
    .attr('y2', l => nodes.find(n => n.id === l.target)?.y || 0)
    .attr('stroke', '#2a2a3a')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '4,4')

  // Draw nodes
  const nodeGroup = svg.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('transform', d => `translate(${d.x},${d.y})`)
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      selectedDistrict.value = d.id
      const rect = container.value.getBoundingClientRect()
      tooltipPos.value = {
        x: Math.min(d.x + 35, rect.width - 280),
        y: Math.max(d.y - 60, 10)
      }
    })

  // Outer glow ring (animated when critical)
  nodeGroup.append('circle')
    .attr('class', 'node-glow')
    .attr('r', 28)
    .attr('fill', 'none')
    .attr('stroke', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#2a2a3a'
    })
    .attr('stroke-width', 2)
    .attr('stroke-opacity', 0.3)

  // Main node circle
  nodeGroup.append('circle')
    .attr('class', 'node-main')
    .attr('r', 20)
    .attr('fill', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#1a1a26'
    })
    .attr('fill-opacity', 0.25)
    .attr('stroke', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#3a3a4a'
    })
    .attr('stroke-width', 2)

  // Inner status dot
  nodeGroup.append('circle')
    .attr('r', 5)
    .attr('fill', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#555570'
    })

  // PKU icon (shield emoji or ▲)
  const hasPKU = (id) => props.plan?.peacekeepers?.includes(id)
  const hasSensor = (id) => props.plan?.sensors?.includes(id)

  nodeGroup.filter(d => hasPKU(d.id))
    .append('text')
    .attr('x', 22)
    .attr('y', -14)
    .attr('font-size', '12px')
    .attr('fill', '#4488ff')
    .text('🛡')

  nodeGroup.filter(d => hasSensor(d.id))
    .append('text')
    .attr('x', 22)
    .attr('y', 4)
    .attr('font-size', '10px')
    .attr('fill', '#ffaa22')
    .text('📡')

  // District name label
  nodeGroup.append('text')
    .attr('y', 36)
    .attr('text-anchor', 'middle')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-size', '9px')
    .attr('fill', '#8888aa')
    .text(d => d.name.length > 18 ? d.name.slice(0, 16) + '…' : d.name)

  // Status label below name
  nodeGroup.append('text')
    .attr('class', 'status-label')
    .attr('y', 48)
    .attr('text-anchor', 'middle')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-size', '8px')
    .attr('fill', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#555570'
    })
    .text(d => {
      const info = getDistrictStatus(d.id)
      return info ? info.status : '—'
    })
}

// Update only the dynamic parts when timeStep changes
function updateStatus() {
  if (!svg) return

  svg.selectAll('.node-glow')
    .attr('stroke', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#2a2a3a'
    })

  svg.selectAll('.node-main')
    .transition().duration(400)
    .attr('fill', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#1a1a26'
    })
    .attr('stroke', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#3a3a4a'
    })

  svg.selectAll('circle')
    .filter(function () { return d3.select(this).attr('r') === '5' })
    .transition().duration(400)
    .attr('fill', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#555570'
    })

  svg.selectAll('.status-label')
    .text(d => {
      const info = getDistrictStatus(d.id)
      return info ? info.status : '—'
    })
    .attr('fill', d => {
      const info = getDistrictStatus(d.id)
      return info ? statusColor(info.status) : '#555570'
    })
}

watch(() => props.timeStep, updateStatus)
watch(() => props.timeline, render, { deep: true })
watch(() => props.districts, render, { deep: true })
watch(() => props.plan, render, { deep: true })

onMounted(() => {
  render()
  resizeObserver = new ResizeObserver(() => render())
  if (container.value) resizeObserver.observe(container.value)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.district-map {
  flex: 1;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(ellipse at center, rgba(0, 232, 123, 0.02) 0%, transparent 70%),
    var(--bg-primary);
}

.district-tooltip {
  position: absolute;
  z-index: 10;
  width: 260px;
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  padding: 0.7rem;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  font-size: 0.75rem;
}
.tt-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}
.tt-name {
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  font-size: 0.78rem;
}
.tt-status {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  letter-spacing: 0.08em;
}
.tt-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 0.8rem;
  padding: 0;
  line-height: 1;
}
.tt-close:hover { color: var(--text-primary); }

.tt-groups { display: flex; flex-direction: column; gap: 0.35rem; }
.tt-group-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.tt-group-name {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  color: var(--text-muted);
  min-width: 60px;
}
.tt-bar-bg {
  flex: 1;
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
}
.tt-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}
.tt-sentiment {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  color: var(--text-secondary);
  min-width: 28px;
  text-align: right;
}
.tt-esc {
  font-family: var(--font-mono);
  font-size: 0.55rem;
  padding: 0.1rem 0.3rem;
  border-radius: 2px;
  background: var(--bg-elevated);
  color: var(--text-muted);
}
.tt-esc.protesting, .tt-esc.clashing { color: #ef4444; background: rgba(239,68,68,0.1); }
.tt-esc.organizing { color: #f97316; background: rgba(249,115,54,0.1); }
.tt-esc.grumbling { color: #eab308; background: rgba(234,179,8,0.1); }
.tt-esc.calm { color: #22c55e; background: rgba(34,197,94,0.1); }

.tt-empty {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-style: italic;
}

.tt-posts {
  margin-top: 0.4rem;
  padding-top: 0.4rem;
  border-top: 1px solid var(--border);
}
.tt-post {
  font-size: 0.65rem;
  color: var(--text-secondary);
  font-style: italic;
  line-height: 1.4;
  margin-bottom: 0.25rem;
}
</style>
