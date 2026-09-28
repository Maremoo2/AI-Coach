import copy
import unittest

from ai_coach.engine import evaluate
from tests.support import request_for, target


class EngineTests(unittest.TestCase):
    def test_all_recommendation_states(self):
        cases = [
            (request_for(1), "INSUFFICIENT_EVIDENCE"),
            (request_for(3), "KEEP"),
            (request_for(5), "PROGRESS"),
            (request_for(5, poor=(0,)), "CONSOLIDATE"),
            (request_for(5, poor=(4,)), "REDUCE"),
            (request_for(3, poor=(0, 1, 2), combinations=(0, 1, 2)), "MOVE"),
            (request_for(6, poor=(3, 4, 5), combinations=(3, 4, 5)), "AVOID_COMBINATION"),
        ]
        for data, expected in cases:
            with self.subTest(expected=expected):
                result = evaluate(data)
                self.assertEqual(result["state"], expected)
                self.assertTrue(result["reason_codes"])
                self.assertTrue(result["evidence"]["source_fact_ids"])

    def test_pure_deterministic_and_order_independent(self):
        data = request_for()
        before = copy.deepcopy(data)
        result = evaluate(data)
        self.assertEqual(data, before)
        self.assertEqual(result, evaluate(data))
        data["athlete_data"]["sessions"].reverse()
        data["source_facts"].reverse()
        self.assertEqual(result, evaluate(data))

    def test_missing_response_is_not_success(self):
        data = request_for()
        target(data)["response"] = None
        result = evaluate(data)
        self.assertEqual(result["state"], "CONSOLIDATE")
        self.assertEqual(result["evidence"]["complete_sessions"], 4)

    def test_missing_fields_never_imputed_as_normal(self):
        for section, key in (("actual", "rpe"), ("actual", "quality"), ("response", "pain"),
                             ("response", "recovery_24h"), ("response", "recovery_48h")):
            data = request_for()
            target(data)[section][key] = None
            with self.subTest(key=key):
                self.assertNotEqual(evaluate(data)["state"], "PROGRESS")

    def test_single_pain_event_is_precaution_not_learned_pattern(self):
        data = request_for(1)
        target(data)["response"]["pain"] = 1
        result = evaluate(data)
        self.assertEqual(result["state"], "REDUCE")
        self.assertIn("PRECAUTIONARY_SIGNAL_NOT_LEARNED_RULE", result["reason_codes"])
        self.assertLessEqual(result["confidence"]["score"], 0.35)

    def test_recent_pain_precedes_combination_rule(self):
        data = request_for(6, poor=(3, 4, 5), combinations=(3, 4, 5))
        target(data)["response"]["pain"] = 2
        self.assertEqual(evaluate(data)["state"], "REDUCE")

    def test_noncomparable_dose_not_pooled(self):
        data = request_for()
        target(data)["planned"]["dose"]["duration_min"] = 55
        result = evaluate(data)
        self.assertEqual(result["state"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["evidence"]["complete_sessions"], 1)

    def test_equivalent_json_numbers_match(self):
        data = request_for()
        target(data)["planned"]["dose"]["duration_min"] = 60.0
        self.assertEqual(evaluate(data)["state"], "PROGRESS")

    def test_no_baseline_does_not_become_avoid_combination(self):
        result = evaluate(request_for(5, poor=(0, 1, 2, 3, 4), combinations=(0, 1, 2, 3, 4)))
        self.assertEqual(result["state"], "MOVE")
        self.assertIsNone(result["evidence"]["combination"]["baseline_poor_rate"])

    def test_future_hq_target_can_be_evaluated_without_becoming_observed(self):
        data = request_for()
        future = copy.deepcopy(target(data)["planned"])
        future.update(session_id="future", scheduled_at="2026-07-10T08:00:00Z")
        data["athlete_data"]["sessions"].append({"planned": future, "actual": None, "response": None})
        data["target_session_id"] = "future"
        result = evaluate(data)
        self.assertEqual(result["state"], "PROGRESS")
        self.assertNotIn("future", result["evidence"]["session_ids"])

    def test_overexecution_does_not_count_as_success(self):
        data = request_for()
        target(data)["actual"]["duration_min"] = 90
        self.assertNotEqual(evaluate(data)["state"], "PROGRESS")

    def test_declining_quality_blocks_progress(self):
        data = request_for()
        for r in data["athlete_data"]["sessions"]:
            if r["planned"]["session_id"] in ("session-3", "session-4"):
                r["actual"]["quality"] = 0.8
        result = evaluate(data)
        self.assertEqual(result["state"], "CONSOLIDATE")
        self.assertAlmostEqual(result["evidence"]["quality_trend"], -0.1)

    def test_adverse_response_at_other_dose_blocks_progress(self):
        data = request_for()
        other = next(r for r in data["athlete_data"]["sessions"] if r["planned"]["session_id"] == "next-4")
        other["actual"]["quality"] = 0.4
        result = evaluate(data)
        self.assertEqual(result["state"], "CONSOLIDATE")
        self.assertIn("RECENT_TOLERANCE_CHANGED_AT_OTHER_DOSE", result["reason_codes"])

    def test_stale_and_out_of_window_evidence(self):
        data = request_for()
        data["as_of"] = "2026-08-01T08:00:00Z"
        self.assertEqual(evaluate(data)["reason_codes"], ["STALE_COMPARABLE_EVIDENCE"])
        data["as_of"] = "2027-01-01T08:00:00Z"
        result = evaluate(data)
        self.assertEqual(result["state"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result["evidence"]["complete_sessions"], 0)

    def test_confidence_increases_with_repeated_consistent_evidence(self):
        self.assertLess(evaluate(request_for(3))["confidence"]["score"], evaluate(request_for(5))["confidence"]["score"])

    def test_hq_only_output_has_no_plan_or_scheduled_workout(self):
        result = evaluate(request_for())
        self.assertEqual(result["authority"], "ADVISORY_ONLY")
        self.assertTrue(result["requires_hq_approval"])
        self.assertNotIn("plan", result)
        self.assertNotIn("candidate_next_dose", result)
