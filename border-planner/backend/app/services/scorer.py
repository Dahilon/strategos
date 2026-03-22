STATUS_SCORES = {
    "CALM": 0.0,
    "TENSE": 0.2,
    "PROTEST": 0.5,
    "CRITICAL": 1.0,
}


def score_run(sim_result):
    """Score a single simulation run.

    Returns a dict with:
      - district_scores: {district_id: peak_score}  (0.0-1.0)
      - critical_count: how many districts hit CRITICAL
      - cascade_count: number of cross-district contagion events
      - global_risk: 0-1 probability proxy for multi-district crisis
      - avg_stress: mean peak score across all districts
    """
    district_peaks = {}

    for timestep in sim_result["timeline"]:
        for did, info in timestep["districts"].items():
            score = STATUS_SCORES.get(info["status"], 0)
            district_peaks[did] = max(district_peaks.get(did, 0), score)

    critical_count = sum(1 for v in district_peaks.values() if v >= 1.0)
    cascades = len(sim_result.get("cascades", []))

    return {
        "district_scores": district_peaks,
        "critical_count": critical_count,
        "cascade_count": cascades,
        "global_risk": 1.0 if critical_count >= 3 else critical_count / 3.0,
        "avg_stress": sum(district_peaks.values()) / max(len(district_peaks), 1),
        "narrative": sim_result.get("final_summary", {}).get("narrative", ""),
    }


def aggregate_runs(scored_runs):
    """Average scores across multiple runs of the same scenario+plan."""
    n = len(scored_runs)
    if n == 0:
        return {}

    all_dids = list(scored_runs[0]["district_scores"].keys())

    avg_district = {}
    for did in all_dids:
        avg_district[did] = sum(
            r["district_scores"].get(did, 0) for r in scored_runs
        ) / n

    return {
        "district_scores": avg_district,
        "critical_count": sum(r["critical_count"] for r in scored_runs) / n,
        "cascade_count": sum(r["cascade_count"] for r in scored_runs) / n,
        "global_risk": sum(r["global_risk"] for r in scored_runs) / n,
        "avg_stress": sum(r["avg_stress"] for r in scored_runs) / n,
    }


def compare_plans(results_by_plan):
    """Compare aggregated results across all plans for a scenario.

    Returns a list of plan results sorted by composite score (best first).
    Each entry includes risk_reduction_pct relative to baseline.
    """
    def composite(agg):
        cascade_norm = min(agg["cascade_count"] / 5.0, 1.0)
        return 0.5 * agg["global_risk"] + 0.3 * agg["avg_stress"] + 0.2 * cascade_norm

    baseline_score = composite(
        results_by_plan.get("baseline", list(results_by_plan.values())[0])
    )

    ranked = []
    for plan_id, agg in results_by_plan.items():
        score = composite(agg)
        if baseline_score > 0:
            reduction = (baseline_score - score) / baseline_score * 100
        else:
            reduction = 0.0

        ranked.append({
            "plan_id": plan_id,
            "composite_score": round(score, 4),
            "global_risk": round(agg["global_risk"], 4),
            "avg_stress": round(agg["avg_stress"], 4),
            "cascade_count": round(agg["cascade_count"], 2),
            "critical_count": round(agg["critical_count"], 2),
            "district_scores": {k: round(v, 3) for k, v in agg["district_scores"].items()},
            "risk_reduction_pct": round(reduction, 1),
        })

    ranked.sort(key=lambda x: x["composite_score"])
    return ranked
