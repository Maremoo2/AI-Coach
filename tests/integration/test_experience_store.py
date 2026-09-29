import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_coach.experience import make_event, normalize_life_context
from ai_coach.experience_collector import ExperienceCollector
from ai_coach.experience_store import ExperienceStore
from ai_coach.sequences import build_sequence_observations


NOW = "2026-09-29T20:00:00+02:00"


class ExperienceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "experience.sqlite"
        self.store = ExperienceStore(self.db_path)
        self.collector = ExperienceCollector(self.store, "athlete")

    def tearDown(self):
        self.temp.cleanup()

    def planned(self, session_id="p1", when="2026-09-29T18:00:00+02:00"):
        return {
            "session_id": session_id,
            "plan_version": "hq-v1",
            "scheduled_at": when,
            "workout_type": "RUN_THRESHOLD",
            "sport": "RUN",
            "stimuli": ["THRESHOLD"],
            "dose": {
                "duration_min": 60,
                "intervals": 3,
                "work_min": 10,
                "rest_min": 2,
                "intensity": "HARD",
                "volume": None,
            },
            "key_session": True,
        }

    def test_end_to_end_collection_materialization_and_correction(self):
        experience_id, _ = self.collector.capture_plan(self.planned(), NOW)
        actual_id = self.collector.capture_actual(
            experience_id,
            {
                "activity_id": "a1",
                "planned_session_id": "p1",
                "started_at": "2026-09-29T18:05:00+02:00",
                "workout_type": "RUN_THRESHOLD",
                "sport": "RUN",
                "duration_min": 59,
                "execution": "A",
                "rpe": 7,
                "quality": 0.88,
                "pain": 2,
            },
            NOW,
        )
        self.collector.capture_life_context(
            experience_id,
            "2026-09-29T08:00:00+02:00",
            {
                "workday_load": "HIGH",
                "available_training_window_min": 70,
                "title": "Private meeting name",
            },
            NOW,
        )
        self.collector.capture_recovery(
            experience_id,
            "2026-09-30T18:00:00+02:00",
            {"recovery_24h": "NORMAL", "recovery_48h": None, "pain": 0},
            "2026-09-30T18:01:00+02:00",
        )
        self.collector.correct(
            experience_id,
            actual_id,
            "2026-09-30T19:00:00+02:00",
            {"pain": 0},
            "ENTRY_ERROR",
            "2026-09-30T19:00:00+02:00",
        )

        snapshot = self.store.materialize(experience_id)
        self.assertEqual(snapshot["latest"]["ACTUAL_EXPOSURE"]["pain"], 0)
        self.assertNotIn("title", snapshot["latest"]["LIFE_CONTEXT"])
        self.assertEqual(snapshot["outcome_label"], "GOOD")
        original = next(e for e in snapshot["events"] if e["event_id"] == actual_id)
        self.assertEqual(original["payload"]["pain"], 2)

    def test_idempotent_connector_retry_does_not_duplicate(self):
        experience_id, first = self.collector.capture_plan(self.planned(), NOW)
        _, second = self.collector.capture_plan(self.planned(), NOW)
        self.assertEqual(first, second)
        self.assertEqual(len(self.store.read()), 1)
        self.assertEqual(self.store.experience_ids(), [experience_id])

    def test_update_and_delete_are_rejected(self):
        self.collector.capture_plan(self.planned(), NOW)
        with sqlite3.connect(self.db_path) as db:
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE experience_events SET payload='{}' WHERE sequence=1")
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("DELETE FROM experience_events WHERE sequence=1")

    def test_export_preserves_unknown_and_supports_sequence_learning(self):
        first, _ = self.collector.capture_plan(
            self.planned("p1", "2026-09-28T18:00:00+02:00"), NOW
        )
        self.collector.capture_actual(
            first,
            {
                "activity_id": "a1",
                "planned_session_id": "p1",
                "started_at": "2026-09-28T18:00:00+02:00",
                "workout_type": "RUN_THRESHOLD",
                "sport": "RUN",
                "duration_min": 60,
                "execution": "A",
                "quality": 0.9,
            },
            NOW,
        )
        second, _ = self.collector.capture_plan(
            self.planned("p2", "2026-09-29T18:00:00+02:00"), NOW
        )
        self.collector.capture_actual(
            second,
            {
                "activity_id": "a2",
                "planned_session_id": "p2",
                "started_at": "2026-09-29T18:00:00+02:00",
                "workout_type": "RUN_THRESHOLD",
                "sport": "RUN",
                "duration_min": 60,
                "execution": "A",
                "quality": None,
            },
            NOW,
        )
        rows = self.store.export_learning_rows("athlete")
        target = next(row for row in rows if row["experience_id"] == second)
        self.assertEqual(target["outcome_label"], "UNKNOWN")
        observations = build_sequence_observations(rows)
        self.assertEqual(observations[0]["outcome"], "UNKNOWN")

    def test_cli_append_and_export(self):
        event = make_event(
            athlete_id="athlete",
            experience_id="e1",
            event_type="LIFE_CONTEXT",
            occurred_at=NOW,
            recorded_at=NOW,
            source_kind="CALENDAR_DERIVED",
            source_ref="calendar:derived",
            payload=normalize_life_context({"travel": False, "available_training_window_min": 45}),
            idempotency_key="context:e1",
        )
        event_path = Path(self.temp.name) / "event.json"
        event_path.write_text(json.dumps(event), encoding="utf-8")
        append = subprocess.run(
            [sys.executable, "-m", "ai_coach.experience_cli", "--db", str(self.db_path), "append", str(event_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(append.returncode, 0, append.stderr)
        export = subprocess.run(
            [sys.executable, "-m", "ai_coach.experience_cli", "--db", str(self.db_path), "export"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(export.returncode, 0, export.stderr)
        rows = json.loads(export.stdout)
        self.assertEqual(rows[0]["life_context"]["available_training_window_min"], 45)
