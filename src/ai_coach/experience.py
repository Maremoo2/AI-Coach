"""Experience-event contract and privacy-preserving normalization.

The experience layer stores facts that may become useful evidence later without
pretending that every stored field is already a validated training signal.
Raw observations remain immutable; derived features can be recomputed.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from .contracts import digest

EXPERIENCE_SCHEMA_VERSION = "1.0"
EXPERIENCE_POLICY_VERSION = "experience-1.0"

EVENT_TYPES = {
    "PLANNED_EXPOSURE",
    "ACTUAL_EXPOSURE",
    "SUBJECTIVE_RESPONSE",
    "RECOVERY_RESPONSE",
    "LIFE_CONTEXT",
    "DOWNSTREAM_OUTCOME",
    "BENCHMARK_STATE",
    "COACH_DECISION",
    "CORRECTION",
}

SOURCE_KINDS = {
    "HQ",
    "TREDICT",
    "ATHLETE",
    "CALENDAR_DERIVED",
    "COACH",
    "DEVICE",
    "SYSTEM_DERIVED",
}

# Calendar/event titles, attendees, customer names and free text are intentionally
# absent. The experience store needs training-relevant constraints, not a diary.
LIFE_CONTEXT_FIELDS = {
    "workday_load",
    "busy_minutes",
    "available_training_window_min",
    "travel",
    "late_evening_commitment",
    "sleep_status",
    "stress_status",
    "fueling_status",
    "illness_signal",
    "injury_signal",
    "weather_constraint",
}

STATUS_VALUES = {"GREEN", "AMBER", "RED", None}


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include an offset")
    return parsed


def stable_experience_id(
    athlete_id: str,
    *,
    planned_session_id: str | None = None,
    actual_source_ref: str | None = None,
    started_at: str | None = None,
) -> str:
    """Create a stable pseudonymous experience identifier.

    A planned HQ session is the preferred anchor. Orphan activities can still be
    captured using their source reference and timestamp.
    """
    if not athlete_id:
        raise ValueError("athlete_id is required")
    anchor = planned_session_id or actual_source_ref
    if not anchor:
        raise ValueError("planned_session_id or actual_source_ref is required")
    value = {
        "athlete_id": athlete_id,
        "anchor": anchor,
        "started_at": None if planned_session_id else started_at,
    }
    return "exp_" + digest(value)[:24]


def normalize_life_context(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Reduce life/calendar context to training-relevant, low-sensitivity fields."""
    raw = raw or {}
    result: dict[str, Any] = {"context_version": "1.0"}
    for key in LIFE_CONTEXT_FIELDS:
        if key in raw:
            result[key] = deepcopy(raw[key])

    for key in ("sleep_status", "stress_status", "fueling_status"):
        if key in result and result[key] not in STATUS_VALUES:
            raise ValueError(f"{key} must be GREEN, AMBER, RED or null")
    for key in ("travel", "late_evening_commitment", "illness_signal", "injury_signal"):
        if key in result and result[key] is not None and not isinstance(result[key], bool):
            raise ValueError(f"{key} must be boolean or null")
    for key in ("busy_minutes", "available_training_window_min"):
        if key in result and (not isinstance(result[key], (int, float)) or result[key] < 0):
            raise ValueError(f"{key} must be a non-negative number")
    return result


def dose_signature(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a compact comparable dose signature without inventing missing data."""
    if not record:
        return None
    dose = record.get("dose") or {}
    signature = {
        "workout_type": record.get("workout_type"),
        "sport": record.get("sport"),
        "stimuli": sorted(record.get("stimuli") or []),
        "duration_min": dose.get("duration_min", record.get("duration_min")),
        "intensity": dose.get("intensity", record.get("intensity")),
        "intervals": dose.get("intervals"),
        "work_min": dose.get("work_min"),
        "rest_min": dose.get("rest_min"),
        "volume": deepcopy(dose.get("volume", record.get("volume"))),
        "template_id": record.get("template_id"),
    }
    return {key: value for key, value in signature.items() if value is not None and value != []}


def make_event(
    *,
    athlete_id: str,
    experience_id: str,
    event_type: str,
    occurred_at: str,
    recorded_at: str,
    source_kind: str,
    source_ref: str,
    payload: dict[str, Any],
    supersedes_event_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    event = {
        "schema_version": EXPERIENCE_SCHEMA_VERSION,
        "athlete_id": athlete_id,
        "experience_id": experience_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "source": {"kind": source_kind, "ref": source_ref},
        "payload": deepcopy(payload),
        "supersedes_event_id": supersedes_event_id,
        "idempotency_key": idempotency_key,
    }
    identity = {key: event[key] for key in event if key != "event_id"}
    event["event_id"] = "evt_" + digest(identity)[:28]
    validate_event(event)
    return event


def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "event_id",
        "athlete_id",
        "experience_id",
        "event_type",
        "occurred_at",
        "recorded_at",
        "source",
        "payload",
        "supersedes_event_id",
        "idempotency_key",
    }
    if set(event) != required:
        missing = sorted(required - set(event))
        extra = sorted(set(event) - required)
        raise ValueError(f"invalid experience event fields; missing={missing}, extra={extra}")
    if event["schema_version"] != EXPERIENCE_SCHEMA_VERSION:
        raise ValueError("unsupported experience event schema")
    if event["event_type"] not in EVENT_TYPES:
        raise ValueError("unknown experience event type")
    if not event["athlete_id"] or not event["experience_id"] or not event["event_id"]:
        raise ValueError("event identity fields are required")
    _parse_timestamp(event["occurred_at"])
    _parse_timestamp(event["recorded_at"])
    source = event["source"]
    if set(source) != {"kind", "ref"} or source["kind"] not in SOURCE_KINDS or not source["ref"]:
        raise ValueError("invalid event source")
    if not isinstance(event["payload"], dict):
        raise ValueError("event payload must be an object")
    if event["event_type"] == "LIFE_CONTEXT":
        normalized = normalize_life_context(event["payload"])
        if normalized != event["payload"]:
            raise ValueError("LIFE_CONTEXT payload must already be privacy-normalized")
    if event["event_type"] == "CORRECTION":
        if not event["supersedes_event_id"]:
            raise ValueError("CORRECTION requires supersedes_event_id")
        if set(event["payload"]) - {"set", "reason_code"}:
            raise ValueError("CORRECTION payload supports only set and reason_code")
        if not isinstance(event["payload"].get("set"), dict) or not event["payload"]["set"]:
            raise ValueError("CORRECTION payload.set must be a non-empty object")
    elif event["supersedes_event_id"] is not None:
        raise ValueError("only CORRECTION may supersede another event")
    return event


def outcome_label(snapshot: dict[str, Any]) -> str:
    """Conservative label used for later pattern analysis.

    Missing information remains UNKNOWN. A GOOD label requires positive evidence;
    it is never inferred merely from the absence of a problem.
    """
    recovery = snapshot.get("latest", {}).get("RECOVERY_RESPONSE")
    downstream = snapshot.get("latest", {}).get("DOWNSTREAM_OUTCOME")
    actual = snapshot.get("latest", {}).get("ACTUAL_EXPOSURE")

    values = []
    if recovery:
        values.extend([recovery.get("recovery_24h"), recovery.get("recovery_48h")])
    if downstream:
        values.append(downstream.get("next_session_quality"))
    if actual:
        quality = actual.get("quality")
        if quality is not None:
            values.append("GOOD" if quality >= 0.75 else "POOR")

    if any(value == "POOR" for value in values):
        return "POOR"
    known = [value for value in values if value is not None]
    if known and all(value in {"NORMAL", "GOOD"} for value in known):
        return "GOOD"
    return "UNKNOWN"
