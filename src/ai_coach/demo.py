"""Synthetic onboarding demo. Never imports synced athlete files."""
from datetime import timedelta

from .coaching import local_date
from .hq import HQAuthority
from .service import CoachService


def seed_demo(journal, hq_token, clock):
    if journal.state()["revision"]:
        if journal.state()["profile"]["athlete_id"] != "demo-athlete":
            raise ValueError("Demo requires its own empty database")
        return
    service = CoachService(journal, clock)
    profile = {"athlete_id": "demo-athlete", "name": "Demo · syntetiske data", "timezone": "Europe/Oslo",
               "weekly_minutes": 240, "max_session_minutes": 75, "available_days": [0, 2, 4, 6],
               "preferred_workouts": ["RUN_EASY", "BIKE_AEROBIC", "SWIM_TECHNIQUE"], "blocked_workouts": [],
               "equipment": ["Løpesko", "Sykkel", "Basseng"], "limitations": "Kun demonstrasjon, ikke personlige treningsråd.", "coaching_tone": "CALM"}
    service.save("profile", profile, 0)
    today = local_date(profile, clock())
    week = today - timedelta(days=today.weekday())
    sessions = [{"id": f"demo-{d}", "date": (week + timedelta(days=d)).isoformat(),
                 "workout_type": w, "duration_min": minutes, "intensity": "EASY", "locked": False,
                 "purpose": purpose} for d, w, minutes, purpose in
                [(0, "RUN_EASY", 45, "Rolig kontinuitet. Registrer hvordan kroppen responderer."),
                 (2, "BIKE_AEROBIC", 60, "Jevn, kontrollert innsats."),
                 (4, "SWIM_TECHNIQUE", 40, "Teknikk og god rytme."),
                 (6, "RUN_EASY", 50, "Avslutt uken med en kontrollert økt.")]]
    HQAuthority(journal, hq_token).import_plan({"athlete_id": "demo-athlete", "version": "hq-demo-1", "authority": "HQ", "week_start": week.isoformat(), "sessions": sessions}, hq_token, 1, clock())
    goal = {"id": "demo-goal", "athlete_id": "demo-athlete", "title": "5 km med tydelig fremgang", "metric": "5 km tid", "unit": "min",
            "baseline": 30, "target": 27, "direction": "DECREASE", "start_date": (today - timedelta(days=28)).isoformat(),
            "target_date": (today + timedelta(days=56)).isoformat(), "measurements": [{"date": today.isoformat(), "value": 28.8, "source": "SYNTHETIC_DEMO"}], "status": "ACTIVE"}
    service.save("goal", goal, journal.state()["revision"])
    for session in sessions:
        if session["date"] <= today.isoformat():
            service.save("checkin", {"id": "check-" + session["id"], "athlete_id": "demo-athlete", "session_id": session["id"],
                "observed_at": clock(), "status": "DONE", "duration_min": session["duration_min"], "rpe": 4, "quality": 0.85,
                "pain": 0, "energy": 4, "recovery": "NORMAL", "notes": "Syntetisk demonstrasjon."}, journal.state()["revision"])
