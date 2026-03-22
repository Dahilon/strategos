from .llm_client import LLMClient
from .seed_builder import build_simulation_prompt


def run_simulation(scenario_id, plan_id):
    """Run a single LLM simulation for a scenario + deployment plan.

    Returns the structured prediction as a dict with keys:
      - timeline: list of {hour, districts: {id: {status, events}}}
      - cascades: list of cross-district contagion events
      - final_summary: overall outcome metrics
    """
    client = LLMClient()
    messages = build_simulation_prompt(scenario_id, plan_id)
    result = client.chat_json(messages=messages, temperature=0.4, max_tokens=8192)

    # Basic structural validation
    if "timeline" not in result:
        raise ValueError("LLM response missing 'timeline' key")
    if "final_summary" not in result:
        raise ValueError("LLM response missing 'final_summary' key")
    if not result["timeline"]:
        raise ValueError("LLM returned empty timeline")
    if "cascades" not in result:
        result["cascades"] = []

    return result
