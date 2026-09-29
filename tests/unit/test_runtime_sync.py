import unittest

from ai_coach.runtime_sync import (
    EVENT_COLUMNS,
    activity_event_key,
    information_rich_plan,
    pending_question_fields,
    plan_event_key,
    reconcile_runtime_plan,
    runtime_experience_key,
)


class RuntimeSyncTests(unittest.TestCase):
    def test_keys_are_stable_and_revision_sensitive(self):
        plan = {"id": "p1", "updatedAt": "2026-09-29T07:00:00Z"}
        self.assertEqual(plan_event_key(plan), "PLANNED:p1:2026-09-29T07:00:00Z")
        self.assertEqual(activity_event_key({"id": "a1"}), "ACTUAL:a1")
        self.assertEqual(runtime_experience_key(plan_id="p1"), "plan:p1")
        self.assertEqual(runtime_experience_key(activity_id="a1"), "activity:a1")
        self.assertIn("event_key", EVENT_COLUMNS)

    def test_exact_plan_link_wins(self):
        plan = {
            "id": "p1",
            "sportType": "cycling",
            "date": "2026-09-29T18:00:00+02:00",
        }
        activities = [
            {
                "id": "a1",
                "planned_session_id": "p1",
                "sportType": "cycling",
                "date": "2026-09-29T21:00:00+02:00",
            },
            {
                "id": "a2",
                "sportType": "cycling",
                "date": "2026-09-29T18:05:00+02:00",
            },
        ]
        result = reconcile_runtime_plan(plan, activities)
        self.assertEqual(result["status"], "EXACT")
        self.assertEqual(result["actual_id"], "a1")

    def test_ambiguous_runtime_match_is_not_guessed(self):
        plan = {
            "id": "p1",
            "sportType": "running",
            "date": "2026-09-29T18:00:00+02:00",
        }
        activities = [
            {"id": "a1", "sportType": "running", "date": "2026-09-29T17:30:00+02:00"},
            {"id": "a2", "sportType": "running", "date": "2026-09-29T18:30:00+02:00"},
        ]
        result = reconcile_runtime_plan(plan, activities)
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIsNone(result["actual_id"])

    def test_quality_plan_gets_minimal_subjective_questions(self):
        plan = {"title": "CSS benchmark – 400/200 m", "notes": ""}
        self.assertTrue(information_rich_plan(plan))
        fields = pending_question_fields(plan, {"rpe": None, "quality": None, "pain": None})
        self.assertEqual(fields, ["rpe", "quality", "pain"])

    def test_easy_plan_does_not_create_noise(self):
        plan = {"title": "Rolig svøm", "notes": "lett teknikk"}
        self.assertFalse(information_rich_plan(plan))
        self.assertEqual(pending_question_fields(plan, {}), [])
