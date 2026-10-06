"""Event-sourced local application state. No cloud synchronization or plan API."""
import json
import sqlite3
from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .contracts import canonical, digest, require


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ConflictError(ValueError):
    pass


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS journal (
                  sequence INTEGER PRIMARY KEY, kind TEXT NOT NULL, entity_id TEXT NOT NULL,
                  recorded_at TEXT NOT NULL, payload TEXT NOT NULL,
                  previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE);
                CREATE TRIGGER IF NOT EXISTS journal_no_update BEFORE UPDATE ON journal
                BEGIN SELECT RAISE(ABORT, 'Immutable journal'); END;
                CREATE TRIGGER IF NOT EXISTS journal_no_delete BEFORE DELETE ON journal
                BEGIN SELECT RAISE(ABORT, 'Immutable journal'); END;
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    @contextmanager
    def transaction(self, expected_revision=None):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            events = self.read(db)
            if expected_revision is not None and expected_revision != len(events):
                raise ConflictError("Data changed. Refresh before approving or saving.")
            yield db, self.project(events)

    def read(self, db=None):
        if db is None:
            with closing(self.connect()) as connection:
                return self.read(connection)
        events, previous = [], "GENESIS"
        for seq, kind, entity_id, recorded_at, payload, previous_hash, event_hash in db.execute("SELECT * FROM journal ORDER BY sequence"):
            body = {"kind": kind, "entity_id": entity_id, "recorded_at": recorded_at, "payload": json.loads(payload)}
            require(seq == len(events) + 1 and previous_hash == previous and digest({"previous": previous, **body}) == event_hash, "Journal integrity failure")
            events.append({"sequence": seq, **body, "event_hash": event_hash})
            previous = event_hash
        return events

    def append(self, db, kind, entity_id, payload, recorded_at=None):
        events = self.read(db)
        previous = events[-1]["event_hash"] if events else "GENESIS"
        body = {"kind": kind, "entity_id": entity_id, "recorded_at": recorded_at or utc_now(), "payload": payload}
        event_hash = digest({"previous": previous, **body})
        db.execute("INSERT INTO journal VALUES (?,?,?,?,?,?,?)", (len(events) + 1, kind, entity_id, body["recorded_at"], canonical(payload), previous, event_hash))
        return event_hash

    @staticmethod
    def project(events):
        state = {"revision": len(events), "profile": None, "goals": {}, "checkins": {},
                 "plan": None, "plans": {}, "proposals": {}, "evaluations": {}, "imports": {},
                 "source_snapshot": None, "source_snapshots": {}, "garmin_sync": None, "garmin_status": None, "garmin_activities": {},
                 "last_event_hash": events[-1]["event_hash"] if events else "GENESIS"}
        for event in events:
            kind, key, value = event["kind"], event["entity_id"], deepcopy(event["payload"])
            if kind == "GARMIN_SYNC":
                state["garmin_sync"] = value
                state["garmin_activities"].update({a["id"]: a for a in value["activities"]})
            elif kind == "GARMIN_STATUS":
                state["garmin_status"] = value
            elif kind == "PROFILE":
                state["profile"] = value
            elif kind == "SOURCE_SNAPSHOT":
                state["source_snapshot"] = value
                state["source_snapshots"][key] = value
            elif kind == "HQ_PLAN":
                state["plan"] = value
                state["plans"][value["version"]] = value
            elif kind in ("GOAL", "CHECKIN", "PROPOSAL", "EVALUATION", "IMPORT"):
                name = {"GOAL": "goals", "CHECKIN": "checkins", "PROPOSAL": "proposals",
                        "EVALUATION": "evaluations", "IMPORT": "imports"}[kind]
                state[name][key] = value
            elif kind == "HQ_DECISION":
                state["proposals"][key]["status"] = value["decision"]
        return state

    def state(self):
        return self.project(self.read())

    def backup(self, directory):
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        # Exclusive reservation prevents overwriting an earlier backup.
        from uuid import uuid4
        target = folder / f"coach-{uuid4().hex}.sqlite"
        with target.open("xb"):
            pass
        with closing(self.connect()) as source, closing(sqlite3.connect(target)) as dest:
            source.backup(dest)
        # Check the copied chain and persist an external checkpoint alongside it.
        copied = Journal(target).read()
        manifest = {"file": target.name, "events": len(copied),
                    "last_event_hash": copied[-1]["event_hash"] if copied else "GENESIS"}
        import hashlib
        manifest["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        target.with_suffix(".json").write_text(canonical(manifest), encoding="utf-8")
        return manifest
