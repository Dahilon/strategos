import json
import os
from ..config import Config


def load_config(filename, world_id=None):
    """Load a config file. If world_id given, loads from worlds/<world_id>/. Otherwise loads from root config/."""
    if world_id:
        path = os.path.join(Config.CONFIG_DIR, 'worlds', world_id, filename)
    else:
        path = os.path.join(Config.CONFIG_DIR, filename)
    with open(path, 'r') as f:
        return json.load(f)


def list_worlds():
    """Return all available worlds from worlds.json registry."""
    registry = load_config('worlds.json')
    worlds = registry['worlds']
    # Inject scenarios list into each world for the home screen
    for world in worlds:
        try:
            scenarios = load_config('scenarios.json', world['id'])['scenarios']
            world['scenarios'] = [
                {'id': s['id'], 'name': s['name'], 'intensity': s.get('intensity', 'medium'),
                 'time_horizon_hours': s.get('time_horizon_hours', 72),
                 'description': s.get('description', '')[:200]}
                for s in scenarios
            ]
        except Exception:
            world['scenarios'] = []
    return worlds


def build_district_prose(districts):
    lines = []
    for d in districts:
        security_label = {
            "minimal": "MINIMAL", "low": "LOW",
            "moderate": "MODERATE", "high": "HIGH"
        }.get(d["current_security"], d["current_security"].upper())

        segments_str = ", ".join(
            f"{k.replace('_', ' ')} ({int(v * 100)}%)"
            for k, v in d["segments"].items()
        )
        connections_str = ", ".join(d["connections"])
        traits_str = ", ".join(d["traits"])

        lines.append(
            f"DISTRICT: {d['name']}\n"
            f"- Population: {d['population']:,}. Density: {d['density']}.\n"
            f"- Economic stress: {d['economic_stress']}/1.0. Protest history: {d['protest_history']}/1.0.\n"
            f"- Security presence: {security_label}.\n"
            f"- Traits: {traits_str}.\n"
            f"- Population segments: {segments_str}.\n"
            f"- Connected to: {connections_str}.\n"
        )
    return "\n".join(lines)


def build_plan_prose(plan, districts_lookup):
    if not plan["peacekeepers"] and not plan["sensors"]:
        return (
            "DEPLOYMENT: NONE (Baseline)\n"
            "No additional peacekeeping units or sensor arrays deployed. "
            "Only existing baseline police presence."
        )

    lines = [f'DEPLOYMENT PLAN: "{plan["label"]}"', ""]

    if plan["peacekeepers"]:
        lines.append("Peacekeeping units stationed in:")
        for did in plan["peacekeepers"]:
            name = districts_lookup[did]["name"]
            lines.append(
                f"- {name}: 1 platoon (40 personnel). Crowd control and "
                f"de-escalation capability. Protest escalation probability "
                f"reduced by ~60%. Armed confrontation probability reduced "
                f"by ~80%. Active community engagement and counter-narrative messaging."
            )
        lines.append("")

    if plan["sensors"]:
        lines.append("Sensor arrays deployed in:")
        for did in plan["sensors"]:
            name = districts_lookup[did]["name"]
            lines.append(
                f"- {name}: Ground sensors, CCTV, and social media monitoring. "
                f"Anomalous gathering detected within 15 minutes. Authorities "
                f"alerted within 30 minutes. Protest mobilization detected "
                f"2-4 hours earlier than baseline."
            )
        lines.append("")

    lines.append("All other districts: baseline police presence only.")
    return "\n".join(lines)


OUTPUT_FORMAT_INSTRUCTION = """
Respond ONLY with valid JSON. No markdown, no explanation, no text outside the JSON.

Use this exact schema:
{
  "timeline": [
    {
      "hour": 0,
      "districts": {
        "<district_id>": {
          "status": "CALM|TENSE|PROTEST|CRITICAL",
          "events": ["short description of notable event, if any"]
        }
      }
    }
  ],
  "cascades": [
    {
      "from_district": "<district_id>",
      "to_district": "<district_id>",
      "hour": 12,
      "mechanism": "social media|road network|word of mouth|economic contagion"
    }
  ],
  "final_summary": {
    "districts_critical": ["<district_id>", ...],
    "districts_protest": ["<district_id>", ...],
    "peak_unrest_hour": 36,
    "total_incidents": 7,
    "narrative": "2-3 sentence summary of what happened"
  }
}

The timeline must have one entry for every 6-hour block from hour 0 to the end of the time horizon.
Every district must appear in every timestep. District IDs must be lowercase_snake_case as given.
"""


def build_simulation_prompt(scenario_id, plan_id, world_id='kharaba_border'):
    districts_data = load_config('districts.json', world_id)['districts']
    scenarios_data = load_config('scenarios.json', world_id)['scenarios']
    plans_data = load_config('plans.json', world_id)['plans']

    # Load world context description
    try:
        worlds = load_config('worlds.json')['worlds']
        world_meta = next((w for w in worlds if w['id'] == world_id), {})
        world_context = world_meta.get('world_context', world_id)
    except Exception:
        world_context = world_id

    districts_lookup = {d['id']: d for d in districts_data}
    scenario = next(s for s in scenarios_data if s['id'] == scenario_id)
    plan = next(p for p in plans_data if p['id'] == plan_id)

    district_ids = [d['id'] for d in districts_data]
    hours = list(range(0, scenario['time_horizon_hours'] + 1, 6))

    system_prompt = (
        "You are a crisis simulation engine producing realistic, internally consistent "
        "simulations of how populations and institutions respond to crises across "
        "interconnected zones.\n\n"
        "Rules:\n"
        "- Be realistic. Not every scenario leads to catastrophe. Response assets have real effects.\n"
        "- Model cascade effects: disruption in connected zones can spread, but distance and barriers matter.\n"
        "- Pre-positioned resources REDUCE escalation where deployed. Sensors DETECT problems earlier.\n"
        "- Zones with high economic stress and disruption history are more volatile.\n"
        f"- Use exactly these district IDs: {json.dumps(district_ids)}\n"
        f"- Timeline must cover hours: {json.dumps(hours)}\n"
        "- Each district status must be one of: CALM, TENSE, PROTEST, CRITICAL"
    )

    user_prompt = (
        "Simulate the following scenario.\n\n"
        f"WORLD: {world_context}\n\n"
        f"{build_district_prose(districts_data)}\n"
        f"SCENARIO: {scenario['name']}\n"
        f"Time horizon: {scenario['time_horizon_hours']} hours.\n"
        f"Intensity: {scenario['intensity']}.\n\n"
        f"{scenario['description']}\n\n"
        f"{build_plan_prose(plan, districts_lookup)}\n\n"
        f"{OUTPUT_FORMAT_INSTRUCTION}"
    )

    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]
