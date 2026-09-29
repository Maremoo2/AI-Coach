"""Deterministic HQ-plan ↔ actual-activity reconciliation."""
from __future__ import annotations

from datetime import datetime


def _time(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include an offset")
    return parsed


def reconcile_one(planned, actual_candidates, tolerance_hours=8):
    """Match one planned session without guessing through ambiguity.

    Exact source links win. Otherwise a unique same-sport activity within the
    configured time window can be linked. Ambiguous candidates are surfaced for
    review rather than silently attached.
    """
    session_id = planned["session_id"]
    exact = [a for a in actual_candidates if a.get("planned_session_id") == session_id]
    if len(exact) == 1:
        return {"status": "EXACT", "actual": exact[0], "candidate_ids": [exact[0].get("activity_id")]}
    if len(exact) > 1:
        return {
            "status": "AMBIGUOUS",
            "actual": None,
            "candidate_ids": [a.get("activity_id") for a in exact],
        }

    scheduled = _time(planned.get("scheduled_at"))
    if scheduled is None:
        return {"status": "UNMATCHED", "actual": None, "candidate_ids": []}

    matches = []
    for actual in actual_candidates:
        if actual.get("sport") != planned.get("sport"):
            continue
        started = _time(actual.get("started_at"))
        if started is None:
            continue
        delta_h = abs((started - scheduled).total_seconds()) / 3600
        if delta_h <= tolerance_hours:
            matches.append((delta_h, actual))

    if len(matches) == 1:
        actual = matches[0][1]
        return {"status": "TIME_SPORT", "actual": actual, "candidate_ids": [actual.get("activity_id")]}
    if len(matches) > 1:
        matches.sort(key=lambda pair: pair[0])
        return {
            "status": "AMBIGUOUS",
            "actual": None,
            "candidate_ids": [a.get("activity_id") for _, a in matches],
        }
    return {"status": "UNMATCHED", "actual": None, "candidate_ids": []}


def reconcile_window(planned_sessions, actual_sessions, tolerance_hours=8):
    """Return reconciliation results without mutating either source dataset."""
    return [
        {
            "planned_session_id": planned["session_id"],
            **reconcile_one(planned, actual_sessions, tolerance_hours=tolerance_hours),
        }
        for planned in planned_sessions
    ]
