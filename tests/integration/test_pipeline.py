import json
from contextlib import closing
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_coach.audit import AuditLog
from ai_coach.engine import evaluate
from tests.support import request_for, target

ROOT = Path(__file__).resolve().parents[2]


class PipelineTests(unittest.TestCase):
    def test_fixtures_match_all_expected_states(self):
        paths = list((ROOT / "tests" / "fixtures").glob("*.json"))
        self.assertEqual(len(paths), 7)
        for path in paths:
            with self.subTest(fixture=path.name):
                fixture = json.loads(path.read_text())
                self.assertEqual(evaluate(fixture["request"])["state"], fixture["expected_state"])

    def test_cli_emits_advice_preserves_input_and_appends_replayable_history(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            audit = Path(directory) / "audit.sqlite"
            source.write_text(json.dumps(request_for()), encoding="utf-8")
            original = source.read_bytes()
            run = subprocess.run([sys.executable, "-m", "ai_coach.cli", str(source), "--audit", str(audit)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["state"], "PROGRESS")
            self.assertEqual(original, source.read_bytes())
            log = AuditLog(audit)
            self.assertEqual(len(log.read()), 1)
            self.assertTrue(log.replay())

    def test_history_appends_and_sql_update_delete_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.sqlite"
            log = AuditLog(path)
            data = request_for()
            log.append(data, evaluate(data))
            target(data)["response"]["pain"] = 2
            log.append(data, evaluate(data))
            self.assertEqual([e["recommendation"]["state"] for e in log.read()], ["PROGRESS", "REDUCE"])
            self.assertTrue(log.replay())
            with closing(sqlite3.connect(path)) as db, db:
                for statement in ("UPDATE events SET payload='{}'", "DELETE FROM events"):
                    with self.assertRaises(sqlite3.IntegrityError):
                        db.execute(statement)

    def test_forged_advice_is_not_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            log = AuditLog(Path(directory) / "audit.sqlite")
            data = request_for()
            result = evaluate(data)
            result["state"] = "KEEP"
            with self.assertRaises(ValueError):
                log.append(data, result)
            self.assertEqual(log.read(), [])

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.sqlite"
            log = AuditLog(path)
            data = request_for()
            log.append(data, evaluate(data))
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("DROP TRIGGER no_update")
                db.execute("UPDATE events SET payload='{}'")
            with self.assertRaisesRegex(ValueError, "integrity"):
                log.read()

    def test_invalid_cli_input_fails_without_creating_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            source, audit = Path(directory) / "input.json", Path(directory) / "audit.sqlite"
            source.write_text('{"invalid": true}')
            run = subprocess.run([sys.executable, "-m", "ai_coach.cli", str(source), "--audit", str(audit)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(audit.exists())
            self.assertEqual(run.stdout, "")
