"""Helpers that turn normalized source data into immutable experience events."""
from __future__ import annotations

from copy import deepcopy

from .experience import (
    dose_signature,
    make_event,
    normalize_life_context,
    stable_experience_id,
)


class ExperienceCollector:
    def __init__(self, store, athlete_id):
        self.store = store
        self.athlete_id = athlete_id

    def _append(self, **kwargs):
        event = make_event(athlete_id=self.athlete_id, **kwargs)
        return self.store.append(event)

    def capture_plan(self, planned, recorded_at):
        experience_id = stable_experience_id(
            self.athlete_id, planned_session_id=planned["session_id"]
        )
        payload = {
            "session_id": planned["session_id"],
            "plan_version": planned.get("plan_version"),
            "scheduled_at": planned.get("scheduled_at"),
            "workout_type": planned.get("workout_type"),
            "sport": planned.get("sport"),
            "stimuli": deepcopy(planned.get("stimuli") or []),
            "dose": deepcopy(planned.get("dose")),
            "dose_signature": dose_signature(planned),
            "template_id": planned.get("template_id"),
            "key_session": bool(planned.get("key_session", False)),
            "benchmark": bool(planned.get("benchmark", False)),
            "novel_dose": bool(planned.get("novel_dose", False)),
        }
        event_id = self._append(
            experience_id=experience_id,
            event_type="PLANNED_EXPOSURE",
            occurred_at=planned["scheduled_at"],
            recorded_at=recorded_at,
            source_kind="HQ",
            source_ref=f"hq:{planned.get('plan_version')}:{planned['session_id']}",
            payload=payload,
            idempotency_key=f"plan:{planned.get('plan_version')}:{planned['session_id']}",
            supersedes_event_id=None,
        )
        return experience_id, event_id

    def capture_actual(self, experience_id, actual, recorded_at):
        payload = {
            "activity_id": actual.get("activity_id"),
            "planned_session_id": actual.get("planned_session_id"),
            "started_at": actual.get("started_at"),
            "workout_type": actual.get("workout_type"),
            "sport": actual.get("sport"),
            "duration_min": actual.get("duration_min"),
            "execution": actual.get("execution"),
            "rpe": actual.get("rpe"),
            "quality": actual.get("quality"),
            "pain": actual.get("pain"),
            "volume": deepcopy(actual.get("volume")),
            "metrics": deepcopy(actual.get("metrics") or {}),
            "dose_signature": dose_signature(actual),
        }
        activity_id = actual.get("activity_id") or actual.get("source_ref")
        if not activity_id:
            raise ValueError("actual activity requires activity_id or source_ref")
        return self._append(
            experience_id=experience_id,
            event_type="ACTUAL_EXPOSURE",
            occurred_at=actual["started_at"],
            recorded_at=recorded_at,
            source_kind="TREDICT",
            source_ref=f"tredict:{activity_id}",
            payload=payload,
            idempotency_key=f"actual:{activity_id}",
            supersedes_event_id=None,
        )

    def capture_subjective_response(self, experience_id, occurred_at, response, recorded_at):
        payload = {
            "rpe": response.get("rpe"),
            "quality": response.get("quality"),
            "pain": response.get("pain"),
            "felt": response.get("felt"),
            "modified_reason_code": response.get("modified_reason_code"),
        }
        return self._append(
            experience_id=experience_id,
            event_type="SUBJECTIVE_RESPONSE",
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_kind="ATHLETE",
            source_ref=response.get("source_ref", "athlete:post-workout"),
            payload=payload,
            idempotency_key=response.get("idempotency_key"),
            supersedes_event_id=None,
        )

    def capture_recovery(self, experience_id, occurred_at, response, recorded_at):
        payload = {
            "recovery_24h": response.get("recovery_24h"),
            "recovery_48h": response.get("recovery_48h"),
            "pain": response.get("pain"),
            "notes_code": response.get("notes_code"),
        }
        return self._append(
            experience_id=experience_id,
            event_type="RECOVERY_RESPONSE",
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_kind="ATHLETE",
            source_ref=response.get("source_ref", "athlete:recovery"),
            payload=payload,
            idempotency_key=response.get("idempotency_key"),
            supersedes_event_id=None,
        )

    def capture_life_context(self, experience_id, occurred_at, raw_context, recorded_at, source_ref="calendar:derived"):
        payload = normalize_life_context(raw_context)
        return self._append(
            experience_id=experience_id,
            event_type="LIFE_CONTEXT",
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_kind="CALENDAR_DERIVED",
            source_ref=source_ref,
            payload=payload,
            idempotency_key=f"context:{experience_id}:{occurred_at}",
            supersedes_event_id=None,
        )

    def capture_downstream(self, experience_id, occurred_at, outcome, recorded_at):
        payload = {
            "next_session_id": outcome.get("next_session_id"),
            "next_session_quality": outcome.get("next_session_quality"),
            "hours_to_next_session": outcome.get("hours_to_next_session"),
            "performance_change": outcome.get("performance_change"),
        }
        return self._append(
            experience_id=experience_id,
            event_type="DOWNSTREAM_OUTCOME",
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_kind="SYSTEM_DERIVED",
            source_ref=outcome.get("source_ref", "derived:downstream"),
            payload=payload,
            idempotency_key=outcome.get("idempotency_key"),
            supersedes_event_id=None,
        )

    def capture_decision(self, experience_id, occurred_at, decision, recorded_at):
        payload = {
            "decision": decision["decision"],
            "state": decision.get("state"),
            "reason_codes": list(decision.get("reason_codes") or []),
            "confidence": deepcopy(decision.get("confidence")),
            "plan_version": decision.get("plan_version"),
            "requires_hq_approval": decision.get("requires_hq_approval", True),
        }
        return self._append(
            experience_id=experience_id,
            event_type="COACH_DECISION",
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_kind="COACH",
            source_ref=decision.get("source_ref", "coach:v1"),
            payload=payload,
            idempotency_key=decision.get("idempotency_key"),
            supersedes_event_id=None,
        )

    def capture_benchmark(self, experience_id, occurred_at, benchmark, recorded_at):
        payload = {
            "kind": benchmark["kind"],
            "value": benchmark.get("value"),
            "unit": benchmark.get("unit"),
            "protocol_version": benchmark.get("protocol_version"),
            "valid": benchmark.get("valid"),
        }
        return self._append(
            experience_id=experience_id,
            event_type="BENCHMARK_STATE",
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_kind=benchmark.get("source_kind", "TREDICT"),
            source_ref=benchmark.get("source_ref", f"benchmark:{benchmark['kind']}"),
            payload=payload,
            idempotency_key=benchmark.get("idempotency_key"),
            supersedes_event_id=None,
        )

    def correct(self, experience_id, target_event_id, occurred_at, fields, reason_code, recorded_at):
        return self._append(
            experience_id=experience_id,
            event_type="CORRECTION",
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_kind="ATHLETE",
            source_ref="athlete:correction",
            payload={"set": deepcopy(fields), "reason_code": reason_code},
            idempotency_key=None,
            supersedes_event_id=target_event_id,
        )
