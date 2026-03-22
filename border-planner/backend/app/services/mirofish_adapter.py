"""
MiroFish adapter — bridges the multi-agent engine to the planner API.

Drop-in replacement for simulator.run_simulation(). Uses distinct agents
(MiroFish pattern) instead of a monolithic LLM call.
"""

from .seed_builder import load_config
from .agent_engine import run_agent_simulation


def run_simulation_agents(scenario_id: str, plan_id: str) -> dict:
    """
    Run a multi-agent simulation for one scenario + plan combo.

    Returns the same shape as simulator.run_simulation():
      {timeline, cascades, final_summary}
    plus extra agent fields:
            {agent_manifest, incident_log}
    """
    districts = load_config("districts.json")["districts"]
    scenarios = load_config("scenarios.json")["scenarios"]
    plans = load_config("plans.json")["plans"]

    scenario = next(s for s in scenarios if s["id"] == scenario_id)
    plan = next(p for p in plans if p["id"] == plan_id)

    result = run_agent_simulation(
        districts=districts,
        scenario=scenario,
        plan=plan,
        hours_per_round=6,
    )

    # Validate same shape as monolithic simulator
    if "timeline" not in result:
        raise ValueError("Agent simulation missing 'timeline'")
    if "final_summary" not in result:
        raise ValueError("Agent simulation missing 'final_summary'")
    if not result["timeline"]:
        raise ValueError("Agent simulation returned empty timeline")
    if "cascades" not in result:
        result["cascades"] = []
    if "incident_log" not in result:
        result["incident_log"] = []

    return result
