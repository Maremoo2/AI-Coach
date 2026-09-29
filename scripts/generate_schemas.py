"""Regenerate public Draft 2020-12 schemas from the versioned contract."""
import json
from pathlib import Path
from ai_coach.taxonomy import STATES, STIMULI, WORKOUTS

ROOT = Path(__file__).resolve().parents[1] / "schemas"


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


def array(item, **kwargs):
    return {"type": "array", "items": item, **kwargs}


def enum(*values):
    return {"enum": list(values)}


def number(lo=0, hi=None):
    result = {"type": "number", "minimum": lo}
    if hi is not None:
        result["maximum"] = hi
    return result


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


text = {"type": "string", "minLength": 1}
timestamp = {"type": "string", "format": "date-time"}
refs = array(text, minItems=1, uniqueItems=True)
identity = {"session_id": text, "athlete_id": text, "source_fact_ids": refs}
dose = obj({"duration_min": {"type": "number", "exclusiveMinimum": 0},
            "intervals": {"type": "integer", "minimum": 0},
            "work_min": number(), "rest_min": number(),
            "intensity": enum("EASY", "MODERATE", "HARD"),
            "volume": nullable(obj({"value": number(), "unit": enum("M", "KM", "REPS", "KG_REPS")}))})
planned = obj({**identity, "plan_version": text, "authority": {"const": "HQ"},
               "scheduled_at": timestamp, "workout_type": enum(*WORKOUTS),
               "sport": enum("RUN", "BIKE", "SWIM", "STRENGTH", "MIXED"),
               "stimuli": array(enum(*STIMULI), minItems=1, uniqueItems=True), "dose": dose})
actual = obj({**identity, "started_at": timestamp, "duration_min": number(),
              "execution": enum("A", "B", "C"), "rpe": nullable(number(0, 10)),
              "quality": nullable(number(0, 1)),
              "volume": nullable(obj({"value": number(), "unit": enum("M", "KM", "REPS", "KG_REPS")}))})
response = obj({**identity, "recorded_at": timestamp, "pain": nullable(number(0, 10)),
                "recovery_24h": enum("NORMAL", "POOR", None),
                "recovery_48h": enum("NORMAL", "POOR", None),
                "sleep_quality": nullable(number(0, 1)),
                "next_session_quality": enum("GOOD", "POOR", None),
                "next_session_id": nullable(text)})
fact = obj({"id": text, "source": text, "recorded_at": timestamp,
            "kind": enum("HQ_PLAN", "DEVICE", "ATHLETE_REPORT", "CORRECTION"),
            "supersedes": nullable(text), "payload": {"type": "object"}})
record = obj({"planned": planned, "actual": nullable(actual), "response": nullable(response)})
request = obj({"schema_version": {"const": "1.0"}, "as_of": timestamp,
               "target_session_id": text,
               "source_facts": array(fact, minItems=1),
               "athlete_data": obj({"athlete_id": text, "sessions": array(record, minItems=1)})})
feature = obj({"session_id": text, "completion_ratio": nullable(number()),
               "complete_response": {"type": "boolean"},
               "success": {"type": "boolean"}, "adverse": {"type": "boolean"},
               "previous_session_id": nullable(text), "combination": nullable(text)})
evidence = obj({"session_ids": array(text, uniqueItems=True),
                "excluded_session_ids": array(text, uniqueItems=True),
                "source_fact_ids": array(text, uniqueItems=True),
                "complete_sessions": {"type": "integer", "minimum": 0},
                "successful_sessions": {"type": "integer", "minimum": 0},
                "adverse_sessions": {"type": "integer", "minimum": 0},
                "quality_trend": nullable({"type": "number"}),
                "combination": nullable(obj({"key": text, "exposed_session_ids": array(text),
                    "baseline_session_ids": array(text), "poor_rate": number(0, 1),
                    "baseline_poor_rate": nullable(number(0, 1))}))})
recommendation = obj({"schema_version": {"const": "1.0"}, "engine_version": text,
    "policy_version": text, "taxonomy_version": text, "input_hash": text,
    "athlete_id": text, "target_session_id": text, "target_plan_version": text,
    "as_of": timestamp, "state": enum(*STATES),
    "authority": {"const": "ADVISORY_ONLY"}, "requires_hq_approval": {"const": True},
    "confidence": obj({"score": number(0, 1), "label": enum("LOW", "MODERATE", "HIGH"),
                       "meaning": {"const": "EVIDENCE_STRENGTH_NOT_PROBABILITY"}}),
    "reason_codes": array(text, minItems=1), "constraints": array(text, minItems=1),
    "evidence": evidence, "derived_features": array(feature)})

for name, schema in {"planned_workout": planned, "actual_workout": actual,
                     "response": response, "source_fact": fact,
                     "evaluation_request": request, "recommendation": recommendation}.items():
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": name, **schema}
    (ROOT / f"{name}.schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

from ai_coach.app_contracts import CONTRACTS
for name, schema in CONTRACTS.items():
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": f"app_{name}", **schema}
    (ROOT / f"app_{name}.schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
