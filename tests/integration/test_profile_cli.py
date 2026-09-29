import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_coach.experience_collector import ExperienceCollector
from ai_coach.experience_store import ExperienceStore


class ProfileCliTests(unittest.TestCase):
    def test_profile_cli_materializes_store(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "experience.sqlite"
            store = ExperienceStore(db)
            collector = ExperienceCollector(store, "athlete")
            experience_id, _ = collector.capture_plan(
                {
                    "session_id": "p1",
                    "plan_version": "hq-v1",
                    "scheduled_at": "2026-10-10T10:00:00Z",
                    "workout_type": "RUN_THRESHOLD",
                    "sport": "RUN",
                    "stimuli": ["THRESHOLD"],
                    "dose": {"duration_min": 60, "intervals": 3, "work_min": 10, "rest_min": 2, "intensity": "HARD", "volume": None},
                    "key_session": True,
                },
                "2026-10-09T10:00:00Z",
            )
            collector.capture_actual(
                experience_id,
                {
                    "activity_id": "a1",
                    "planned_session_id": "p1",
                    "started_at": "2026-10-10T10:00:00Z",
                    "workout_type": "RUN_THRESHOLD",
                    "sport": "RUN",
                    "duration_min": 60,
                    "execution": "A",
                    "quality": 0.90,
                },
                "2026-10-10T12:00:00Z",
            )
            collector.capture_recovery(
                experience_id,
                "2026-10-11T10:00:00Z",
                {"recovery_24h": "NORMAL", "recovery_48h": None, "pain": 0},
                "2026-10-11T10:05:00Z",
            )
            run = subprocess.run(
                [sys.executable, "-m", "ai_coach.profile_cli", "--db", str(db), "--as-of", "2026-10-12T10:00:00Z"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result["dose_profiles"][0]["absorption"]["good"], 1)
            self.assertFalse(result["can_write_plan"])
