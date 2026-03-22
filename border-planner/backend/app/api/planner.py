import json
import os
import traceback
from flask import Blueprint, request, jsonify
from ..config import Config
from ..services.seed_builder import load_config
from ..services.simulator import run_simulation
from ..services.mirofish_adapter import run_simulation_agents
from ..services.scorer import score_run, aggregate_runs, compare_plans

planner_bp = Blueprint('planner', __name__)


def _check_llm():
    if not Config.llm_ready():
        return jsonify({
            "success": False,
            "error": "LLM_API_KEY not configured. Edit backend/.env with your OpenAI API key."
        }), 503
    return None


@planner_bp.route('/config', methods=['GET'])
def get_config():
    """Return districts, scenarios, plans, and agent templates for the frontend."""
    agent_templates = load_config("agent_templates.json")
    # Extract just the type metadata for the frontend (no persona templates)
    agent_types = {
        k: {"label": v["label"], "icon": v["icon"]}
        for k, v in agent_templates["agent_types"].items()
    }
    return jsonify({
        "success": True,
        "data": {
            "districts": load_config("districts.json")["districts"],
            "scenarios": load_config("scenarios.json")["scenarios"],
            "plans": load_config("plans.json")["plans"],
            "agent_types": agent_types,
        }
    })


@planner_bp.route('/simulate', methods=['POST'])
def simulate():
    """Run a single simulation for one scenario + plan combo.
    Pass mode='agents' for multi-agent simulation."""
    data = request.get_json() or {}
    scenario_id = data.get("scenario_id")
    plan_id = data.get("plan_id")
    mode = data.get("mode", "agents")  # 'monolithic' or 'agents'

    if not scenario_id or not plan_id:
        return jsonify({
            "success": False,
            "error": "scenario_id and plan_id are required"
        }), 400

    err = _check_llm()
    if err:
        return err

    try:
        if mode == "agents":
            result = run_simulation_agents(scenario_id, plan_id)
        else:
            result = run_simulation(scenario_id, plan_id)
        scores = score_run(result)
        return jsonify({
            "success": True,
            "data": {
                "simulation": result,
                "scores": scores,
                "mode": mode,
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@planner_bp.route('/run-matrix', methods=['POST'])
def run_matrix():
    """Run all plans for a scenario (N runs each). Returns ranked comparison."""
    data = request.get_json() or {}
    scenario_id = data.get("scenario_id")
    num_runs = min(data.get("num_runs", 3), 5)  # cap at 5
    mode = data.get("mode", "agents")

    if not scenario_id:
        return jsonify({
            "success": False,
            "error": "scenario_id is required"
        }), 400

    err = _check_llm()
    if err:
        return err

    sim_fn = run_simulation_agents if mode == "agents" else run_simulation
    plans = load_config("plans.json")["plans"]
    results_by_plan = {}
    raw_runs = {}

    try:
        for plan in plans:
            scored_runs = []
            plan_raw = []
            for _ in range(num_runs):
                sim = sim_fn(scenario_id, plan["id"])
                scores = score_run(sim)
                scored_runs.append(scores)
                plan_raw.append({
                    "simulation": sim,
                    "scores": scores,
                })
            results_by_plan[plan["id"]] = aggregate_runs(scored_runs)
            raw_runs[plan["id"]] = plan_raw

        ranked = compare_plans(results_by_plan)

        # Attach plan labels
        plan_labels = {p["id"]: p["label"] for p in plans}
        for entry in ranked:
            entry["label"] = plan_labels.get(entry["plan_id"], entry["plan_id"])

        # Cache results
        os.makedirs(Config.RESULTS_DIR, exist_ok=True)
        cache_path = os.path.join(Config.RESULTS_DIR, f"{scenario_id}.json")
        with open(cache_path, 'w') as f:
            json.dump({
                "scenario_id": scenario_id,
                "num_runs": num_runs,
                "ranked_plans": ranked,
            }, f, indent=2)

        return jsonify({
            "success": True,
            "data": {
                "scenario_id": scenario_id,
                "num_runs": num_runs,
                "ranked_plans": ranked,
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@planner_bp.route('/results/<scenario_id>', methods=['GET'])
def get_results(scenario_id):
    """Return cached results for a scenario, if available."""
    cache_path = os.path.join(Config.RESULTS_DIR, f"{scenario_id}.json")
    if not os.path.exists(cache_path):
        return jsonify({
            "success": False,
            "error": "No cached results for this scenario. Run /api/planner/run-matrix first."
        }), 404

    with open(cache_path, 'r') as f:
        data = json.load(f)
    return jsonify({"success": True, "data": data})
