"""Append-only, hash-linked SQLite evaluation history (local single host)."""
import json
import sqlite3
from contextlib import closing

from .contracts import canonical, digest
from .engine import evaluate


class AuditLog:
    def __init__(self, path):
        self.path = str(path)
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'Audit events are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'Audit events are immutable'); END;
            """)

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _read(db):
        previous = "GENESIS"
        events = []
        for sequence, previous_hash, event_hash, payload in db.execute("SELECT * FROM events ORDER BY sequence"):
            value = json.loads(payload)
            if sequence != len(events) + 1 or previous_hash != previous or digest({"previous_hash": previous, "payload": value}) != event_hash:
                raise ValueError("Audit integrity failure")
            events.append({"sequence": sequence, "event_hash": event_hash, **value})
            previous = event_hash
        return events

    def read(self):
        with closing(self._connect()) as db:
            return self._read(db)

    def append(self, request, recommendation):
        # Never record a forged or stale result as an engine evaluation.
        if evaluate(request) != recommendation:
            raise ValueError("Recommendation does not match request replay")
        payload = {"request": request, "recommendation": recommendation}
        encoded = canonical(payload)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            events = self._read(db)
            previous = events[-1]["event_hash"] if events else "GENESIS"
            event_hash = digest({"previous_hash": previous, "payload": payload})
            db.execute("INSERT INTO events VALUES (?, ?, ?, ?)", (len(events) + 1, previous, event_hash, encoded))
        return event_hash

    def replay(self):
        for event in self.read():
            if evaluate(event["request"]) != event["recommendation"]:
                raise ValueError("Replay differs: retain the original engine/policy version")
        return True
