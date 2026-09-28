"""Versioned deterministic policy. No ML, network access, or plan mutation."""
from copy import deepcopy
from datetime import timedelta

from . import __version__
from .contracts import digest, hq_envelope, instant, validate_request
from .features import derive, dose_key
from .taxonomy import TAXONOMY_VERSION

POLICY_VERSION = "rules-0.1.0"
WINDOW_DAYS = 84
RECENT_DAYS = 21
MIN_COMPLETE = 3
MIN_PROGRESS = 5


def evaluate(request):
    data = deepcopy(request)
    validate_request(data)
    # Canonicalize unordered collections so replay and evidence ordering are stable.
    data["source_facts"].sort(key=lambda f: f["id"])
    sessions = data["athlete_data"]["sessions"]
    sessions.sort(key=lambda r: r["planned"]["session_id"])
    for r in sessions:
        r["planned"]["stimuli"].sort()
        for item in (r["planned"], r["actual"], r["response"]):
            if item:
                item["source_fact_ids"].sort()
    target = next(r for r in sessions if r["planned"]["session_id"] == data["target_session_id"])
    cutoff = instant(data["as_of"])
    cohort = [r for r in sessions if r["actual"]
              and cutoff - timedelta(days=WINDOW_DAYS) <= instant(r["actual"]["started_at"]) <= cutoff
              and dose_key(r["planned"]) == dose_key(target["planned"])]
    cohort.sort(key=lambda r: (instant(r["actual"]["started_at"]), r["planned"]["session_id"]))
    features = [derive(r, sessions) for r in cohort]
    complete = [f for f in features if f["complete_response"]]
    n = len(complete)
    successful = sum(f["success"] for f in complete)
    adverse = sum(f["adverse"] for f in complete)
    qualities = [r["actual"]["quality"] for r, f in zip(cohort, features) if f["complete_response"]]
    trend = round(sum(qualities[-2:]) / 2 - sum(qualities[:2]) / 2, 4) if n >= 4 else None
    latest = cohort[-1] if cohort else None
    recent = bool(latest and instant(latest["actual"]["started_at"]) >= cutoff - timedelta(days=RECENT_DAYS))
    recent_related = [r for r in sessions if r["actual"]
                      and r["planned"]["workout_type"] == target["planned"]["workout_type"]
                      and instant(r["actual"]["started_at"]) >= cutoff - timedelta(days=RECENT_DAYS)]
    pain = any(r["response"] and r["response"]["pain"] is not None and r["response"]["pain"] > 0
               for r in recent_related)
    changed_tolerance = any(derive(r, sessions)["adverse"] for r in recent_related if r not in cohort)

    combo = None
    # Only report the most recent exposure's combination; compare like doses.
    combo_key = features[-1]["combination"] if features else None
    if combo_key:
        exposed = [f for f in complete if f["combination"] == combo_key]
        baseline = [f for f in complete if f["combination"] != combo_key]
        combo = {"key": combo_key, "exposed_session_ids": [f["session_id"] for f in exposed],
                 "baseline_session_ids": [f["session_id"] for f in baseline],
                 "poor_rate": sum(f["adverse"] for f in exposed) / len(exposed) if exposed else 0,
                 "baseline_poor_rate": sum(f["adverse"] for f in baseline) / len(baseline) if baseline else None}

    state, reasons = "INSUFFICIENT_EVIDENCE", ["TOO_FEW_COMPLETE_COMPARABLE_SESSIONS"]
    if pain:
        state, reasons = "REDUCE", ["RECENT_REPORTED_PAIN", "PRECAUTIONARY_SIGNAL_NOT_LEARNED_RULE"]
    elif changed_tolerance:
        state, reasons = "CONSOLIDATE", ["RECENT_TOLERANCE_CHANGED_AT_OTHER_DOSE", "HQ_TO_REVIEW_RECENT_RESPONSE"]
    elif combo and recent and len(combo["exposed_session_ids"]) >= 3 and combo["poor_rate"] >= 2 / 3:
        if len(combo["baseline_session_ids"]) >= 3 and combo["baseline_poor_rate"] <= 1 / 3 and combo["poor_rate"] - combo["baseline_poor_rate"] >= 0.4:
            state, reasons = "AVOID_COMBINATION", ["REPEATED_COMBINATION_ASSOCIATION", "BETTER_COMPARABLE_BASELINE", "ASSOCIATION_NOT_CAUSATION"]
        else:
            state, reasons = "MOVE", ["REPEATED_SPACING_SIGNAL", "BASELINE_NOT_CONCLUSIVE", "HQ_TO_REVIEW_SPACING"]
    elif recent and features[-1]["adverse"]:
        state, reasons = "REDUCE", ["RECENT_ADVERSE_RESPONSE", "PRECAUTIONARY_SIGNAL_NOT_LEARNED_RULE"]
    elif n >= MIN_COMPLETE:
        if not recent:
            reasons = ["STALE_COMPARABLE_EVIDENCE"]
        elif adverse / n >= 0.5:
            state, reasons = "REDUCE", ["REPEATED_ADVERSE_RESPONSE"]
        elif not features[-1]["complete_response"]:
            state, reasons = "CONSOLIDATE", ["LATEST_RESPONSE_INCOMPLETE"]
        elif n >= MIN_PROGRESS and successful == n and len(complete) == len(features) and (trend is None or trend >= -0.05):
            state, reasons = "PROGRESS", ["REPEATED_SUCCESSFUL_EXECUTION", "NORMAL_RECOVERY", "NO_DOWNSTREAM_QUALITY_LOSS"]
        elif adverse or (trend is not None and trend < -0.05) or successful / n < 0.8:
            state, reasons = "CONSOLIDATE", ["MIXED_OR_DECLINING_RESPONSE"]
        else:
            state, reasons = "KEEP", ["DOSE_TOLERATED", "PROGRESSION_THRESHOLD_NOT_MET"]

    # Evidence strength is not calibrated statistical or clinical confidence.
    coverage = n / len(features) if features else 0
    consistency = max(successful, adverse, n - successful - adverse) / n if n else 0
    score = round(min(0.95, n / 8) * coverage * (0.5 + 0.5 * consistency) * (1 if recent else 0.5), 3)
    if state in ("INSUFFICIENT_EVIDENCE", "MOVE") or "PRECAUTIONARY_SIGNAL_NOT_LEARNED_RULE" in reasons:
        score = min(score, 0.35)
    if state == "AVOID_COMBINATION":
        score = min(score, round(min(len(combo["exposed_session_ids"]), len(combo["baseline_session_ids"])) / 8, 3))
    related_ids = {f["session_id"] for f in features}
    related_ids.add(target["planned"]["session_id"])
    related_ids.update(r["planned"]["session_id"] for r in recent_related)
    related_ids.update(f["previous_session_id"] for f in features if f["previous_session_id"])
    related_ids.update(r["response"]["next_session_id"] for r in cohort if r["response"] and r["response"]["next_session_id"])
    fact_ids = sorted({ref for r in sessions if r["planned"]["session_id"] in related_ids
                       for item in (r["planned"], r["actual"], r["response"]) if item for ref in item["source_fact_ids"]})
    result = {"schema_version": "1.0", "engine_version": __version__, "policy_version": POLICY_VERSION,
              "taxonomy_version": TAXONOMY_VERSION, "input_hash": digest(data),
              "athlete_id": data["athlete_data"]["athlete_id"], "target_session_id": data["target_session_id"],
              "target_plan_version": target["planned"]["plan_version"], "as_of": data["as_of"],
              "authority": "ADVISORY_ONLY", "requires_hq_approval": True,
              "state": state, "confidence": {"score": score, "label": "HIGH" if score >= 0.8 else "MODERATE" if score >= 0.5 else "LOW",
                  "meaning": "EVIDENCE_STRENGTH_NOT_PROBABILITY"},
              "reason_codes": reasons,
              "constraints": ["HQ_MUST_APPROVE", "NO_DIRECT_PLAN_WRITE", "REVALIDATE_IF_PLAN_OR_TOLERANCE_CHANGED"],
              "evidence": {"session_ids": [f["session_id"] for f in features],
                  "excluded_session_ids": sorted(r["planned"]["session_id"] for r in sessions if r not in cohort),
                  "source_fact_ids": fact_ids, "complete_sessions": n, "successful_sessions": successful,
                  "adverse_sessions": adverse, "quality_trend": trend, "combination": combo},
              "derived_features": features}
    return hq_envelope(result)
