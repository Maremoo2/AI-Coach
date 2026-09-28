import copy
import json
import unittest
from importlib.resources import files

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from ai_coach.contracts import hq_envelope, validate_request
from ai_coach.engine import evaluate
from tests.support import request_for, target


class ContractTests(unittest.TestCase):
    def assertRejected(self, data):
        with self.assertRaises((ValueError, ValidationError)):
            validate_request(data)

    def test_all_published_schemas_are_valid(self):
        for path in files("ai_coach.schemas").iterdir():
            if path.name.endswith(".json"):
                Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_invalid_input_matrix(self):
        mutations = [
            lambda d: d.update(schema_version="2.0"),
            lambda d: d.update(target_session_id="missing"),
            lambda d: target(d)["planned"].update(authority="ENGINE"),
            lambda d: target(d)["planned"].update(sport="SWIM"),
            lambda d: target(d)["planned"].update(workout_type="UNKNOWN"),
            lambda d: target(d)["planned"]["dose"].update(duration_min=0),
            lambda d: target(d)["planned"]["dose"].update(intervals=3, work_min=30),
            lambda d: target(d)["actual"].update(rpe=11),
            lambda d: target(d)["actual"].update(quality=float("nan")),
            lambda d: target(d)["actual"].update(duration_min=float("inf")),
            lambda d: target(d)["actual"].update(athlete_id="other"),
            lambda d: target(d)["actual"].update(session_id="other"),
            lambda d: target(d)["actual"].update(started_at="2030-01-01T00:00:00Z"),
            lambda d: target(d)["actual"].update(started_at="2026-06-01T08:00:00"),
            lambda d: target(d)["response"].update(recorded_at=target(d)["actual"]["started_at"]),
            lambda d: target(d)["response"].update(next_session_id="missing"),
            lambda d: target(d)["response"].update(next_session_id=None),
            lambda d: target(d).update(actual=None),
            lambda d: target(d)["planned"].update(source_fact_ids=["missing"]),
            lambda d: target(d)["actual"].update(recommendation="PROGRESS"),
            lambda d: d["source_facts"].append(copy.deepcopy(d["source_facts"][0])),
            lambda d: d["athlete_data"]["sessions"].append(copy.deepcopy(target(d))),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(case=i):
                data = request_for()
                mutate(data)
                self.assertRejected(data)

    def test_corrections_preserve_raw_history_but_require_renormalization(self):
        data = request_for()
        old_id = target(data)["response"]["source_fact_ids"][0]
        data["source_facts"].append({"id": "correction", "source": "synthetic-fixture",
            "recorded_at": data["as_of"], "kind": "CORRECTION", "supersedes": old_id, "payload": {"pain": 2}})
        self.assertRejected(data)
        target(data)["response"]["source_fact_ids"] = ["correction"]
        target(data)["response"]["pain"] = 2
        self.assertEqual(evaluate(data)["state"], "REDUCE")
        self.assertEqual(len(data["source_facts"]), 26)

    def test_hq_contract_rejects_authority_escalation_and_extra_fields(self):
        for change in ({"requires_hq_approval": False}, {"authority": "HQ"}, {"plan_patch": {}}, {"state": "APPLY"}):
            result = evaluate(request_for())
            result.update(change)
            with self.subTest(change=change), self.assertRaises(ValidationError):
                hq_envelope(result)
