import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.unit.test_coach_v1 import context


class CoachCliTests(unittest.TestCase):
    def test_daily_brief_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "context.json"
            path.write_text(json.dumps(context()), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, "-m", "ai_coach.coach_cli", str(path)],
                capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result["selected_variant"], "A")
            self.assertEqual(result["workout"]["venue"], "MYWHOOSH")
