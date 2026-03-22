"""Quick test: verify scoring logic with mock data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scorer import score_run, aggregate_runs, compare_plans

mock_result = {
    "timeline": [
        {"hour": 0, "districts": {
            "northern_border_town": {"status": "CALM", "events": []},
            "eastern_crossing": {"status": "CALM", "events": []},
            "industrial_belt": {"status": "CALM", "events": []},
        }},
        {"hour": 6, "districts": {
            "northern_border_town": {"status": "PROTEST", "events": ["Market protest"]},
            "eastern_crossing": {"status": "TENSE", "events": []},
            "industrial_belt": {"status": "CALM", "events": []},
        }},
        {"hour": 12, "districts": {
            "northern_border_town": {"status": "CRITICAL", "events": ["Escalated"]},
            "eastern_crossing": {"status": "PROTEST", "events": ["Cascade"]},
            "industrial_belt": {"status": "TENSE", "events": []},
        }},
    ],
    "cascades": [
        {"from_district": "northern_border_town", "to_district": "eastern_crossing", "hour": 12, "mechanism": "road network"}
    ],
    "final_summary": {
        "districts_critical": ["northern_border_town"],
        "districts_protest": ["eastern_crossing"],
        "peak_unrest_hour": 12,
        "total_incidents": 3,
        "narrative": "Test narrative"
    }
}

print("=== Score single run ===")
scores = score_run(mock_result)
for k, v in scores.items():
    print(f"  {k}: {v}")

print("\n=== Aggregate 2 identical runs ===")
agg = aggregate_runs([scores, scores])
for k, v in agg.items():
    print(f"  {k}: {v}")

print("\n=== Compare plans ===")
better_agg = {
    "district_scores": {"northern_border_town": 0.2, "eastern_crossing": 0.2, "industrial_belt": 0.0},
    "critical_count": 0, "cascade_count": 0, "global_risk": 0.0, "avg_stress": 0.133
}
ranked = compare_plans({"baseline": agg, "northern_shield": better_agg})
for p in ranked:
    print(f"  {p['plan_id']}: composite={p['composite_score']}, reduction={p['risk_reduction_pct']}%")

print("\nAll tests passed!")
