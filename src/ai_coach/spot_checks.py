"""Goal-aligned benchmark scheduling used as periodic spot checks."""

from datetime import datetime, timezone

CHECKS = {
    "RUN_5K": {"sport": "RUN", "min_days": 42, "template_id": "RUN_INTERVAL_5X4", "quality": True},
    "BIKE_FTP": {"sport": "BIKE", "min_days": 42, "template_id": "BIKE_THRESHOLD_4X8", "quality": True},
    "SWIM_CSS": {"sport": "SWIM", "min_days": 35, "template_id": "SWIM_CSS_10X100", "quality": True},
    "STRENGTH_SUBMAX": {"sport": "STRENGTH", "min_days": 42, "template_id": "STRENGTH_EVO_FULLBODY_A", "quality": True},
}


def _instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def due_spot_check(as_of, benchmarks, goal_sports, execution_gate="GREEN", days_since_quality=99):
    if execution_gate != "GREEN" or days_since_quality < 6:
        return None
    latest = {b["kind"]: b.get("last_tested_at") for b in benchmarks}
    now = _instant(as_of)
    candidates = []
    for kind, spec in CHECKS.items():
        if spec["sport"] not in goal_sports:
            continue
        value = latest.get(kind)
        age = 10_000 if not value else (now - _instant(value)).days
        if age >= spec["min_days"]:
            candidates.append((age / spec["min_days"], kind, spec))
    if not candidates:
        return None
    _, kind, spec = sorted(candidates, key=lambda x: (-x[0], x[1]))[0]
    return {
        "kind": kind,
        "sport": spec["sport"],
        "template_id": spec["template_id"],
        "reason": "BENCHMARK_DUE",
        "requires_hq_approval": True,
        "counts_as_quality_session": True,
    }
