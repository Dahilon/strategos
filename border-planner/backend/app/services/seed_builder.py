import json
import os
from ..config import Config


def load_config(filename):
    path = os.path.join(Config.CONFIG_DIR, filename)
    with open(path, 'r') as f:
        return json.load(f)


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


def build_simulation_prompt(scenario_id, plan_id):
    districts_data = load_config("districts.json")["districts"]
    scenarios_data = load_config("scenarios.json")["scenarios"]
    plans_data = load_config("plans.json")["plans"]

    districts_lookup = {d["id"]: d for d in districts_data}
    scenario = next(s for s in scenarios_data if s["id"] == scenario_id)
    plan = next(p for p in plans_data if p["id"] == plan_id)

    district_ids = [d["id"] for d in districts_data]
    hours = list(range(0, scenario["time_horizon_hours"] + 1, 6))

    system_prompt = (
        "You are a geopolitical simulation engine specializing in civil unrest "
        "prediction and border stability analysis. You produce realistic, "
        "internally consistent simulations of how civilian populations respond "
        "to crises across interconnected districts.\n\n"
        "Rules:\n"
        "- Be realistic. Not every scenario leads to catastrophe. Peacekeepers "
        "and sensors have real effects.\n"
        "- Model cascade effects: unrest in connected districts can spread, "
        "but distance and barriers matter.\n"
        "- Peacekeepers REDUCE escalation where stationed. Sensors DETECT "
        "problems earlier, enabling faster response.\n"
        "- Districts with high economic stress and protest history are more volatile.\n"
        f"- Use exactly these district IDs: {json.dumps(district_ids)}\n"
        f"- Timeline must cover hours: {json.dumps(hours)}\n"
        "- Each district status must be one of: CALM, TENSE, PROTEST, CRITICAL"
    )

    user_prompt = (
        "Simulate the following scenario.\n\n"
        "WORLD: Kharaba Border Zone\n"
        "A frontier region of 10 districts along a contested international border. "
        "The central government maintains partial control. Peripheral districts "
        "are influenced by cross-border actors.\n\n"
        f"{build_district_prose(districts_data)}\n"
        f"SCENARIO: {scenario['name']}\n"
        f"Time horizon: {scenario['time_horizon_hours']} hours.\n"
        f"Intensity: {scenario['intensity']}.\n\n"
        f"{scenario['description']}\n\n"
        f"{build_plan_prose(plan, districts_lookup)}\n\n"
        f"{OUTPUT_FORMAT_INSTRUCTION}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
