"""Synthetic athlete only; no synced project data is used in tests."""
from datetime import datetime, timedelta, timezone


def stamp(value):
    return value.isoformat().replace("+00:00", "Z")


def request_for(count=5, poor=(), combinations=()):
    start = datetime(2026, 6, 1, 8, tzinfo=timezone.utc)
    sessions, facts = [], []

    def add(session_id, when, workout="RUN_EASY", bad=False, followup=None):
        plan_ref, actual_ref, response_ref = [f"{session_id}-{kind}" for kind in ("plan", "actual", "response")]
        response_time = when + timedelta(hours=73)
        for ref, kind, recorded in ((plan_ref, "HQ_PLAN", when - timedelta(days=1)),
                                     (actual_ref, "DEVICE", when + timedelta(hours=1)),
                                     (response_ref, "ATHLETE_REPORT", response_time)):
            facts.append({"id": ref, "source": "synthetic-fixture", "recorded_at": stamp(recorded),
                          "kind": kind, "supersedes": None, "payload": {"synthetic": True}})
        sport = "MIXED" if workout == "CROSSFIT" else "RUN"
        shared = {"session_id": session_id, "athlete_id": "synthetic-athlete"}
        record = {
            "planned": {**shared, "source_fact_ids": [plan_ref], "plan_version": "hq-1", "authority": "HQ",
                "scheduled_at": stamp(when), "workout_type": workout, "sport": sport,
                "stimuli": ["AEROBIC"] if workout == "RUN_EASY" else ["ANAEROBIC", "STRENGTH"],
                "dose": {"duration_min": 60, "intervals": 0, "work_min": 0, "rest_min": 0,
                         "intensity": "EASY", "volume": None}},
            "actual": {**shared, "source_fact_ids": [actual_ref], "started_at": stamp(when),
                "duration_min": 60, "execution": "A", "rpe": 5, "quality": 0.5 if bad else 0.9, "volume": None},
            "response": {**shared, "source_fact_ids": [response_ref], "recorded_at": stamp(response_time),
                "pain": 0, "recovery_24h": "NORMAL", "recovery_48h": "NORMAL", "sleep_quality": 0.8,
                "next_session_quality": "GOOD" if followup else None, "next_session_id": followup}}
        sessions.append(record)
        return record

    for i in range(count):
        when = start + timedelta(days=i * 7)
        if i in combinations:
            add(f"prior-{i}", when - timedelta(hours=19), "CROSSFIT")
        add(f"session-{i}", when, bad=i in poor, followup=f"next-{i}")
        follow = add(f"next-{i}", when + timedelta(hours=60))
        # Recovery followups have a different dose and no measured response yet.
        follow["planned"]["dose"]["duration_min"] = 20
        follow["actual"]["duration_min"] = 20
        follow["response"] = None
        facts.pop()  # Unused future response source.
    return {"schema_version": "1.0", "as_of": stamp(start + timedelta(days=(count - 1) * 7 + 4)),
            "target_session_id": f"session-{count - 1}", "source_facts": facts,
            "athlete_data": {"athlete_id": "synthetic-athlete", "sessions": sessions}}


def target(request):
    return next(r for r in request["athlete_data"]["sessions"] if r["planned"]["session_id"] == request["target_session_id"])
