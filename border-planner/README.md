# Strategos

**AI-powered multi-agent crisis simulation and decision support platform.**

Strategos simulates complex urban crises using autonomous LLM-driven agents, evaluates containment strategies across real geospatial environments, and provides explainable recommendations backed by evidence — enabling operations teams to make defensible decisions under uncertainty.

---

## Key Capabilities

- **Multi-Agent Simulation** — Autonomous agents (utility crews, hospital admins, transit chiefs, EOC coordinators, community organizers, opportunists) each driven by GPT-4o with distinct personas, decision spaces, and communication channels
- **Cascading Crisis Dynamics** — District-to-district escalation propagation modeled through geographic connections
- **Real Geospatial Mapping** — Mapbox GL JS with three modes: District Status, Agent Activity, and Thermal Distress heatmap
- **Automated Containment Prediction** — Algorithmic plan recommendation based on live crisis state analysis
- **Decision Explainability** — Counterfactual comparison (recommended vs baseline), evidence trails, confidence bands, and exportable briefing snapshots
- **Resilient Execution** — Automatic local fallback when LLM is unavailable; configurable timeout/retry; force-local demo mode

## Current Scenario: SF Blackout 2026

A cascading power failure across San Francisco. 8 real districts (SoMa, Mission, Tenderloin, Sunset, Richmond, Marina, Bayview, Financial District) with geographic coordinates, interconnected infrastructure dependencies, and diverse population dynamics.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND  (Vue 3 + Vite + Mapbox GL + D3)              │
│  ├── Home.vue          → World / scenario selector       │
│  ├── PlannerView.vue   → Main command screen             │
│  ├── DistrictMap.vue   → Geospatial map (3 modes)        │
│  ├── ExplainPanel.vue  → Decision explainability         │
│  └── PlanComparison.vue→ Matrix ranking table            │
├──────────── /api proxy (Vite → Flask) ───────────────────┤
│  BACKEND  (Flask, port 5002)                             │
│  ├── /api/planner/config      → World + district config  │
│  ├── /api/planner/simulate    → Single simulation run    │
│  ├── /api/planner/run-matrix  → All plans × N runs       │
│  ├── /api/planner/recommend   → Auto containment pick    │
│  └── /api/planner/explain     → Full explainability      │
├──────────── Services ────────────────────────────────────┤
│  ├── agent_engine.py   → Multi-agent simulation loop     │
│  ├── scorer.py         → Risk scoring + explainability   │
│  ├── seed_builder.py   → World-aware config loading      │
│  └── llm_client.py     → OpenAI SDK (GPT-4o)            │
├──────────── Config ──────────────────────────────────────┤
│  worlds/sf_blackout_2026/                                │
│    ├── districts.json       (8 districts + geo coords)   │
│    ├── scenarios.json       (crisis triggers)            │
│    ├── plans.json           (deployment options)         │
│    └── agent_templates.json (agent types + behaviors)    │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (GPT-4o)

### 1. Backend

```bash
cd backend
cp .env.example .env        # Add your OpenAI key to LLM_API_KEY
pip install -r requirements.txt
python run.py
```

Backend starts on **http://localhost:5002**. Health check: `http://localhost:5002/health`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend opens on **http://localhost:3000**. Vite proxies all `/api` calls to the backend automatically.

### 3. Demo Mode (No API Key Needed)

For instant demos without LLM latency, add this to `backend/.env`:

```
SIM_FORCE_LOCAL_DECISIONS=true
```

All agent decisions become rule-based (instant, deterministic). The full simulation loop still runs — districts cascade, agents act, scoring works — but no OpenAI calls are made.

---

## How It Works

### Simulation Flow

1. **Config Loading** — World-specific districts, scenarios, plans, and agent templates loaded from JSON config
2. **Agent Spawning** — 5-6 agents per district, each with a type, persona, channel, stance, influence weight, and activity level
3. **Time-Step Loop** (6-hour intervals over 48h):
   - Each agent receives current district state + recent impactful actions from other agents
   - GPT-4o decides what each agent does (or local fallback if LLM unavailable)
   - Actions feed back into district state: sentiments shift, escalation levels change
   - Cross-district cascades trigger through geographic connections
4. **Scoring** — Composite risk score: 50% global risk + 30% avg stress + 20% cascade normalization
5. **Output** — Full timeline, agent manifest, incident log, cascades, final narrative

### Map Modes

| Mode | What It Shows |
|------|--------------|
| **Districts** | Large circles = districts. Color = status (CALM/TENSE/PROTEST/CRITICAL). Size/opacity scale with distress. Overlays show peacekeepers 🛡 and sensors 📡 |
| **Agents** | Tiny circles = individual agents. Size = influence. Opacity = activity. White halo = recent escalation. Filter by type, channel, escalation, or use preset chips (Responders / Disruptors / High Risk) |
| **Thermal** | Weather-radar heatmap. Intensity driven by composite distress across districts. Red hot zones = areas needing immediate intervention |

### Decision Support Pipeline

```
Run Simulation → Compare All Plans → Predict Best Containment → Explain Decision → Export Briefing
```

- **Compare All Plans** — Runs every plan × N simulations, ranks by composite score
- **Predict Best Containment** — Scores plans against current crisis state, penalizes uncovered critical districts
- **Explain Decision** — Counterfactual bars (recommended vs baseline), per-district stress deltas, cascade prevention evidence, confidence bands (mean ± σ)
- **Export** — JSON briefing snapshot with timestamp, narrative, evidence, and all metrics

---

## Configuration

### Environment Variables (backend/.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | OpenAI API key (required for LLM mode) |
| `LLM_MODEL_NAME` | `gpt-4o` | Model to use |
| `LLM_TIMEOUT_SECONDS` | `45` | Per-request timeout |
| `LLM_MAX_RETRIES` | `1` | Retry count on failure |
| `SIM_ALLOW_LOCAL_FALLBACK` | `true` | Auto-fallback to rules when LLM fails |
| `SIM_FORCE_LOCAL_DECISIONS` | `false` | Skip all LLM calls (demo mode) |
| `AGENT_SCALE_FACTOR` | `1.0` | Multiply agent population (e.g., 2.0 = double) |
| `AGENT_SCALE_MAX` | `6` | Max agents per type per district after scaling |

### Frontend Environment (frontend/.env)

| Variable | Description |
|----------|-------------|
| `VITE_MAPBOX_TOKEN` | Mapbox GL access token for geospatial rendering |
| `VITE_API_BASE_URL` | Override API base (optional; Vite proxy handles it in dev) |

---

## Project Structure

```
border-planner/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── config.py            # Environment config
│   │   ├── api/
│   │   │   └── planner.py       # All API endpoints
│   │   └── services/
│   │       ├── agent_engine.py  # Multi-agent simulation core
│   │       ├── scorer.py        # Scoring + explainability
│   │       ├── seed_builder.py  # World-aware config loader
│   │       ├── simulator.py     # Legacy monolithic simulator
│   │       ├── mirofish_adapter.py # Agent sim adapter
│   │       └── llm_client.py    # OpenAI SDK wrapper
│   ├── config/
│   │   ├── worlds.json          # World registry
│   │   └── worlds/
│   │       └── sf_blackout_2026/
│   │           ├── districts.json
│   │           ├── scenarios.json
│   │           ├── plans.json
│   │           └── agent_templates.json
│   ├── run.py                   # Entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── index.js         # Axios client
│   │   │   └── planner.js       # API functions
│   │   ├── components/
│   │   │   ├── DistrictMap.vue   # Mapbox + D3 map
│   │   │   ├── ExplainPanel.vue  # Explainability UI
│   │   │   ├── PlanComparison.vue# Ranking table
│   │   │   ├── Recommendation.vue# Best plan card
│   │   │   └── SystemLog.vue     # Activity log
│   │   ├── views/
│   │   │   ├── Home.vue          # World selector
│   │   │   └── PlannerView.vue   # Main command view
│   │   ├── router/index.js
│   │   └── main.js
│   ├── vite.config.js
│   └── package.json
└── docs/
    └── sf-only-implementation-plan.md
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/planner/config` | GET | List worlds or get world config (`?world_id=sf_blackout_2026`) |
| `/api/planner/simulate` | POST | Run single simulation (`world_id`, `scenario_id`, `plan_id`) |
| `/api/planner/run-matrix` | POST | Run all plans × N runs, return ranked comparison |
| `/api/planner/recommend` | POST | Predict best containment plan from current sim state |
| `/api/planner/explain` | POST | Build full explainability payload with counterfactual + evidence |
| `/api/planner/results/<id>` | GET | Retrieve cached matrix results |
| `/health` | GET | Service health check |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, Vite, Mapbox GL JS, D3.js, Vue Router, Axios |
| Backend | Flask, Flask-CORS |
| AI | OpenAI GPT-4o via Python SDK |
| Config | JSON-based world/scenario/plan definitions |

---

## License

Internal use only.
