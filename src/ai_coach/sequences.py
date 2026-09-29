"""Sequence observations preserve both adverse and successful spacing evidence."""
from __future__ import annotations

from datetime import datetime


def _instant(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include an offset")
    return parsed


def _bucket(hours):
    if hours < 18:
        return "LT18H"
    if hours <= 30:
        return "18_30H"
    return "30_48H"


def build_sequence_observations(learning_rows, min_hours=4, max_hours=48):
    """Create adjacent-session observations without case-only sampling.

    GOOD and POOR outcomes are both retained. UNKNOWN stays explicit so missing
    recovery data cannot be silently converted into a successful exposure.
    """
    ordered = [row for row in learning_rows if row.get("started_at")]
    ordered.sort(key=lambda row: _instant(row["started_at"]))
    result = []
    for previous, current in zip(ordered, ordered[1:]):
        prev_time = _instant(previous["started_at"])
        current_time = _instant(current["started_at"])
        hours = (current_time - prev_time).total_seconds() / 3600
        if hours < min_hours or hours > max_hours:
            continue
        prev_type = previous.get("workout_type")
        current_type = current.get("workout_type")
        if not prev_type or not current_type:
            continue
        outcome = current.get("outcome_label", "UNKNOWN")
        completeness = sum(
            current.get(key) is not None
            for key in ("actual", "subjective_response", "recovery_response", "downstream_outcome")
        )
        result.append(
            {
                "id": f"seq:{previous['experience_id']}->{current['experience_id']}",
                "previous_experience_id": previous["experience_id"],
                "target_experience_id": current["experience_id"],
                "hours_between": round(hours, 2),
                "pattern_key": f"{prev_type}->{current_type}:{_bucket(hours)}",
                "outcome": outcome,
                "confidence": round(min(completeness / 4, 1.0), 3),
                "is_negative_evidence": outcome == "GOOD",
                "is_adverse_evidence": outcome == "POOR",
            }
        )
    return result


def summarize_sequences(observations):
    summary = {}
    for obs in observations:
        bucket = summary.setdefault(
            obs["pattern_key"],
            {"exposures": 0, "good": 0, "poor": 0, "unknown": 0},
        )
        bucket["exposures"] += 1
        bucket[obs["outcome"].lower()] += 1
    return summary
