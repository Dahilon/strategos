<template>
  <div ref="container" class="district-map">
    <div v-if="mapError" class="map-warning">{{ mapError }}</div>
    <div
      v-if="selectedAgentInfo"
      class="agent-tooltip"
      :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
    >
      <div class="tt-header">
        <span class="tt-name">{{ selectedAgentInfo.name }}</span>
        <span class="tt-status">{{ selectedAgentLabel }}</span>
        <button class="tt-close" @click="selectedAgent = null">✕</button>
      </div>
      <div class="agent-meta-grid">
        <div><span class="meta-k">Type</span><span class="meta-v">{{ selectedAgentInfo.type }}</span></div>
        <div><span class="meta-k">District</span><span class="meta-v">{{ selectedAgentInfo.district }}</span></div>
        <div><span class="meta-k">Stance</span><span class="meta-v">{{ selectedAgentInfo.stance }}</span></div>
        <div><span class="meta-k">Events</span><span class="meta-v">{{ selectedAgentHistory.length }}</span></div>
      </div>
      <div v-if="selectedAgentHistory.length" class="tt-posts">
        <div v-for="(item, i) in selectedAgentHistory" :key="i" class="tt-post">
          <span class="mono">T+{{ item.hour }}h</span> · <strong>{{ item.action_type }}</strong> · {{ item.escalation }}
          <div>{{ item.summary || 'No summary' }}</div>
        </div>
      </div>
      <div v-else class="tt-empty">No recent actions recorded.</div>
    </div>
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
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import mapboxgl from 'mapbox-gl'

const props = defineProps({
  districts: { type: Array, default: () => [] },
  timeline: { type: Array, default: () => [] },
  plan: { type: Object, default: null },
  timeStep: { type: Number, default: 0 },
  agentManifest: { type: Array, default: () => [] },
  incidentLog: { type: Array, default: () => [] },
  agentTypes: { type: Object, default: () => ({}) }
})

const container = ref(null)
const selectedDistrict = ref(null)
const selectedAgent = ref(null)
const tooltipPos = ref({ x: 0, y: 0 })
const mapError = ref('')
let svg = null
let map = null
let mapReady = false
let resizeObserver = null

const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN || ''

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

const selectedAgentInfo = computed(() => {
  if (selectedAgent.value == null) return null
  return props.agentManifest.find(a => a.agent_id === selectedAgent.value) || null
})

const selectedAgentLabel = computed(() => {
  if (!selectedAgentInfo.value) return ''
  return props.agentTypes?.[selectedAgentInfo.value.type]?.label || selectedAgentInfo.value.type
})

const selectedAgentHistory = computed(() => {
  if (selectedAgent.value == null) return []
  return [...(props.incidentLog || [])]
    .filter(i => i.agent_id === selectedAgent.value)
    .sort((a, b) => b.hour - a.hour)
    .slice(0, 5)
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

const useGeoMode = computed(() => {
  if (!props.districts.length) return false
  return props.districts.every(d => d?.geo?.center?.lat != null && d?.geo?.center?.lng != null)
})

function centerFromDistricts() {
  const valid = props.districts.filter(d => d?.geo?.center?.lat != null && d?.geo?.center?.lng != null)
  if (!valid.length) return [-122.4194, 37.7749]
  const lat = valid.reduce((s, d) => s + d.geo.center.lat, 0) / valid.length
  const lng = valid.reduce((s, d) => s + d.geo.center.lng, 0) / valid.length
  return [lng, lat]
}

function shortLabel(name) {
  if (!name) return '—'
  return name.length > 18 ? `${name.slice(0, 16)}…` : name
}

function buildDistrictPointGeoJSON() {
  return {
    type: 'FeatureCollection',
    features: props.districts
      .filter(d => d?.geo?.center?.lat != null && d?.geo?.center?.lng != null)
      .map(d => {
        const info = getDistrictStatus(d.id)
        const hasPKU = props.plan?.peacekeepers?.includes(d.id) ? 1 : 0
        const hasSensor = props.plan?.sensors?.includes(d.id) ? 1 : 0
        return {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [d.geo.center.lng, d.geo.center.lat],
          },
          properties: {
            id: d.id,
            name: d.name,
            short: shortLabel(d.name),
            status: info?.status || 'CALM',
            hasPKU,
            hasSensor,
          },
        }
      }),
  }
}

function buildDistrictLinkGeoJSON() {
  const byId = Object.fromEntries(props.districts.map(d => [d.id, d]))
  const features = []
  for (const d of props.districts) {
    for (const c of (d.connections || [])) {
      if (d.id < c && byId[c]?.geo?.center && d?.geo?.center) {
        features.push({
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: [
              [d.geo.center.lng, d.geo.center.lat],
              [byId[c].geo.center.lng, byId[c].geo.center.lat],
            ],
          },
          properties: {},
        })
      }
    }
  }
  return { type: 'FeatureCollection', features }
}

function buildAgentGeoJSON() {
  const byDistrict = Object.fromEntries(props.districts.map(d => [d.id, d]))
  const features = (props.agentManifest || [])
    .map(agent => {
      const district = byDistrict[agent.district]
      if (!district?.geo?.center) return null

      // Deterministic jitter so markers are separable but stable across rerenders.
      const seed = (agent.agent_id + 1) * 9301
      const r = (seed % 100) / 100
      const angle = (((seed * 7) % 360) * Math.PI) / 180
      const radius = 0.003 + r * 0.0025
      const lng = district.geo.center.lng + Math.cos(angle) * radius
      const lat = district.geo.center.lat + Math.sin(angle) * radius

      return {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lng, lat] },
        properties: {
          agent_id: agent.agent_id,
          name: agent.name,
          type: agent.type,
          district: agent.district,
          stance: agent.stance,
        },
      }
    })
    .filter(Boolean)

  return { type: 'FeatureCollection', features }
}

function ensureMapbox() {
  if (!container.value || !useGeoMode.value) return false
  if (!mapboxToken) {
    mapError.value = 'VITE_MAPBOX_TOKEN not set. Falling back to abstract map.'
    return false
  }
  mapError.value = ''
  if (map) return true

  mapboxgl.accessToken = mapboxToken
  map = new mapboxgl.Map({
    container: container.value,
    style: 'mapbox://styles/mapbox/dark-v11',
    center: centerFromDistricts(),
    zoom: 10.3,
    dragRotate: false,
  })

  map.on('load', () => {
    mapReady = true
    initMapboxLayers()
    refreshMapboxSources()

    map.on('click', 'agent-markers', (e) => {
      const feature = e.features?.[0]
      if (!feature) return
      selectedDistrict.value = null
      selectedAgent.value = Number(feature.properties?.agent_id)
      const rect = container.value.getBoundingClientRect()
      tooltipPos.value = {
        x: Math.min((e.point?.x || 0) + 18, rect.width - 320),
        y: Math.max((e.point?.y || 0) - 120, 10),
      }
    })

    map.on('click', 'district-fill', (e) => {
      const feature = e.features?.[0]
      if (!feature) return
      selectedAgent.value = null
      const districtId = feature.properties?.id
      selectedDistrict.value = districtId
      const rect = container.value.getBoundingClientRect()
      tooltipPos.value = {
        x: Math.min((e.point?.x || 0) + 20, rect.width - 280),
        y: Math.max((e.point?.y || 0) - 60, 10),
      }
    })

    map.on('mouseenter', 'district-fill', () => {
      map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'district-fill', () => {
      map.getCanvas().style.cursor = ''
    })

    map.on('mouseenter', 'agent-markers', () => {
      map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'agent-markers', () => {
      map.getCanvas().style.cursor = ''
    })
  })

  return true
}

function initMapboxLayers() {
  if (!map || !mapReady) return

  if (!map.getSource('district-points')) {
    map.addSource('district-points', {
      type: 'geojson',
      data: buildDistrictPointGeoJSON(),
    })
  }
  if (!map.getSource('district-links')) {
    map.addSource('district-links', {
      type: 'geojson',
      data: buildDistrictLinkGeoJSON(),
    })
  }
  if (!map.getSource('agent-points')) {
    map.addSource('agent-points', {
      type: 'geojson',
      data: buildAgentGeoJSON(),
    })
  }

  if (!map.getLayer('district-links')) {
    map.addLayer({
      id: 'district-links',
      type: 'line',
      source: 'district-links',
      paint: {
        'line-color': '#2a2a3a',
        'line-width': 1.5,
        'line-opacity': 0.8,
      },
    })
  }

  if (!map.getLayer('district-fill')) {
    map.addLayer({
      id: 'district-fill',
      type: 'circle',
      source: 'district-points',
      paint: {
        'circle-radius': 14,
        'circle-color': [
          'match', ['get', 'status'],
          'CALM', '#22c55e',
          'TENSE', '#eab308',
          'PROTEST', '#f97316',
          'CRITICAL', '#ef4444',
          '#555570',
        ],
        'circle-stroke-width': 2,
        'circle-stroke-color': '#b9b9cc',
        'circle-opacity': 0.35,
      },
    })
  }

  if (!map.getLayer('district-labels')) {
    map.addLayer({
      id: 'district-labels',
      type: 'symbol',
      source: 'district-points',
      layout: {
        'text-field': ['get', 'short'],
        'text-font': ['Open Sans Semibold'],
        'text-size': 10,
        'text-offset': [0, 2],
        'text-anchor': 'top',
      },
      paint: {
        'text-color': '#b3b3c8',
      },
    })
  }

  if (!map.getLayer('agent-markers')) {
    map.addLayer({
      id: 'agent-markers',
      type: 'circle',
      source: 'agent-points',
      paint: {
        'circle-radius': 5,
        'circle-color': [
          'match', ['get', 'type'],
          'utility_crew', '#60a5fa',
          'hospital_admin', '#34d399',
          'transit_chief', '#f59e0b',
          'eoc_coordinator', '#a78bfa',
          'community_organizer', '#f472b6',
          'opportunist', '#ef4444',
          'authority', '#60a5fa',
          'student', '#fbbf24',
          'worker', '#f97316',
          'trader', '#22c55e',
          'agitator', '#ef4444',
          '#ffffff',
        ],
        'circle-stroke-width': 1.2,
        'circle-stroke-color': '#0b0f19',
        'circle-opacity': 0.95,
      },
    })
  }

  if (!map.getLayer('pku-layer')) {
    map.addLayer({
      id: 'pku-layer',
      type: 'symbol',
      source: 'district-points',
      filter: ['==', ['get', 'hasPKU'], 1],
      layout: {
        'text-field': '🛡',
        'text-size': 14,
        'text-offset': [1.2, -0.6],
      },
      paint: { 'text-color': '#4488ff' },
    })
  }

  if (!map.getLayer('sensor-layer')) {
    map.addLayer({
      id: 'sensor-layer',
      type: 'symbol',
      source: 'district-points',
      filter: ['==', ['get', 'hasSensor'], 1],
      layout: {
        'text-field': '📡',
        'text-size': 12,
        'text-offset': [1.2, 0.9],
      },
      paint: { 'text-color': '#ffaa22' },
    })
  }
}

function refreshMapboxSources() {
  if (!map || !mapReady) return
  const points = map.getSource('district-points')
  if (points) points.setData(buildDistrictPointGeoJSON())
  const links = map.getSource('district-links')
  if (links) links.setData(buildDistrictLinkGeoJSON())
  const agents = map.getSource('agent-points')
  if (agents) agents.setData(buildAgentGeoJSON())
}

function render() {
  if (!container.value || !props.districts.length) return

  // If geo data + token are available, prefer Mapbox rendering.
  if (useGeoMode.value && ensureMapbox()) {
    d3.select(container.value).selectAll('svg.fallback-svg').remove()
    refreshMapboxSources()
    return
  }

  const rect = container.value.getBoundingClientRect()
  const width = rect.width || 800
  const height = rect.height || 600

  d3.select(container.value).selectAll('svg.fallback-svg').remove()

  svg = d3.select(container.value)
    .append('svg')
    .attr('class', 'fallback-svg')
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
      selectedAgent.value = null
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
  if (map && mapReady && useGeoMode.value) {
    refreshMapboxSources()
    return
  }
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
watch(() => props.agentManifest, updateStatus, { deep: true })
watch(() => props.incidentLog, updateStatus, { deep: true })

watch(useGeoMode, (nextGeo) => {
  if (!nextGeo && map) {
    map.remove()
    map = null
    mapReady = false
  }
  render()
})

onMounted(() => {
  nextTick(() => render())
  resizeObserver = new ResizeObserver(() => {
    if (map) map.resize()
    render()
  })
  if (container.value) resizeObserver.observe(container.value)
})

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
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

.map-warning {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 11;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: #f59e0b;
  background: rgba(20, 20, 28, 0.85);
  border: 1px solid rgba(245, 158, 11, 0.35);
  padding: 0.25rem 0.45rem;
  border-radius: 4px;
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

.agent-tooltip {
  position: absolute;
  z-index: 12;
  width: 300px;
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  padding: 0.7rem;
  box-shadow: 0 4px 20px rgba(0,0,0,0.45);
  font-size: 0.75rem;
}

.agent-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.35rem 0.75rem;
  margin-bottom: 0.45rem;
}

.meta-k {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.meta-v {
  display: block;
  font-size: 0.7rem;
  color: var(--text-primary);
}

.mono {
  font-family: var(--font-mono);
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
