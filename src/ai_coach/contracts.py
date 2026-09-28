"""Strict wire validation and cross-record invariants at the HQ boundary."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from importlib.resources import files

from jsonschema import Draft202012Validator, FormatChecker

from .taxonomy import WORKOUTS

FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(ValueError, TypeError))
def timestamp_format(value):
    # Do not depend on jsonschema's optional RFC3339 format extra being installed.
    if not isinstance(value, str):
        return True
    pattern = r"\d{4}-\d{2}-\d{2}[Tt](?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)"
    return bool(re.fullmatch(pattern, value)) and instant(value).tzinfo is not None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def instant(value):
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00"))


def validate(name, value):
    # JSON Schema's numeric checks alone do not reject Python NaN/Infinity.
    canonical(value)
    schema = json.loads(files("ai_coach.schemas").joinpath(f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FORMAT_CHECKER).validate(value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_request(request):
    validate("evaluation_request", request)
    cutoff = instant(request["as_of"])
    facts = request["source_facts"]
    fact_map = {f["id"]: f for f in facts}
    require(len(fact_map) == len(facts), "Duplicate source fact id")
    superseded = set()
    for fact in facts:
        require(instant(fact["recorded_at"]) <= cutoff, "Future source fact")
        old_id = fact["supersedes"]
        if old_id is not None:
            require(fact["kind"] == "CORRECTION", "Only a correction can supersede a fact")
            require(old_id in fact_map and old_id != fact["id"], "Invalid correction reference")
            require(old_id not in superseded, "Ambiguous correction branch")
            require(instant(fact_map[old_id]["recorded_at"]) < instant(fact["recorded_at"]), "Correction must be newer")
            superseded.add(old_id)
    sessions = request["athlete_data"]["sessions"]
    athlete = request["athlete_data"]["athlete_id"]
    by_id = {r["planned"]["session_id"]: r for r in sessions}
    require(len(by_id) == len(sessions), "Duplicate session id")
    require(request["target_session_id"] in by_id, "Unknown target session")
    for record in sessions:
        planned, actual, response = (record[k] for k in ("planned", "actual", "response"))
        session_id = planned["session_id"]
        require(planned["sport"] == WORKOUTS[planned["workout_type"]][0], "Workout/sport mismatch")
        dose = planned["dose"]
        require((dose["intervals"] == 0) == (dose["work_min"] == 0), "Inconsistent interval dose")
        require(dose["intervals"] * dose["work_min"] + max(0, dose["intervals"] - 1) * dose["rest_min"] <= dose["duration_min"], "Intervals exceed total duration")
        for item in (planned, actual, response):
            if item is None:
                continue
            require(item["athlete_id"] == athlete and item["session_id"] == session_id, "Cross-athlete/session data")
            for ref in item["source_fact_ids"]:
                require(ref in fact_map, "Unknown source fact")
                require(ref not in superseded, "Normalized data references superseded fact")
        require(response is None or actual is not None, "Response without actual workout")
        if actual:
            ended = instant(actual["started_at"]) + timedelta(minutes=actual["duration_min"])
            require(ended <= cutoff, "Future or unfinished actual workout")
        if response:
            recorded = instant(response["recorded_at"])
            require(ended <= recorded <= cutoff, "Response outside observation time")
            for hours in (24, 48):
                if response[f"recovery_{hours}h"] is not None:
                    require(recorded >= ended + timedelta(hours=hours), "Premature recovery observation")
            next_id = response["next_session_id"]
            require((next_id is None) == (response["next_session_quality"] is None), "Next-session quality needs a session link")
            if next_id is not None:
                require(next_id in by_id and next_id != session_id, "Invalid next-session reference")
                nxt = by_id[next_id]["actual"]
                require(nxt is not None, "Next session has no actual workout")
                next_start = instant(nxt["started_at"])
                require(ended <= next_start and next_start + timedelta(minutes=nxt["duration_min"]) <= recorded, "Invalid next-session chronology")
    return request


def hq_envelope(recommendation):
    """Validate and copy the advisory output. Deliberately no plan writer."""
    validate("recommendation", recommendation)
    return json.loads(canonical(recommendation))
