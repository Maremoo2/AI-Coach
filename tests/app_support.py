from datetime import datetime, timezone

NOW = "2026-07-03T12:00:00+00:00"


def profile():
    return {"athlete_id": "synthetic-athlete", "name": "Synthetic athlete", "timezone": "Europe/Oslo",
            "weekly_minutes": 240, "max_session_minutes": 90, "available_days": list(range(7)),
            "preferred_workouts": ["RUN_EASY", "BIKE_AEROBIC"], "blocked_workouts": [],
            "equipment": [], "limitations": "", "coaching_tone": "CALM"}


def plan():
    return {"athlete_id": "synthetic-athlete", "authority": "HQ", "version": "hq-test-1", "week_start": "2026-06-29",
            "sessions": [{"id": "done", "date": "2026-06-29", "workout_type": "RUN_EASY", "duration_min": 60,
                          "intensity": "EASY", "purpose": "Recorded session", "locked": False},
                         {"id": "next", "date": "2026-07-04", "workout_type": "RUN_EASY", "duration_min": 60,
                          "intensity": "EASY", "purpose": "Next session", "locked": False}]}


def checkin():
    return {"id": "check-1", "athlete_id": "synthetic-athlete", "session_id": "done", "observed_at": "2026-07-02T12:00:00Z",
            "status": "DONE", "duration_min": 60, "rpe": 5, "quality": 0.9, "pain": 0,
            "recovery": "NORMAL", "energy": 4, "notes": "Synthetic"}


def goal():
    return {"id": "goal-1", "athlete_id": "synthetic-athlete", "title": "5 km", "metric": "5 km time", "unit": "min",
            "baseline": 30, "target": 27, "direction": "DECREASE", "start_date": "2026-06-01", "target_date": "2026-09-01",
            "measurements": [], "status": "ACTIVE"}
