"""Quick test: run one multi-agent simulation and print results."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.mirofish_adapter import run_simulation_agents

print("Running multi-agent simulation: hostile_agitation_north × northern_shield")
print("This calls the LLM once per agent per timestep (~14 agents × 13 steps)...")
print()

result = run_simulation_agents("hostile_agitation_north", "northern_shield")

print(f"Timeline steps: {len(result['timeline'])}")
print(f"Agents: {len(result.get('agent_manifest', []))}")
print(f"Cascades: {len(result['cascades'])}")
print(f"Narrative: {result['final_summary']['narrative']}")
print()

# Show agent manifest
print("AGENT MANIFEST:")
for a in result.get("agent_manifest", []):
    print(f"  #{a['agent_id']} {a['name']:25s} {a['type']:12s} in {a['district']}")
print()

# Show timeline summary
print("TIMELINE:")
for step in result["timeline"]:
    hour = step["hour"]
    statuses = {did: info["status"] for did, info in step["districts"].items()}
    critical = [d for d, s in statuses.items() if s == "CRITICAL"]
    protest = [d for d, s in statuses.items() if s == "PROTEST"]
    tense = [d for d, s in statuses.items() if s == "TENSE"]
    print(f"  T+{hour:>3d}h  CRITICAL={len(critical)}  PROTEST={len(protest)}  TENSE={len(tense)}")
    
    # Show group breakdowns for first few districts with agents
    for did, info in sorted(step["districts"].items()):
        groups = info.get("groups", [])
        if groups:
            g_parts = []
            for g in groups:
                g_parts.append(f"{g['group']}:{g['escalation_level']}({g['sentiment']:+.1f})")
            print(f"         {did}: {', '.join(g_parts)}")
            for g in groups:
                for post in g.get("sample_posts", []):
                    print(f"           \"{post[:80]}\"")

print()
print("Scores:")
from app.services.scorer import score_run
scores = score_run(result)
for k, v in scores.items():
    if k != "district_scores":
        print(f"  {k}: {v}")
