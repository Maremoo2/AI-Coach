"""Small, explicit application contracts, separate from source observations."""
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator

from .contracts import FORMAT_CHECKER, canonical, require
from .taxonomy import WORKOUTS


def obj(properties, required=None):
    return {"type": "object", "properties": properties, "additionalProperties": False,
            "required": list(properties) if required is None else required}


def arr(item, **kwargs):
    return {"type": "array", "items": item, **kwargs}


def num(low=0, high=10000):
    return {"type": "number", "minimum": low, "maximum": high}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


TEXT = {"type": "string", "minLength": 1, "maxLength": 500}
NOTE = {"type": "string", "maxLength": 2000}
ID = {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"}
DATE = {"type": "string", "format": "date"}
TIME = {"type": "string", "format": "date-time"}
PROFILE = obj({"athlete_id": ID, "name": TEXT, "timezone": TEXT,
    "weekly_minutes": num(0, 2400), "max_session_minutes": num(5, 480),
    "available_days": arr({"type": "integer", "minimum": 0, "maximum": 6}, uniqueItems=True),
    "preferred_workouts": arr({"enum": list(WORKOUTS)}, minItems=1, uniqueItems=True),
    "blocked_workouts": arr({"enum": list(WORKOUTS)}, uniqueItems=True),
    "equipment": arr(TEXT, uniqueItems=True), "limitations": NOTE,
    "coaching_tone": {"enum": ["CALM", "DIRECT", "ENCOURAGING"]}})
GOAL = obj({"id": ID, "athlete_id": ID, "title": TEXT, "metric": TEXT, "unit": TEXT,
    "baseline": num(-10000), "target": num(-10000), "direction": {"enum": ["INCREASE", "DECREASE"]},
    "start_date": DATE, "target_date": DATE,
    "measurements": arr(obj({"date": DATE, "value": num(-10000), "source": TEXT})),
    "status": {"enum": ["ACTIVE", "PAUSED", "COMPLETED"]}})
SESSION = obj({"id": ID, "date": DATE, "workout_type": {"enum": list(WORKOUTS)},
    "duration_min": num(5, 480), "intensity": {"enum": ["EASY", "MODERATE", "HARD"]},
    "purpose": TEXT, "locked": {"type": "boolean"}})
PLAN = obj({"athlete_id": ID, "version": ID, "authority": {"const": "HQ"},
    "week_start": DATE, "sessions": arr(SESSION, maxItems=21)})
CHECKIN = obj({"id": ID, "athlete_id": ID, "session_id": ID, "observed_at": TIME,
    "status": {"enum": ["DONE", "PARTIAL", "SKIPPED"]},
    "duration_min": num(0, 480), "rpe": nullable(num(0, 10)),
    "quality": nullable(num(0, 1)), "pain": nullable(num(0, 10)),
    "recovery": {"enum": ["NORMAL", "POOR", "UNKNOWN"]},
    "energy": nullable(num(1, 5)), "notes": NOTE})
CONTRACTS = {"profile": PROFILE, "goal": GOAL, "plan": PLAN, "checkin": CHECKIN}


def validate_app(name, value):
    canonical(value)
    Draft202012Validator(CONTRACTS[name], format_checker=FORMAT_CHECKER).validate(value)
    if name == "profile":
        try:
            ZoneInfo(value["timezone"])
        except ZoneInfoNotFoundError as error:
            raise ValueError("Unknown timezone") from error
        require(not set(value["preferred_workouts"]) & set(value["blocked_workouts"]), "A preferred workout is blocked")
    elif name == "goal":
        require(value["target_date"] > value["start_date"], "Goal deadline must follow start")
        difference = value["target"] - value["baseline"]
        require(difference > 0 if value["direction"] == "INCREASE" else difference < 0, "Goal direction conflicts with target")
        dates = [m["date"] for m in value["measurements"]]
        require(len(dates) == len(set(dates)), "Duplicate measurement date")
        require(all(d >= value["start_date"] for d in dates), "Measurement precedes goal baseline")
    elif name == "plan":
        start = date.fromisoformat(value["week_start"])
        require(start.weekday() == 0, "Plan week must start on Monday")
        ids = [s["id"] for s in value["sessions"]]
        require(len(ids) == len(set(ids)), "Duplicate planned session")
        require(all(0 <= (date.fromisoformat(s["date"]) - start).days < 7 for s in value["sessions"]), "Session outside plan week")
    elif name == "checkin":
        require(value["status"] != "SKIPPED" or value["duration_min"] == 0, "Skipped workout cannot have actual minutes")
    return value
