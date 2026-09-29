"""Runtime tool and venue policy."""

TOOL_POLICY_VERSION = "1.0"

CAPABILITIES = {
    "TREDICT": {
        "kind": "CONNECTED_DATA",
        "reads": ["activities", "planned_workouts", "capacity", "zones", "training_effort", "body_values"],
        "writes": ["planned_workout_date", "activity_title_notes"],
        "write_policy": "HUMAN_CONFIRMATION_REQUIRED",
    },
    "GOOGLE_CALENDAR": {
        "kind": "CONNECTED_CONTEXT",
        "reads": ["events", "availability"],
        "writes": ["events"],
        "write_policy": "HUMAN_CONFIRMATION_REQUIRED",
    },
    "MYWHOOSH": {"kind": "EXECUTION_VENUE", "reads": [], "writes": [], "write_policy": "NO_LIVE_CONNECTOR"},
    "EVO_GYM": {"kind": "EXECUTION_VENUE", "reads": [], "writes": [], "write_policy": "NO_LIVE_CONNECTOR"},
}


def runtime_reads(mode="DAILY"):
    if mode == "POST_WORKOUT":
        return [
            {"tool": "TREDICT", "resource": "latest_activity", "window": "target_session"},
            {"tool": "TREDICT", "resource": "recent_activities", "window": "14d"},
            {"tool": "TREDICT", "resource": "planned_workouts", "window": "next_7d"},
        ]
    if mode == "WEEKLY":
        return [
            {"tool": "TREDICT", "resource": "recent_activities", "window": "14d"},
            {"tool": "TREDICT", "resource": "planned_workouts", "window": "next_14d"},
            {"tool": "TREDICT", "resource": "capacity", "window": "current"},
            {"tool": "TREDICT", "resource": "zones", "window": "current"},
            {"tool": "GOOGLE_CALENDAR", "resource": "events", "window": "next_14d"},
        ]
    return [
        {"tool": "TREDICT", "resource": "recent_activities", "window": "14d"},
        {"tool": "TREDICT", "resource": "planned_workouts", "window": "today+7d"},
        {"tool": "GOOGLE_CALENDAR", "resource": "events", "window": "today+7d"},
    ]


def choose_venue(workout, environment):
    available = set(environment.get("available_tools", []))
    season = environment.get("season")
    preferred = environment.get("preferred_venues", {})
    sport = workout["sport"]
    supported = workout.get("venues", [])

    explicit = preferred.get(sport)
    if explicit in supported and (explicit not in CAPABILITIES or explicit in available):
        return explicit
    if sport == "BIKE" and season == "WINTER" and "MYWHOOSH" in available and "MYWHOOSH" in supported:
        return "MYWHOOSH"
    if sport == "STRENGTH" and "EVO_GYM" in available and "EVO_GYM" in supported:
        return "EVO_GYM"
    if sport == "RUN" and environment.get("prefer_indoor_run") and "EVO_GYM" in available and "EVO_TREADMILL" in supported:
        return "EVO_TREADMILL"
    for venue in supported:
        if venue in ("OUTDOOR", "POOL", "HOME") or venue in available:
            return venue
    return supported[0] if supported else None
