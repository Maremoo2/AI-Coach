"""Conservative pattern learning from repeated coach observations."""

from collections import defaultdict
from statistics import median

PERSONALIZATION_VERSION = "1.0"


def infer_personal_rules(observations, corrections=None):
    corrections = corrections or {}
    grouped = defaultdict(list)
    for obs in observations:
        grouped[obs["pattern_key"]].append(obs)

    rules = []
    for key in sorted(grouped):
        rows = grouped[key]
        outcomes = [r["outcome"] for r in rows]
        counts = {name: outcomes.count(name) for name in sorted(set(outcomes))}
        dominant, dominant_n = max(counts.items(), key=lambda item: (item[1], item[0]))
        confidence = median(float(r.get("confidence", 0.0)) for r in rows)
        consistency = dominant_n / len(rows)

        status = "OBSERVATION"
        if len(rows) >= 3 and consistency >= 2 / 3 and confidence >= 0.4:
            status = "CANDIDATE_RULE"
        if len(rows) >= 5 and consistency >= 0.8 and confidence >= 0.6:
            status = "ESTABLISHED_RULE"
        if key in corrections:
            dominant = corrections[key]
            status = "USER_CORRECTED_RULE"

        rules.append({
            "pattern_key": key,
            "outcome": dominant,
            "status": status,
            "evidence_count": len(rows),
            "consistency": round(consistency, 3),
            "median_confidence": round(confidence, 3),
            "source_observation_ids": sorted(r["id"] for r in rows),
            "can_write_plan": False,
        })
    return rules
