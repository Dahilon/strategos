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
from ..config import Config
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
    available_actions: List[str] = field(default_factory=list)
    reaction_speed: str = "moderate"   # fast | moderate | deliberate
    channel: str = "general"           # comms channel label


@dataclass
class AgentAction:
    round_num: int
    hour: int
    agent_id: int
    agent_name: str
    agent_type: str
    district_id: str
    action_type: str         # operational action verb
    content: str             # The text the agent produced
    sentiment: float         # -1 to 1
    escalation: str          # calm, grumbling, organizing, protesting, clashing
    channel: str = "general" # comms channel


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
    world_id: str = 'kharaba_border',
) -> List[AgentProfile]:
    """Build agent profiles from templates + scenario + deployment plan."""
    templates = load_config("agent_templates.json", world_id)
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
                available_actions=tmpl.get("actions", ["post", "do_nothing"]),
                reaction_speed=tmpl.get("reaction_speed", "moderate"),
                channel=tmpl.get("channel", "general"),
            ))
            agent_id += 1

        # Add authority agent if PKU is deployed and this world defines authority.
        # Some worlds (e.g., SF blackout) model command via other types.
        if has_pku and "authority" in agent_types:
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
                available_actions=tmpl.get("actions", ["deploy_unit", "conduct_patrol", "do_nothing"]),
                reaction_speed=tmpl.get("reaction_speed", "deliberate"),
                channel=tmpl.get("channel", "official_comms"),
            ))
            agent_id += 1

    # Add destabilizing agents per scenario injection districts.
    # Border world uses "agitator"; SF world uses "opportunist".
    injection_type = None
    if "agitator" in agent_types:
        injection_type = "agitator"
    elif "opportunist" in agent_types:
        injection_type = "opportunist"

    if not injection_type:
        return agents

    for did in scenario.get("injection_districts", []):
        district = districts_lookup.get(did)
        if not district:
            continue
        tmpl = agent_types[injection_type]
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
            agent_type=injection_type,
            district_id=did,
            persona=persona,
            stance="opposing",
            activity_level=tmpl["default_activity_level"],
            influence_weight=tmpl["default_influence_weight"],
            available_actions=tmpl.get("actions", ["broadcast_disinformation", "incite_gathering", "go_dark"]),
            reaction_speed=tmpl.get("reaction_speed", "immediate"),
            channel=tmpl.get("channel", "underground_broadcast"),
        ))
        agent_id += 1

    return agents


def expand_agent_population(agents: List[AgentProfile], scale_factor: float) -> List[AgentProfile]:
    """Expand base agent list into a larger population with slight behavioral variation."""
    if scale_factor <= 1.0:
        return agents

    base_scale = int(scale_factor)
    fractional = scale_factor - base_scale
    expanded: List[AgentProfile] = []
    next_agent_id = 0

    for agent in agents:
        # Keep deterministic-ish variability per agent while preserving diversity.
        copies = max(1, base_scale)
        if random.random() < fractional:
            copies += 1

        for idx in range(copies):
            activity_jitter = (random.random() - 0.5) * 0.12
            influence_jitter = (random.random() - 0.5) * 0.18
            name_suffix = f" #{idx + 1}" if copies > 1 else ""

            expanded.append(AgentProfile(
                agent_id=next_agent_id,
                name=f"{agent.name}{name_suffix}",
                agent_type=agent.agent_type,
                district_id=agent.district_id,
                persona=agent.persona,
                stance=agent.stance,
                activity_level=max(0.1, min(1.0, agent.activity_level + activity_jitter)),
                influence_weight=max(0.2, agent.influence_weight + influence_jitter),
                available_actions=list(agent.available_actions),
                reaction_speed=agent.reaction_speed,
                channel=agent.channel,
            ))
            next_agent_id += 1

    return expanded


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

BATCH_DECISION_PROMPT = """You are running a multi-agent operational simulation. Each agent has a specific role, persona, and a defined action vocabulary. They observe the same world state but act INDEPENDENTLY based on their own persona, motivations, and reaction speed.

CURRENT WORLD STATE:
{world_state}

MOST IMPACTFUL RECENT ACTIONS (LAST 12 HOURS):
{impactful_actions}

AGENTS TO SIMULATE:
{agent_descriptions}

For EACH agent, choose ONE action from their available action list. Respond ONLY with valid JSON:
{{
  "decisions": [
    {{
      "agent_id": <int>,
      "action_type": "<exact action name from that agent's available actions>",
      "content": "What they specifically say, broadcast, or do — 1-2 sentences, first person, in character. Empty string if do_nothing or go_dark.",
      "sentiment": <float: -1.0 = maximally hostile/destabilizing, +1.0 = calm/stabilizing>,
      "escalation": "calm|grumbling|organizing|protesting|clashing"
    }}
  ]
}}

Rules:
- Use ONLY an action from that agent's AVAILABLE ACTIONS list. Do not invent new action types.
- Content must be voiced authentically as that specific person would speak or act.
- REACT to recent world events: if an agitator called a gathering, students may rally; if a PKU deployed, the agitator should go_dark or back off.
- When relevant, explicitly react to one of the MOST IMPACTFUL RECENT ACTIONS above (support, counter, exploit, or adapt).
- Reaction speed matters: fast agents (agitator, student) act immediately and emotionally; deliberate agents (authority) are measured and institutional.
- Escalation reflects their actual state honestly: clashing = violence occurring, protesting = active confrontation, organizing = mobilizing, grumbling = discontent expressed, calm = no significant concern.
- A PKU commander does not spread rumors. A trader does not deploy a unit. A student does not establish a cordon. Stay strictly in role.
- Agitator goes_dark when PKU is present and surveillance is active — strategic self-preservation.
"""


def _build_impactful_actions_context(
    previous_actions: List[AgentAction],
    hour: int,
    lookback_hours: int = 12,
    limit: int = 3,
) -> str:
    """Summarize top impactful recent actions so agents can react to one another."""
    impact_weights = {
        "calm": 0.0,
        "grumbling": 0.2,
        "organizing": 0.5,
        "protesting": 0.75,
        "clashing": 1.0,
    }

    recent = [
        a for a in previous_actions
        if a.hour >= max(0, hour - lookback_hours)
        and a.action_type not in ("do_nothing", "go_dark")
        and (a.content or "").strip()
    ]
    if not recent:
        return "None yet — crisis is just starting."

    scored = []
    for a in recent:
        score = impact_weights.get(a.escalation, 0.0) + min(0.5, abs(a.sentiment) * 0.5)
        if a.agent_type in ("agitator", "opportunist"):
            score += 0.2
        scored.append((score, a))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    lines = []
    for idx, (_, action) in enumerate(top, start=1):
        snippet = action.content.strip().replace("\n", " ")
        lines.append(
            f"{idx}. T+{action.hour}h | {action.agent_name} ({action.agent_type}) in {action.district_id} | "
            f"{action.action_type} | {action.escalation} | \"{snippet[:180]}\""
        )
    return "\n".join(lines)


def _pick_available_action(agent: AgentProfile, candidates: List[str]) -> str:
    """Return the first action that exists in the agent's vocabulary."""
    for action in candidates:
        if action in agent.available_actions:
            return action
    if "do_nothing" in agent.available_actions:
        return "do_nothing"
    if "go_dark" in agent.available_actions:
        return "go_dark"
    return agent.available_actions[0] if agent.available_actions else "do_nothing"


def _local_fallback_decision(agent: AgentProfile, round_num: int) -> Dict[str, Any]:
    """Deterministic decision used when LLM calls fail or local mode is forced."""
    # Simple cadence: early rounds mobilize for non-supportive actors; stabilizing actors coordinate.
    if agent.agent_type in ("agitator", "opportunist"):
        action = _pick_available_action(agent, ["broadcast_disinformation", "broadcast_speculation", "incite_gathering", "create_panic_buying", "exploit_supply_shortage"])
        escalation = "organizing" if round_num < 2 else "protesting"
        sentiment = -0.65
        content = f"{agent.name}: amplify instability messaging through {agent.channel}."
    elif agent.agent_type in ("authority", "eoc_coordinator"):
        action = _pick_available_action(agent, ["issue_statement", "issue_city_alert", "allocate_resources", "coordinate_agencies", "conduct_patrol"])
        escalation = "grumbling"
        sentiment = 0.35
        content = f"{agent.name}: coordinate response resources and communicate official guidance."
    elif agent.agent_type in ("hospital_admin",):
        action = _pick_available_action(agent, ["activate_emergency_protocol", "coordinate_triage", "call_for_supplies", "allocate_fuel"])
        escalation = "organizing"
        sentiment = 0.2
        content = f"{agent.name}: activate medical continuity procedures and triage operations."
    elif agent.agent_type in ("utility_crew",):
        action = _pick_available_action(agent, ["dispatch_crews", "assess_grid_damage", "reroute_power", "request_equipment"])
        escalation = "organizing"
        sentiment = 0.15
        content = f"{agent.name}: deploy utility crews and prioritize restoration targets."
    elif agent.agent_type in ("transit_chief",):
        action = _pick_available_action(agent, ["activate_backup_power", "reroute_service", "coordinate_shuttles", "request_fuel"])
        escalation = "organizing"
        sentiment = 0.1
        content = f"{agent.name}: adjust transit operations and coordinate alternative routes."
    elif agent.agent_type in ("student", "community_organizer"):
        action = _pick_available_action(agent, ["organize_rally", "mobilize_volunteers", "coordinate_info_sharing", "organize_food_distribution", "spread_narrative"])
        escalation = "organizing"
        sentiment = -0.05 if agent.stance == "opposing" else 0.05
        content = f"{agent.name}: mobilize local networks to coordinate public action."
    elif agent.agent_type in ("worker", "trader"):
        action = _pick_available_action(agent, ["warn_coworkers", "call_union_meeting", "alert_trade_network", "secure_inventory", "contact_authorities"])
        escalation = "grumbling" if round_num < 2 else "organizing"
        sentiment = -0.1
        content = f"{agent.name}: issue practical warnings through trusted local channels."
    else:
        action = _pick_available_action(agent, ["do_nothing"])
        escalation = "calm"
        sentiment = 0.0
        content = ""

    if action in ("do_nothing", "go_dark"):
        content = ""
        escalation = "calm"
        sentiment = 0.0

    return {
        "agent_id": agent.agent_id,
        "action_type": action,
        "content": content,
        "sentiment": sentiment,
        "escalation": escalation,
    }


def run_round(
    client: LLMClient,
    agents: List[AgentProfile],
    world_state: str,
    round_num: int,
    hour: int,
    previous_actions: List[AgentAction],
) -> (List[AgentAction], bool):
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
                channel=agent.channel,
            ))

    if not active_agents:
        return idle_actions, False

    # Build agent descriptions for the batch prompt
    agent_lines = []
    for a in active_agents:
        action_list = ", ".join(a.available_actions) if a.available_actions else "post, do_nothing"
        agent_lines.append(
            f"AGENT #{a.agent_id} \u2014 {a.name} ({a.agent_type}, {a.district_id})\n"
            f"  PERSONA: {a.persona[:350]}\n"
            f"  AVAILABLE ACTIONS: {action_list}\n"
            f"  REACTION SPEED: {a.reaction_speed}"
        )
    agent_descriptions = "\n\n".join(agent_lines)

    prompt = BATCH_DECISION_PROMPT.format(
        world_state=world_state,
        impactful_actions=_build_impactful_actions_context(previous_actions, hour),
        agent_descriptions=agent_descriptions,
    )

    used_fallback = False
    if Config.SIM_FORCE_LOCAL_DECISIONS:
        used_fallback = True
        decisions_raw = [_local_fallback_decision(a, round_num) for a in active_agents]
        decisions_map = {d["agent_id"]: d for d in decisions_raw}
    else:
        try:
            result = client.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            decisions_raw = result.get("decisions", [])
            decisions_map = {d["agent_id"]: d for d in decisions_raw}
        except Exception:
            if Config.SIM_ALLOW_LOCAL_FALLBACK:
                used_fallback = True
                decisions_raw = [_local_fallback_decision(a, round_num) for a in active_agents]
                decisions_map = {d["agent_id"]: d for d in decisions_raw}
            else:
                # Preserve legacy behavior: if fallback disabled and LLM fails, agents idle.
                decisions_map = {}

    actions = list(idle_actions)
    for agent in active_agents:
        d = decisions_map.get(agent.agent_id, {})
        chosen_action = d.get("action_type", "do_nothing")
        if chosen_action not in agent.available_actions:
            chosen_action = "do_nothing" if "do_nothing" in agent.available_actions else (agent.available_actions[0] if agent.available_actions else "do_nothing")
        actions.append(AgentAction(
            round_num=round_num, hour=hour,
            agent_id=agent.agent_id, agent_name=agent.name,
            agent_type=agent.agent_type, district_id=agent.district_id,
            action_type=chosen_action,
            content=d.get("content", ""),
            sentiment=float(d.get("sentiment", 0.0)),
            escalation=d.get("escalation", "calm"),
            channel=agent.channel,
        ))

    return actions, used_fallback


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
        active = [a for a in acts if a.action_type not in ("do_nothing", "go_dark")]
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
        if a.action_type in ("do_nothing", "go_dark"):
            continue
        incidents.append({
            "hour": hour,
            "agent_id": a.agent_id,
            "agent_name": a.agent_name,
            "agent_type": a.agent_type,
            "district_id": a.district_id,
            "district_name": districts_lookup.get(a.district_id, a.district_id),
            "action_type": a.action_type,
            "channel": a.channel,
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
    world_id: str = 'kharaba_border',
) -> dict:
    """
    Run a full multi-agent simulation.

    Returns the same shape as the monolithic simulator:
      {timeline, cascades, final_summary, agent_manifest}
    """
    client = LLMClient()
    base_agents = build_agents(districts, scenario, plan, world_id)
    scale = max(1.0, min(float(Config.AGENT_SCALE_FACTOR), float(Config.AGENT_SCALE_MAX)))
    agents = expand_agent_population(base_agents, scale)
    horizon = scenario.get("time_horizon_hours", 72)
    hours = list(range(0, horizon + 1, hours_per_round))

    all_actions: List[AgentAction] = []
    timeline = []
    all_cascades = []
    incident_log = []
    fallback_rounds = 0

    # All district IDs (including ones without agents)
    all_district_ids = [d["id"] for d in districts]

    for round_num, hour in enumerate(hours):
        # Build world state observation
        world_state = build_world_summary(
            hour, scenario, districts, all_actions, round_num,
        )

        # Each agent decides
        round_actions, used_fallback = run_round(
            client,
            agents,
            world_state,
            round_num,
            hour,
            all_actions,
        )
        if used_fallback:
            fallback_rounds += 1
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
        "engine_meta": {
            "fallback_rounds": fallback_rounds,
            "used_local_fallback": fallback_rounds > 0,
            "agent_scale_factor": round(scale, 2),
            "base_agent_count": len(base_agents),
            "agent_count": len(agents),
        },
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
