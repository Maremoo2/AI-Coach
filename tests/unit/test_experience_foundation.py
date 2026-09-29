import unittest

from ai_coach.experience import (
    make_event,
    normalize_life_context,
    outcome_label,
    stable_experience_id,
)
from ai_coach.reconciliation import reconcile_one
from ai_coach.sampling import adaptive_capture_questions
from ai_coach.sequences import build_sequence_observations


class ExperienceContractTests(unittest.TestCase):
    def test_stable_id_uses_plan_anchor(self):
        a = stable_experience_id("athlete", planned_session_id="session-1")
        b = stable_experience_id("athlete", planned_session_id="session-1")
        self.assertEqual(a, b)

    def test_life_context_discards_calendar_content(self):
        result = normalize_life_context({
            "workday_load": "HIGH",
            "busy_minutes": 420,
            "available_training_window_min": 55,
            "travel": False,
            "title": "Secret customer meeting",
            "attendees": ["person@example.com"],
            "notes": "confidential",
        })
        self.assertEqual(result["workday_load"], "HIGH")
        self.assertEqual(result["available_training_window_min"], 55)
        self.assertNotIn("title", result)
        self.assertNotIn("attendees", result)
        self.assertNotIn("notes", result)

    def test_missing_is_not_good_outcome(self):
        snapshot = {"latest": {"ACTUAL_EXPOSURE": {"quality": None}}}
        self.assertEqual(outcome_label(snapshot), "UNKNOWN")

    def test_correction_requires_target(self):
        with self.assertRaises(ValueError):
            make_event(
                athlete_id="a",
                experience_id="e",
                event_type="CORRECTION",
                occurred_at="2026-09-29T10:00:00+02:00",
                recorded_at="2026-09-29T10:01:00+02:00",
                source_kind="ATHLETE",
                source_ref="athlete:correction",
                payload={"set": {"pain": 0}, "reason_code": "ENTRY_ERROR"},
            )


class ReconciliationTests(unittest.TestCase):
    def test_exact_link_beats_time_matching(self):
        planned = {
            "session_id": "p1",
            "sport": "RUN",
            "scheduled_at": "2026-09-29T18:00:00+02:00",
        }
        activities = [
            {
                "activity_id": "a1",
                "planned_session_id": "p1",
                "sport": "RUN",
                "started_at": "2026-09-29T20:00:00+02:00",
            },
            {
                "activity_id": "a2",
                "sport": "RUN",
                "started_at": "2026-09-29T18:10:00+02:00",
            },
        ]
        self.assertEqual(reconcile_one(planned, activities)["actual"]["activity_id"], "a1")

    def test_ambiguous_time_match_is_not_guessed(self):
        planned = {
            "session_id": "p1",
            "sport": "BIKE",
            "scheduled_at": "2026-09-29T18:00:00+02:00",
        }
        activities = [
            {"activity_id": "a1", "sport": "BIKE", "started_at": "2026-09-29T17:30:00+02:00"},
            {"activity_id": "a2", "sport": "BIKE", "started_at": "2026-09-29T18:30:00+02:00"},
        ]
        result = reconcile_one(planned, activities)
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIsNone(result["actual"])


class SamplingTests(unittest.TestCase):
    def test_routine_easy_session_stays_quiet_after_baseline(self):
        snapshot = {
            "latest": {
                "PLANNED_EXPOSURE": {
                    "key_session": False,
                    "benchmark": False,
                    "novel_dose": False,
                    "dose": {"intensity": "EASY"},
                },
                "ACTUAL_EXPOSURE": {"execution": "A", "quality": None, "rpe": None, "pain": None},
            }
        }
        result = adaptive_capture_questions(snapshot, "POST_WORKOUT", history_count=10)
        self.assertEqual(result["questions"], [])

    def test_key_session_requests_only_missing_core_fields(self):
        snapshot = {
            "latest": {
                "PLANNED_EXPOSURE": {
                    "key_session": True,
                    "benchmark": False,
                    "novel_dose": False,
                    "dose": {"intensity": "HARD"},
                },
                "ACTUAL_EXPOSURE": {"execution": "A", "rpe": 7, "quality": None, "pain": None},
            }
        }
        fields = [
            item["field"]
            for item in adaptive_capture_questions(snapshot, "POST_WORKOUT", history_count=10)["questions"]
        ]
        self.assertEqual(fields, ["quality", "pain"])


class SequenceTests(unittest.TestCase):
    def test_successful_sequence_is_retained_as_negative_evidence(self):
        rows = [
            {
                "experience_id": "e1",
                "workout_type": "CROSSFIT",
                "started_at": "2026-09-28T18:00:00+02:00",
                "outcome_label": "GOOD",
                "actual": {},
                "subjective_response": {},
                "recovery_response": {},
                "downstream_outcome": {},
            },
            {
                "experience_id": "e2",
                "workout_type": "BIKE_THRESHOLD",
                "started_at": "2026-09-29T18:00:00+02:00",
                "outcome_label": "GOOD",
                "actual": {},
                "subjective_response": {},
                "recovery_response": {},
                "downstream_outcome": {},
            },
        ]
        observations = build_sequence_observations(rows)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["outcome"], "GOOD")
        self.assertTrue(observations[0]["is_negative_evidence"])
