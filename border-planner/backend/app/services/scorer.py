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


def recommend_containment(sim_result, plans, world_id=None):
    """Given current sim state, score every plan's projected effectiveness
    and return the best containment recommendation with reasoning."""
    from .seed_builder import load_config

    timeline = sim_result.get("timeline", [])
    if not timeline:
        return {"recommended_plan": None, "reason": "No simulation data available."}

    last_step = timeline[-1]
    districts_state = last_step.get("districts", {})

    # Compute current distress per district
    district_distress = {}
    critical_districts = []
    for did, info in districts_state.items():
        score = STATUS_SCORES.get(info.get("status", "CALM"), 0)
        groups = info.get("groups", [])
        escalated = sum(1 for g in groups if g.get("escalation_level") in ("organizing", "protesting", "clashing"))
        esc_factor = escalated / max(len(groups), 1)
        distress = max(0.05, min(1.0, score * 0.65 + esc_factor * 0.35))
        district_distress[did] = distress
        if score >= 1.0:
            critical_districts.append(did)

    # Score each plan based on how well its deployments cover distressed areas
    plan_scores = []
    for plan in plans:
        pid = plan["id"]
        pku_set = set(plan.get("peacekeepers", []))
        sensor_set = set(plan.get("sensors", []))

        coverage = 0.0
        for did, distress in district_distress.items():
            if did in pku_set:
                coverage += distress * 0.6
            if did in sensor_set:
                coverage += distress * 0.3

        total_distress = sum(district_distress.values()) or 1.0
        coverage_ratio = coverage / total_distress
        # Penalize plans that leave critical districts uncovered
        uncovered_critical = [d for d in critical_districts if d not in pku_set]
        penalty = len(uncovered_critical) * 0.15
        final_score = max(0, coverage_ratio - penalty)

        plan_scores.append({
            "plan_id": pid,
            "label": plan.get("label", pid),
            "containment_score": round(final_score, 4),
            "coverage_ratio": round(coverage_ratio, 4),
            "uncovered_critical": uncovered_critical,
            "peacekeepers": plan.get("peacekeepers", []),
            "sensors": plan.get("sensors", []),
        })

    plan_scores.sort(key=lambda x: -x["containment_score"])
    best = plan_scores[0] if plan_scores else None

    if not best:
        return {"recommended_plan": None, "reason": "No plans available."}

    crit_str = ", ".join(critical_districts) if critical_districts else "none"
    reason_parts = [
        f"Highest containment coverage ({best['coverage_ratio']:.0%}) of distressed districts.",
    ]
    if best["uncovered_critical"]:
        reason_parts.append(f"Warning: {', '.join(best['uncovered_critical'])} critical but uncovered by peacekeepers.")
    else:
        reason_parts.append("All critical districts are covered by peacekeeper deployments.")
    reason_parts.append(f"Critical districts: {crit_str}.")

    return {
        "recommended_plan": best["plan_id"],
        "recommended_label": best["label"],
        "containment_score": best["containment_score"],
        "reason": " ".join(reason_parts),
        "all_plans": plan_scores,
        "district_distress": {k: round(v, 3) for k, v in district_distress.items()},
        "critical_districts": critical_districts,
    }


def build_explainability(sim_results_by_plan, scores_by_plan, plans, recommended_plan_id=None):
    """Build a full explainability payload comparing plans with evidence.

    Args:
        sim_results_by_plan: {plan_id: [sim_result, ...]}  (list of raw sim runs per plan)
        scores_by_plan: {plan_id: [score_dict, ...]}  (list of scored runs per plan)
        plans: list of plan dicts from config
        recommended_plan_id: optional pre-selected recommended plan

    Returns dict with counterfactual, evidence, confidence, and export-ready summary.
    """
    import statistics

    plan_lookup = {p["id"]: p for p in plans}
    baseline_id = "baseline"
    rec_id = recommended_plan_id

    # If no recommendation given, pick the plan with lowest avg composite
    if not rec_id:
        best_score = float("inf")
        for pid, runs in scores_by_plan.items():
            if not runs:
                continue
            agg = aggregate_runs(runs)
            cascade_norm = min(agg["cascade_count"] / 5.0, 1.0)
            comp = 0.5 * agg["global_risk"] + 0.3 * agg["avg_stress"] + 0.2 * cascade_norm
            if comp < best_score:
                best_score = comp
                rec_id = pid
    if not rec_id:
        rec_id = baseline_id

    # --- Confidence bands (per-plan variance) ---
    confidence = {}
    for pid, runs in scores_by_plan.items():
        if len(runs) < 2:
            confidence[pid] = {
                "global_risk": {"mean": runs[0]["global_risk"] if runs else 0, "std": 0, "min": runs[0]["global_risk"] if runs else 0, "max": runs[0]["global_risk"] if runs else 0, "n": len(runs)},
                "avg_stress": {"mean": runs[0]["avg_stress"] if runs else 0, "std": 0, "min": runs[0]["avg_stress"] if runs else 0, "max": runs[0]["avg_stress"] if runs else 0, "n": len(runs)},
                "cascade_count": {"mean": runs[0]["cascade_count"] if runs else 0, "std": 0, "min": runs[0]["cascade_count"] if runs else 0, "max": runs[0]["cascade_count"] if runs else 0, "n": len(runs)},
                "critical_count": {"mean": runs[0]["critical_count"] if runs else 0, "std": 0, "min": runs[0]["critical_count"] if runs else 0, "max": runs[0]["critical_count"] if runs else 0, "n": len(runs)},
            }
            continue
        band = {}
        for metric in ("global_risk", "avg_stress", "cascade_count", "critical_count"):
            vals = [r[metric] for r in runs]
            band[metric] = {
                "mean": round(statistics.mean(vals), 4),
                "std": round(statistics.stdev(vals), 4),
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
                "n": len(vals),
            }
        confidence[pid] = band

    # --- Counterfactual: recommended vs baseline ---
    def plan_agg(pid):
        runs = scores_by_plan.get(pid, [])
        return aggregate_runs(runs) if runs else None

    rec_agg = plan_agg(rec_id)
    base_agg = plan_agg(baseline_id)

    counterfactual = None
    if rec_agg and base_agg and rec_id != baseline_id:
        counterfactual = {
            "recommended": {
                "plan_id": rec_id,
                "label": plan_lookup.get(rec_id, {}).get("label", rec_id),
                "global_risk": round(rec_agg["global_risk"], 4),
                "avg_stress": round(rec_agg["avg_stress"], 4),
                "cascade_count": round(rec_agg["cascade_count"], 2),
                "critical_count": round(rec_agg["critical_count"], 2),
                "district_scores": {k: round(v, 3) for k, v in rec_agg["district_scores"].items()},
            },
            "baseline": {
                "plan_id": baseline_id,
                "label": plan_lookup.get(baseline_id, {}).get("label", "Baseline"),
                "global_risk": round(base_agg["global_risk"], 4),
                "avg_stress": round(base_agg["avg_stress"], 4),
                "cascade_count": round(base_agg["cascade_count"], 2),
                "critical_count": round(base_agg["critical_count"], 2),
                "district_scores": {k: round(v, 3) for k, v in base_agg["district_scores"].items()},
            },
            "deltas": {
                "global_risk": round(base_agg["global_risk"] - rec_agg["global_risk"], 4),
                "avg_stress": round(base_agg["avg_stress"] - rec_agg["avg_stress"], 4),
                "cascade_count": round(base_agg["cascade_count"] - rec_agg["cascade_count"], 2),
                "critical_count": round(base_agg["critical_count"] - rec_agg["critical_count"], 2),
            },
            "district_deltas": {
                did: round(base_agg["district_scores"].get(did, 0) - rec_agg["district_scores"].get(did, 0), 3)
                for did in set(list(base_agg["district_scores"].keys()) + list(rec_agg["district_scores"].keys()))
            },
        }

    # --- Evidence: "Why this plan" from specific events ---
    evidence = []
    rec_sims = sim_results_by_plan.get(rec_id, [])
    base_sims = sim_results_by_plan.get(baseline_id, [])

    # Collect cascade events from baseline that are absent in recommended
    base_cascades = set()
    for sim in base_sims:
        for c in sim.get("cascades", []):
            base_cascades.add((c.get("from_district", ""), c.get("to_district", ""), c.get("mechanism", "")))
    rec_cascades = set()
    for sim in rec_sims:
        for c in sim.get("cascades", []):
            rec_cascades.add((c.get("from_district", ""), c.get("to_district", ""), c.get("mechanism", "")))
    prevented = base_cascades - rec_cascades
    for frm, to, mech in list(prevented)[:5]:
        evidence.append({
            "type": "cascade_prevented",
            "summary": f"Cascade {frm} → {to} ({mech}) observed in baseline but prevented by recommended plan.",
            "severity": "high",
        })

    # District-level improvements
    if counterfactual:
        for did, delta in counterfactual["district_deltas"].items():
            if delta >= 0.15:
                rec_val = counterfactual["recommended"]["district_scores"].get(did, 0)
                base_val = counterfactual["baseline"]["district_scores"].get(did, 0)
                evidence.append({
                    "type": "district_improvement",
                    "district": did,
                    "summary": f"{did}: peak stress drops from {base_val:.2f} to {rec_val:.2f} (Δ{delta:+.2f}).",
                    "severity": "medium" if delta < 0.3 else "high",
                })

    # Check if recommended plan covers critical districts
    rec_plan_cfg = plan_lookup.get(rec_id, {})
    rec_pku = set(rec_plan_cfg.get("peacekeepers", []))
    if rec_agg:
        for did, score in rec_agg["district_scores"].items():
            if score >= 0.5 and did in rec_pku:
                evidence.append({
                    "type": "peacekeeper_coverage",
                    "district": did,
                    "summary": f"Peacekeeper deployed to high-stress district {did} (peak {score:.2f}).",
                    "severity": "medium",
                })

    # Narrative summary
    narrative_parts = []
    if counterfactual:
        d = counterfactual["deltas"]
        narrative_parts.append(
            f"Compared to baseline, the recommended plan reduces global risk by {d['global_risk']:.2f}, "
            f"average stress by {d['avg_stress']:.2f}, and cascades by {d['cascade_count']:.1f}."
        )
    if prevented:
        narrative_parts.append(f"{len(prevented)} cascade event(s) observed in baseline are prevented.")
    covered_crits = []
    if rec_agg:
        for did, score in rec_agg["district_scores"].items():
            if score >= 1.0 and did in rec_pku:
                covered_crits.append(did)
    if covered_crits:
        narrative_parts.append(f"Critical districts with peacekeeper coverage: {', '.join(covered_crits)}.")
    narrative = " ".join(narrative_parts) if narrative_parts else "Insufficient data for comparative analysis."

    return {
        "recommended_plan": rec_id,
        "recommended_label": plan_lookup.get(rec_id, {}).get("label", rec_id),
        "counterfactual": counterfactual,
        "evidence": evidence[:12],
        "confidence": confidence,
        "narrative": narrative,
        "export_summary": {
            "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "recommended_plan": rec_id,
            "narrative": narrative,
            "evidence_count": len(evidence),
            "counterfactual": counterfactual,
            "confidence": confidence,
        },
    }
