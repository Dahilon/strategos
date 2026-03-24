# SF-Only Crisis Planner Implementation Plan

## Scope Decision
- Drop Kharaba from active product flow.
- Keep code support for multi-world internally for now, but all UI defaults, demos, and optimization work target SF only.
- Primary world id: `sf_blackout_2026`.

## Product Goal
Build an operational SF crisis command simulator with:
- Real geospatial map (Mapbox)
- Rich individual agent visibility (clickable agents)
- Larger agent population (hybrid LLM + rule-based followers)
- Automatic containment plan prediction (not only manual plan picks)

## Phase 1: Mapbox Foundation (First Step)

### Objective
Replace abstract node layout with real SF geospatial context while preserving current simulation behaviors.

### Deliverables
1. Mapbox map in planner view
2. SF district centroids as lat/lng points
3. District connections as geospatial lines
4. District status coloring on map circles
5. Existing PKU/sensor overlays still visible
6. Existing district click tooltip still works

### Files To Update
- `backend/config/worlds/sf_blackout_2026/districts.json`
- `frontend/package.json`
- `frontend/src/components/DistrictMap.vue`
- `frontend/src/views/PlannerView.vue` (small integration updates only)
- Optional new helpers:
  - `frontend/src/components/map/mapboxLayers.js`
  - `frontend/src/components/map/mapLegend.js`

### Data Model Changes
Add geospatial fields per SF district:
- `geo.center.lat`
- `geo.center.lng`

Keep existing `map_position` temporarily for fallback.

Example shape:
```json
{
  "id": "soma_market",
  "name": "SoMa / Market Street Corridor",
  "geo": {
    "center": { "lat": 37.7784, "lng": -122.4058 }
  }
}
```

### Technical Approach
1. Install Mapbox GL JS in frontend.
2. Use Mapbox token from frontend env (example: `VITE_MAPBOX_TOKEN`).
3. Render one map instance in `DistrictMap.vue`.
4. Build GeoJSON layers from simulation/timeline data:
   - district point layer (circle)
   - district label layer
   - connections line layer
   - PKU/sensor symbol markers
5. On `timeStep` changes, update source data only (do not recreate map).
6. Keep tooltip logic mapped to clicked district id.

### Acceptance Criteria
- SF map renders on real base map tiles.
- Each district appears at realistic SF location.
- District colors update with timeline step.
- Clicking district shows same summary as current tooltip.
- No regression in simulation controls, incident feed, and matrix compare.
- Frontend production build passes.

### Risks / Mitigations
- Token missing -> show inline map error state with fallback plain panel.
- Performance with rerenders -> update sources instead of rebuilding map.
- Label overlap -> use abbreviated labels and zoom-dependent visibility.

### Effort
- 1 working day for first complete version.

---

## Phase 2: Agent-Level Map Visibility

### Objective
Move from district-only insight to agent-level operational awareness.

### Deliverables
- Agent markers rendered around district centroid with deterministic jitter.
- Agent click card with:
  - name, type, channel, stance
  - last 3-5 actions
  - current escalation/sentiment
  - influence score
- Marker filtering by type/channel.

### Backend Changes
- Ensure simulation response includes per-round or latest `agent_states` snapshots.

### Acceptance Criteria
- User can click individual agents and inspect behavior history.
- Incident feed and map clicks are consistent.

---

## Phase 3: Larger Population Model (MiroFish-Like Depth)

### Objective
Increase realism with many individuals while keeping runtime demo-safe.

### Model
- Leader agents: LLM-driven (strategic actors)
- Follower agents: rule-based propagation (crowd response)

### Deliverables
- Multi-spawn rules per district segment
- Agent trait params:
  - `risk_tolerance`
  - `trust_official`
  - `network_reach`
  - `resource_stress`
- Influence graph and weighted reaction propagation

### Acceptance Criteria
- Total agents increase significantly (for SF target 80-300 depending mode).
- Runtime still acceptable for demo mode.

---

## Phase 4: Predict Best Containment (Auto Strategy)

### Objective
System proposes plans instead of relying only on manual chips.

### Deliverables
- New backend endpoint: generate + evaluate candidate plans under constraints
- Monte Carlo evaluation per candidate
- Return top-N recommendations with confidence and rationale
- New UI button: "Predict Best Containment"

### Optimization Inputs
- Objective profile (for example):
  - minimize critical districts
  - minimize cascade count
  - maximize recovery speed
  - preserve trust
- Budget constraints:
  - max response units
  - max sensor coverage

### Acceptance Criteria
- API returns ranked candidate plans with confidence intervals.
- UI displays recommendation and why it wins.

---

## Phase 5: Decision Support and Explainability

### Objective
Make outputs briefing-ready for operations teams.

### Deliverables
- Confidence bands and run variance
- Counterfactual compare view (Recommended vs Baseline)
- "Why this plan" narrative tied to concrete events and districts
- Export snapshot for briefing

### Acceptance Criteria
- A user can justify recommendation from evidence in one screen.

---

## Implementation Order (Recommended)
1. Phase 1 (Mapbox)
2. Phase 2 (Agent click intel)
3. Phase 3 (Population scale)
4. Phase 4 (Auto containment optimizer)
5. Phase 5 (Decision explainability)

---

## First-Step Execution Checklist (Mapbox)
1. Add SF district `geo.center` lat/lng fields.
2. Install mapbox dependency in frontend.
3. Add `VITE_MAPBOX_TOKEN` handling.
4. Refactor `DistrictMap.vue` to mapbox layers.
5. Wire status updates on timeline changes.
6. Preserve current tooltip behavior.
7. Validate via `npm run build`.

## Definition of Done for First Step
- User opens SF scenario and sees real SF map with active district layers.
- Simulation playback still works exactly as before.
- No regressions in right-side planner panel and logs.
