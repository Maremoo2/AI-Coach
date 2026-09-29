"""Pure helpers for the live Tredict -> Experience Ledger runtime.

The actual connector calls are made by the external conversational runtime.
This module defines stable keys and reconciliation behavior so the live loop can
later migrate to another scheduler without changing the persistence contract.
"""
from __future__ import annotations

from .reconciliation import reconcile_one

LEDGER_VERSION = "1.0"

EVENT_COLUMNS = [
    "event_key",
    "experience_key",
    "event_type",
    "occurred_at_utc",
    "source_kind",
    "source_ref",
    "sport",
    "plan_id",
    "activity_id",
    "match_status",
    "payload_json",
    "collected_at_utc",
]

RECOVERY_COLUMNS = [
    "date",
    "sleep_sec",
    "sleep_baseline_sec",
    "hrv_rmssd",
    "hrv_baseline",
    "source_ref",
    "collected_at_utc",
]

PENDING_COLUMNS = [
    "question_key",
    "experience_key",
    "activity_id",
    "stage",
    "fields_needed_json",
    "reason_codes_json",
    "status",
    "detected_at_utc",
    "asked_at_utc",
    "answered_at_utc",
]

SYNC_COLUMNS = ["key", "value", "updated_at_utc"]


def plan_event_key(plan):
    return f"PLANNED:{plan['id']}:{plan['updatedAt']}"


def activity_event_key(activity):
    return f"ACTUAL:{activity['id']}"


def recovery_key(kind, date):
    if kind not in {"SLEEP", "HRV"}:
        raise ValueError("kind must be SLEEP or HRV")
    return f"{kind}:{date}"


def runtime_experience_key(*, plan_id=None, activity_id=None):
    if plan_id:
        return f"plan:{plan_id}"
    if activity_id:
        return f"activity:{activity_id}"
    raise ValueError("plan_id or activity_id is required")


def reconcile_runtime_plan(planned, activity_candidates, tolerance_hours=8):
    normalized_plan = {
        "session_id": planned["id"],
        "sport": planned["sportType"],
        "scheduled_at": planned["date"],
    }
    normalized_actuals = [
        {
            **activity,
            "activity_id": activity["id"],
            "planned_session_id": activity.get("planned_session_id"),
            "sport": activity.get("sportType"),
            "started_at": activity.get("date"),
        }
        for activity in activity_candidates
    ]
    result = reconcile_one(normalized_plan, normalized_actuals, tolerance_hours)
    if result["actual"] is not None:
        result["actual_id"] = result["actual"]["id"]
    else:
        result["actual_id"] = None
    return result


def information_rich_plan(plan):
    text = " ".join(
        str(plan.get(key) or "") for key in ("title", "notes")
    ).lower()
    markers = (
        "benchmark",
        "test",
        "terskel",
        "threshold",
        "sweet spot",
        "sweetspot",
        "vo2",
        "race",
        "lang ",
        "long ",
        "brick",
    )
    return any(marker in text for marker in markers)


def pending_question_fields(plan=None, activity=None):
    """Minimal fields worth asking for after an information-rich exposure."""
    plan = plan or {}
    activity = activity or {}
    fields = []
    if information_rich_plan(plan):
        if activity.get("rpe") is None:
            fields.append("rpe")
        if activity.get("quality") is None:
            fields.append("quality")
        if activity.get("pain") is None:
            fields.append("pain")
    if activity.get("execution") in {"B", "C"}:
        fields.append("modified_reason_code")
    return list(dict.fromkeys(fields))
