import unittest

from ai_coach.coach import build_daily_brief, post_workout_feedback
from ai_coach.personalization import infer_personal_rules
from ai_coach.progression import adaptation_proposal
from ai_coach.spot_checks import due_spot_check
from ai_coach.tool_policy import choose_venue, runtime_reads
from ai_coach.workout_library import prescribe, template


def context(gate="GREEN", variant_b="RUN_EASY_45", missed=0, season="WINTER"):
    return {
        "schema_version": "1.0",
        "athlete_id": "synthetic-athlete",
        "as_of": "2026-09-29T06:00:00Z",
        "language": "no",
        "hq_plan": {
            "plan_version": "hq-v1",
            "today": {
                "session_id": "today",
                "variants": {"A": "BIKE_SWEETSPOT_2X15", "B": variant_b, "C": "RECOVERY_30"},
            },
        },
        "execution_gate": {"status": gate, "reasons": []},
        "environment": {
            "season": season,
            "available_tools": ["TREDICT", "GOOGLE_CALENDAR", "MYWHOOSH", "EVO_GYM"],
            "preferred_venues": {},
        },
        "capacities": {"cycling_ftp_w": 250},
        "adherence": {
            "planned_14d": 8, "completed_a": 6 - min(missed, 2),
            "completed_b": 0, "completed_c": 0, "missed": missed,
        },
        "goal_sports": ["RUN", "BIKE", "SWIM", "STRENGTH"],
        "benchmarks": [],
        "days_since_quality": 8,
        "performance_context": {"sleep": "GREEN", "stress": "GREEN", "fueling": "GREEN", "travel": False},
        "feedback": None,
    }


class WorkoutLibraryTests(unittest.TestCase):
    def test_mywhoosh_bike_targets_use_ftp(self):
        workout = prescribe("BIKE_SWEETSPOT_2X15", {"cycling_ftp_w": 250}, "MYWHOOSH")
        work = next(step for step in workout["steps"] if step["name"] == "work")
        self.assertEqual(work["target_watts"], [220, 230])
        self.assertEqual(workout["venue"], "MYWHOOSH")

    def test_strength_prefers_evo(self):
        workout = template("STRENGTH_EVO_FULLBODY_A")
        venue = choose_venue(workout, {"season": "WINTER", "available_tools": ["EVO_GYM"]})
        self.assertEqual(venue, "EVO_GYM")


class CoachTests(unittest.TestCase):
    def test_green_gate_executes_hq_plan_a(self):
        brief = build_daily_brief(context())
        self.assertEqual(brief["selected_variant"], "A")
        self.assertEqual(brief["workout"]["template_id"], "BIKE_SWEETSPOT_2X15")
        self.assertEqual(brief["workout"]["venue"], "MYWHOOSH")
        self.assertEqual(brief["authority"], "COACH_ADVISORY_HQ_PLAN_ONLY")
        self.assertTrue(brief["requires_hq_approval_for_plan_changes"])

    def test_amber_uses_only_preapproved_b(self):
        brief = build_daily_brief(context("AMBER"))
        self.assertEqual(brief["selected_variant"], "B")
        self.assertEqual(brief["workout"]["template_id"], "RUN_EASY_45")

    def test_red_uses_only_preapproved_c(self):
        brief = build_daily_brief(context("RED"))
        self.assertEqual(brief["selected_variant"], "C")
        self.assertEqual(brief["workout"]["template_id"], "RECOVERY_30")

    def test_missing_safe_variant_requests_hq_review(self):
        data = context("AMBER", variant_b=None)
        data["hq_plan"]["today"]["variants"]["C"] = None
        brief = build_daily_brief(data)
        self.assertEqual(brief["selected_variant"], "REVIEW")
        self.assertIsNone(brief["workout"])
        self.assertIn("HQ_REVIEW_TODAY_VARIANT", brief["hq_actions"])

    def test_accountability_does_not_stack_makeup(self):
        brief = build_daily_brief(context(missed=2))
        self.assertEqual(brief["accountability"]["action"], "RETURN_TO_RHYTHM")
        self.assertTrue(brief["accountability"]["no_makeup_stacking"])
        self.assertIn("rytme", brief["motivation"].lower())

    def test_quality_day_defers_due_spot_check(self):
        brief = build_daily_brief(context())
        self.assertEqual(brief["spot_check"]["status"], "DEFER_UNTIL_HQ_PLACES_AS_KEY_SESSION")

    def test_no_plan_write_surface(self):
        brief = build_daily_brief(context())
        self.assertNotIn("plan_patch", brief)
        self.assertNotIn("write_plan", brief)
        self.assertIn("NO_DIRECT_PLAN_WRITE", brief["constraints"])


class AdaptationTests(unittest.TestCase):
    def feedback(self, state):
        return {"state": state}

    def test_progress_only_moves_one_library_step(self):
        proposal = adaptation_proposal(self.feedback("PROGRESS"), "RUN_THRESHOLD_3X10")
        self.assertEqual(proposal["candidate_template_id"], "RUN_THRESHOLD_3X12")
        self.assertTrue(proposal["requires_hq_approval"])

    def test_reduce_moves_one_library_step(self):
        proposal = adaptation_proposal(self.feedback("REDUCE"), "RUN_THRESHOLD_3X10")
        self.assertEqual(proposal["candidate_template_id"], "RUN_THRESHOLD_3X8")

    def test_post_workout_feedback_is_actionable(self):
        evaluation = {
            "state": "KEEP", "evidence": {"complete_sessions": 3},
            "confidence": {"score": 0.4, "label": "LOW", "meaning": "EVIDENCE_STRENGTH_NOT_PROBABILITY"},
            "reason_codes": ["DOSE_TOLERATED"],
        }
        result = post_workout_feedback(evaluation)
        self.assertIn("Behold", result["message"])
        self.assertTrue(result["requires_hq_approval"])


class SpotCheckTests(unittest.TestCase):
    def test_due_check_selects_one_goal_aligned_test(self):
        check = due_spot_check(
            "2026-09-29T06:00:00Z",
            [{"kind": "RUN_5K", "last_tested_at": "2026-09-20T06:00:00Z"}],
            ["RUN", "BIKE"], "GREEN", 8,
        )
        self.assertEqual(check["kind"], "BIKE_FTP")

    def test_check_suppressed_when_not_green_or_recent_quality(self):
        self.assertIsNone(due_spot_check("2026-09-29T06:00:00Z", [], ["RUN"], "AMBER", 20))
        self.assertIsNone(due_spot_check("2026-09-29T06:00:00Z", [], ["RUN"], "GREEN", 3))


class PersonalizationTests(unittest.TestCase):
    def test_single_session_never_becomes_rule(self):
        rules = infer_personal_rules([
            {"id": "1", "pattern_key": "crossfit->bike_threshold_24h", "outcome": "BAD", "confidence": 0.9}
        ])
        self.assertEqual(rules[0]["status"], "OBSERVATION")

    def test_repeated_consistent_signal_can_become_rule(self):
        rows = [
            {"id": str(i), "pattern_key": "crossfit->bike_threshold_24h", "outcome": "BAD", "confidence": 0.7}
            for i in range(5)
        ]
        rules = infer_personal_rules(rows)
        self.assertEqual(rules[0]["status"], "ESTABLISHED_RULE")
        self.assertFalse(rules[0]["can_write_plan"])

    def test_explicit_correction_overrides_inference(self):
        rows = [{"id": str(i), "pattern_key": "x", "outcome": "BAD", "confidence": 0.7} for i in range(5)]
        rules = infer_personal_rules(rows, {"x": "NOT_A_PROBLEM"})
        self.assertEqual(rules[0]["status"], "USER_CORRECTED_RULE")
        self.assertEqual(rules[0]["outcome"], "NOT_A_PROBLEM")


class ToolPolicyTests(unittest.TestCase):
    def test_runtime_reads_use_connected_data_but_no_automatic_writes(self):
        reads = runtime_reads("WEEKLY")
        self.assertTrue(any(x["tool"] == "TREDICT" for x in reads))
        self.assertTrue(any(x["tool"] == "GOOGLE_CALENDAR" for x in reads))
        self.assertFalse(any(x["tool"] == "MYWHOOSH" for x in reads))
