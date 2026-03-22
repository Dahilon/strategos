"""
Multi-agent simulation engine — MiroFish pattern.

Each agent is a distinct LLM-driven entity with a persona, stance, and district.
Per timestep, every active agent observes the world state and decides an action.
Agent actions are collected, and district-level outcomes are derived from the
aggregate behavior of agents in each district.

This follows MiroFish's architecture (distinct agents, personas, time-stepped
LLM decisions, action logging) without requiring the OASIS/CAMEL-AI dependency.
"""

import json
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from .llm_client import LLMClient
from .seed_builder import load_config


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AgentProfile:
    agent_id: int
    name: str
    agent_type: str          # student, worker, trader, authority, agitator
    district_id: str
    persona: str             # Full LLM-ready persona text
    stance: str              # supportive, opposing, neutral
    activity_level: float    # 0-1
    influence_weight: float  # multiplier


@dataclass
class AgentAction:
    round_num: int
    hour: int
    agent_id: int
    agent_name: str
    agent_type: str
    district_id: str
    action_type: str         # post, react, organize, patrol, do_nothing
    content: str             # The text the agent produced
    sentiment: float         # -1 to 1
    escalation: str          # calm, grumbling, organizing, protesting, clashing


@dataclass
class GroupStatus:
    group: str
    sentiment: float
    action_count: int
    escalation_level: str
    sample_posts: List[str]


# ---------------------------------------------------------------------------
# Agent builder — creates agent profiles from config
# ---------------------------------------------------------------------------

def build_agents(
    districts: List[dict],
    scenario: dict,
    plan: dict,
) -> List[AgentProfile]:
    """Build agent profiles from templates + scenario + deployment plan."""
    templates = load_config("agent_templates.json")
    agent_types = templates["agent_types"]
    assignments = templates["district_agent_assignments"]
    clauses = templates["deployment_clauses"]
    districts_lookup = {d["id"]: d for d in districts}

    agents = []
    agent_id = 0

    for did, type_list in assignments.items():
        district = districts_lookup.get(did)
        if not district:
            continue

        # Determine deployment clause for this district
        has_pku = did in (plan.get("peacekeepers") or [])
        has_sensor = did in (plan.get("sensors") or [])
        if has_pku and has_sensor:
            deploy_clause = clauses["pku_and_sensor"]
        elif has_pku:
            deploy_clause = clauses["pku_present"]
        elif has_sensor:
            deploy_clause = clauses["sensor_present"]
        else:
            deploy_clause = clauses["none"]

        for atype in type_list:
            tmpl = agent_types[atype]
            idx = agent_id % len(tmpl["names"])
            name = tmpl["names"][idx]

            # Build persona from template
            persona = tmpl["persona_template"].format(
                name=name,
                age=tmpl["ages"][idx] or "unknown",
                district_name=district["name"],
                field=tmpl.get("fields", ["general studies"])[idx % len(tmpl.get("fields", ["general studies"]))],
                workplace=tmpl.get("workplaces", ["local factory"])[idx % len(tmpl.get("workplaces", ["local factory"]))],
                goods=tmpl.get("goods", ["general goods"])[idx % len(tmpl.get("goods", ["general goods"]))],
                deployment_clause=deploy_clause,
                count=40,
                sensor_clause="You have access to real-time sensor feeds giving you early warning of gatherings." if has_sensor else "You rely on foot patrols and informants for situational awareness.",
            )

            agents.append(AgentProfile(
                agent_id=agent_id,
                name=name,
                agent_type=atype,
                district_id=did,
                persona=persona,
                stance=tmpl["default_stance"],
                activity_level=tmpl["default_activity_level"],
                influence_weight=tmpl["default_influence_weight"],
            ))
            agent_id += 1

        # Add authority agent if PKU is deployed here
        if has_pku:
            tmpl = agent_types["authority"]
            idx = agent_id % len(tmpl["names"])
            persona = tmpl["persona_template"].format(
                name=tmpl["names"][idx],
                district_name=district["name"],
                count=40,
                sensor_clause="You have access to real-time sensor feeds giving you early warning of gatherings." if has_sensor else "You rely on foot patrols and informants for situational awareness.",
            )
            agents.append(AgentProfile(
                agent_id=agent_id,
                name=tmpl["names"][idx],
                agent_type="authority",
                district_id=did,
                persona=persona,
                stance="supportive",
                activity_level=tmpl["default_activity_level"],
                influence_weight=tmpl["default_influence_weight"],
            ))
            agent_id += 1

    # Add agitator agents per scenario injection districts
    for did in scenario.get("injection_districts", []):
        district = districts_lookup.get(did)
        if not district:
            continue
        tmpl = agent_types["agitator"]
        idx = agent_id % len(tmpl["names"])

        has_pku = did in (plan.get("peacekeepers") or [])
        has_sensor = did in (plan.get("sensors") or [])
        if has_pku and has_sensor:
            deploy_clause = clauses["pku_and_sensor"]
        elif has_pku:
            deploy_clause = clauses["pku_present"]
        elif has_sensor:
            deploy_clause = clauses["sensor_present"]
        else:
            deploy_clause = clauses["none"]

        persona = tmpl["persona_template"].format(
            name=tmpl["names"][idx],
            district_name=district["name"],
            deployment_clause=deploy_clause,
        )
        agents.append(AgentProfile(
            agent_id=agent_id,
            name=tmpl["names"][idx],
            agent_type="agitator",
            district_id=did,
            persona=persona,
            stance="opposing",
            activity_level=tmpl["default_activity_level"],
            influence_weight=tmpl["default_influence_weight"],
        ))
        agent_id += 1

    return agents


# ---------------------------------------------------------------------------
# World state — tracks what agents can observe
# ---------------------------------------------------------------------------

def build_world_summary(
    hour: int,
    scenario: dict,
    districts: List[dict],
    previous_actions: List[AgentAction],
    round_num: int,
) -> str:
    """Build a world-state summary that agents observe before deciding."""
    districts_lookup = {d["id"]: d for d in districts}

    lines = [
        f"CURRENT TIME: Hour {hour} of {scenario['time_horizon_hours']}.",
        f"SCENARIO: {scenario['name']} — {scenario['description'][:300]}",
        "",
    ]

    if round_num == 0:
        lines.append("This is the START of the crisis. Events are just beginning.")
    else:
        # Summarize recent actions by district
        recent = [a for a in previous_actions if a.hour >= max(0, hour - 6)]
        by_district = {}
        for a in recent:
            by_district.setdefault(a.district_id, []).append(a)

        if by_district:
            lines.append("RECENT EVENTS IN THE REGION:")
            for did, acts in by_district.items():
                dname = districts_lookup.get(did, {}).get("name", did)
                posts = [a.content for a in acts if a.content and a.action_type != "do_nothing"]
                if posts:
                    lines.append(f"  {dname}: {'; '.join(posts[:3])}")
                else:
                    lines.append(f"  {dname}: Quiet.")
        else:
            lines.append("No significant recent activity reported.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent decision — BATCHED: one LLM call per round for all agents
# ---------------------------------------------------------------------------

BATCH_DECISION_PROMPT = """You are simulating multiple distinct agents in a crisis scenario. Each agent has a unique persona and will independently decide what to do this round.

CURRENT WORLD STATE:
{world_state}

AGENTS TO SIMULATE (each decides independently based on their persona):
{agent_descriptions}

For EACH agent, decide their action this round. Respond ONLY with valid JSON:
{{
  "decisions": [
    {{
      "agent_id": <int>,
      "action_type": "post|organize|patrol|do_nothing",
      "content": "What they say or do (1-2 sentences). Empty if do_nothing.",
      "sentiment": <float from -1.0 hostile to 1.0 calm>,
      "escalation": "calm|grumbling|organizing|protesting|clashing"
    }}
  ]
}}

Rules:
- Each agent decides INDEPENDENTLY based on their own persona.
- "post" = publicly speak, share info, make demands. "organize" = mobilize people for collective action. "patrol" = security operations (authority only). "do_nothing" = stay quiet.
- Be true to each persona. A trader won't call for revolution. An agitator won't urge calm.
- Factor in deployment context (peacekeepers, sensors) from each agent's persona.
- Agents with lower activity_level are more likely to do_nothing.
"""


def run_round(
    client: LLMClient,
    agents: List[AgentProfile],
    world_state: str,
    round_num: int,
    hour: int,
) -> List[AgentAction]:
    """Run all agents for one timestep via a SINGLE batched LLM call."""
    # Pre-filter: randomly skip inactive agents
    active_agents = []
    idle_actions = []
    for agent in agents:
        if random.random() <= agent.activity_level:
            active_agents.append(agent)
        else:
            idle_actions.append(AgentAction(
                round_num=round_num, hour=hour,
                agent_id=agent.agent_id, agent_name=agent.name,
                agent_type=agent.agent_type, district_id=agent.district_id,
                action_type="do_nothing", content="", sentiment=0.0,
                escalation="calm",
            ))

    if not active_agents:
        return idle_actions

    # Build agent descriptions for the batch prompt
    agent_lines = []
    for a in active_agents:
        agent_lines.append(
            f"AGENT #{a.agent_id} ({a.name}, {a.agent_type} in {a.district_id}):\n"
            f"  {a.persona[:400]}"
        )
    agent_descriptions = "\n\n".join(agent_lines)

    prompt = BATCH_DECISION_PROMPT.format(
        world_state=world_state,
        agent_descriptions=agent_descriptions,
    )

    try:
        result = client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        decisions_raw = result.get("decisions", [])
        decisions_map = {d["agent_id"]: d for d in decisions_raw}
    except Exception as e:
        # On failure, all agents do nothing
        decisions_map = {}

    actions = list(idle_actions)
    for agent in active_agents:
        d = decisions_map.get(agent.agent_id, {})
        actions.append(AgentAction(
            round_num=round_num, hour=hour,
            agent_id=agent.agent_id, agent_name=agent.name,
            agent_type=agent.agent_type, district_id=agent.district_id,
            action_type=d.get("action_type", "do_nothing"),
            content=d.get("content", ""),
            sentiment=float(d.get("sentiment", 0.0)),
            escalation=d.get("escalation", "calm"),
        ))

    return actions


# ---------------------------------------------------------------------------
# Result aggregation — convert agent actions to district-level outcomes
# ---------------------------------------------------------------------------

ESCALATION_SCORES = {
    "calm": 0.0,
    "grumbling": 0.2,
    "organizing": 0.5,
    "protesting": 0.75,
    "clashing": 1.0,
}


def classify_district_status(actions: List[AgentAction]) -> str:
    """Derive CALM/TENSE/PROTEST/CRITICAL from agent actions in a district."""
    if not actions:
        return "CALM"

    active = [a for a in actions if a.action_type != "do_nothing"]
    if not active:
        return "CALM"

    avg_escalation = sum(
        ESCALATION_SCORES.get(a.escalation, 0) for a in active
    ) / len(active)

    # Check for extreme keywords
    all_content = " ".join(a.content.lower() for a in active)
    critical_keywords = ["violence", "clash", "burn", "attack", "destroy", "weapon", "kill", "blood"]
    has_critical = any(kw in all_content for kw in critical_keywords)

    if has_critical or avg_escalation >= 0.75:
        return "CRITICAL"
    elif avg_escalation >= 0.45:
        return "PROTEST"
    elif avg_escalation >= 0.15:
        return "TENSE"
    return "CALM"


def build_group_statuses(actions: List[AgentAction]) -> List[dict]:
    """Group actions by agent_type and produce per-group summary."""
    by_type = {}
    for a in actions:
        by_type.setdefault(a.agent_type, []).append(a)

    groups = []
    for atype, acts in by_type.items():
        active = [a for a in acts if a.action_type != "do_nothing"]
        avg_sent = sum(a.sentiment for a in acts) / len(acts) if acts else 0

        # Pick worst escalation level
        worst_esc = "calm"
        for a in acts:
            if ESCALATION_SCORES.get(a.escalation, 0) > ESCALATION_SCORES.get(worst_esc, 0):
                worst_esc = a.escalation

        sample = [a.content for a in active if a.content][:2]

        groups.append({
            "group": atype,
            "sentiment": round(avg_sent, 2),
            "action_count": len(active),
            "escalation_level": worst_esc,
            "sample_posts": sample,
        })

    return groups


def build_incident_entries(actions: List[AgentAction], districts: List[dict], hour: int) -> List[dict]:
    """Convert active agent actions into an incident-feed friendly format."""
    districts_lookup = {d["id"]: d.get("name", d["id"]) for d in districts}
    incidents = []

    for a in actions:
        if a.action_type == "do_nothing":
            continue
        incidents.append({
            "hour": hour,
            "agent_id": a.agent_id,
            "agent_name": a.agent_name,
            "agent_type": a.agent_type,
            "district_id": a.district_id,
            "district_name": districts_lookup.get(a.district_id, a.district_id),
            "action_type": a.action_type,
            "summary": a.content,
            "sentiment": round(a.sentiment, 2),
            "escalation": a.escalation,
        })

    return incidents


def detect_cascades(
    all_actions: List[AgentAction],
    districts: List[dict],
    hour: int,
) -> List[dict]:
    """Detect cross-district cascade events based on agent activity patterns."""
    districts_lookup = {d["id"]: d for d in districts}
    connections = {d["id"]: set(d.get("connections", [])) for d in districts}

    # Find districts with high escalation this round
    by_district = {}
    for a in all_actions:
        if a.hour == hour:
            by_district.setdefault(a.district_id, []).append(a)

    hot_districts = set()
    for did, acts in by_district.items():
        status = classify_district_status(acts)
        if status in ("PROTEST", "CRITICAL"):
            hot_districts.add(did)

    cascades = []
    for hot_did in hot_districts:
        for neighbor in connections.get(hot_did, set()):
            if neighbor not in hot_districts:
                # Check if neighbor has any agents who could be influenced
                neighbor_acts = by_district.get(neighbor, [])
                if neighbor_acts:
                    cascades.append({
                        "from_district": hot_did,
                        "to_district": neighbor,
                        "hour": hour,
                        "mechanism": "social media" if random.random() > 0.5 else "word of mouth",
                    })
    return cascades


# ---------------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------------

def run_agent_simulation(
    districts: List[dict],
    scenario: dict,
    plan: dict,
    hours_per_round: int = 6,
) -> dict:
    """
    Run a full multi-agent simulation.

    Returns the same shape as the monolithic simulator:
      {timeline, cascades, final_summary, agent_manifest}
    """
    client = LLMClient()
    agents = build_agents(districts, scenario, plan)
    horizon = scenario.get("time_horizon_hours", 72)
    hours = list(range(0, horizon + 1, hours_per_round))

    all_actions: List[AgentAction] = []
    timeline = []
    all_cascades = []
    incident_log = []

    # All district IDs (including ones without agents)
    all_district_ids = [d["id"] for d in districts]

    for round_num, hour in enumerate(hours):
        # Build world state observation
        world_state = build_world_summary(
            hour, scenario, districts, all_actions, round_num,
        )

        # Each agent decides
        round_actions = run_round(client, agents, world_state, round_num, hour)
        all_actions.extend(round_actions)

        # Detect cascades
        round_cascades = detect_cascades(all_actions, districts, hour)
        all_cascades.extend(round_cascades)

        # Build incident entries for UI timeline/feed
        incident_log.extend(build_incident_entries(round_actions, districts, hour))

        # Aggregate into district-level outcomes
        actions_by_district = {}
        for a in round_actions:
            actions_by_district.setdefault(a.district_id, []).append(a)

        district_results = {}
        for did in all_district_ids:
            acts = actions_by_district.get(did, [])
            status = classify_district_status(acts)

            # Cascade influence: if a neighbor is hot and we have no agents,
            # inherit a muted version of their status
            if not acts:
                districts_lookup = {d["id"]: d for d in districts}
                neighbors = districts_lookup.get(did, {}).get("connections", [])
                neighbor_statuses = []
                for n in neighbors:
                    n_acts = actions_by_district.get(n, [])
                    if n_acts:
                        neighbor_statuses.append(classify_district_status(n_acts))
                if "CRITICAL" in neighbor_statuses:
                    status = "TENSE"
                elif "PROTEST" in neighbor_statuses:
                    status = "TENSE"

            active_posts = [a for a in acts if a.action_type != "do_nothing" and a.content]
            events = [a.content for a in active_posts[:3]]

            district_results[did] = {
                "status": status,
                "events": events,
                "groups": build_group_statuses(acts),
            }

        timeline.append({
            "hour": hour,
            "districts": district_results,
        })

    # Build final summary
    peak_hour = 0
    peak_critical = 0
    all_critical = set()
    all_protest = set()
    for step in timeline:
        crit_count = sum(1 for d in step["districts"].values() if d["status"] == "CRITICAL")
        if crit_count > peak_critical:
            peak_critical = crit_count
            peak_hour = step["hour"]
        for did, d in step["districts"].items():
            if d["status"] == "CRITICAL":
                all_critical.add(did)
            if d["status"] == "PROTEST":
                all_protest.add(did)

    total_incidents = sum(
        1 for a in all_actions
        if a.escalation in ("protesting", "clashing")
    )

    # Generate narrative from agent actions
    narrative = _build_narrative(all_actions, scenario, all_critical, all_protest)

    return {
        "timeline": timeline,
        "cascades": all_cascades,
        "incident_log": incident_log,
        "final_summary": {
            "districts_critical": sorted(all_critical),
            "districts_protest": sorted(all_protest),
            "peak_unrest_hour": peak_hour,
            "total_incidents": total_incidents,
            "narrative": narrative,
        },
        "agent_manifest": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "type": a.agent_type,
                "district": a.district_id,
                "stance": a.stance,
            }
            for a in agents
        ],
    }


def _build_narrative(
    actions: List[AgentAction],
    scenario: dict,
    critical_districts: set,
    protest_districts: set,
) -> str:
    """Build a short narrative summary from agent actions."""
    total_agents = len(set(a.agent_id for a in actions))
    total_active = len(set(a.agent_id for a in actions if a.action_type != "do_nothing"))
    clashes = [a for a in actions if a.escalation == "clashing"]

    parts = [f"Across {scenario['time_horizon_hours']} hours, {total_agents} agents participated in the simulation."]
    if critical_districts:
        parts.append(f"{len(critical_districts)} district(s) reached CRITICAL status: {', '.join(sorted(critical_districts))}.")
    if protest_districts - critical_districts:
        parts.append(f"{len(protest_districts - critical_districts)} additional district(s) saw PROTEST-level unrest.")
    if clashes:
        parts.append(f"{len(clashes)} violent confrontation(s) were reported.")
    if not critical_districts and not protest_districts:
        parts.append("The situation remained largely stable across all districts.")

    return " ".join(parts)
