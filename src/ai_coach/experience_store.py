"""Append-only athlete experience store with corrections and deterministic export."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from copy import deepcopy

from .contracts import canonical, digest
from .experience import outcome_label, validate_event


class ExperienceStore:
    """Local SQLite event store.

    Events are immutable and hash-linked. Corrections append a new event rather
    than mutating the original observation.
    """

    def __init__(self, path):
        self.path = str(path)
        with closing(self._connect()) as db, db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS experience_events (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    experience_id TEXT NOT NULL,
                    athlete_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    supersedes_event_id TEXT,
                    idempotency_key TEXT UNIQUE,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_experience_id
                    ON experience_events(experience_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_athlete
                    ON experience_events(athlete_id, sequence);
                CREATE TRIGGER IF NOT EXISTS experience_no_update
                    BEFORE UPDATE ON experience_events
                    BEGIN SELECT RAISE(ABORT, 'Experience events are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS experience_no_delete
                    BEFORE DELETE ON experience_events
                    BEGIN SELECT RAISE(ABORT, 'Experience events are immutable'); END;
                """
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _row_event(row):
        (
            sequence,
            event_id,
            experience_id,
            athlete_id,
            event_type,
            occurred_at,
            recorded_at,
            source_kind,
            source_ref,
            supersedes_event_id,
            idempotency_key,
            previous_hash,
            event_hash,
            payload,
        ) = row
        return {
            "sequence": sequence,
            "event_id": event_id,
            "experience_id": experience_id,
            "athlete_id": athlete_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "recorded_at": recorded_at,
            "source": {"kind": source_kind, "ref": source_ref},
            "supersedes_event_id": supersedes_event_id,
            "idempotency_key": idempotency_key,
            "previous_hash": previous_hash,
            "event_hash": event_hash,
            "payload": json.loads(payload),
        }

    @classmethod
    def _read_verified(cls, db, where="", params=()):
        query = (
            "SELECT sequence,event_id,experience_id,athlete_id,event_type,"
            "occurred_at,recorded_at,source_kind,source_ref,supersedes_event_id,"
            "idempotency_key,previous_hash,event_hash,payload "
            "FROM experience_events "
        )
        rows = db.execute(query + where + " ORDER BY sequence", params).fetchall()

        # Integrity must be checked over the entire chain, not a filtered subset.
        if where:
            all_rows = db.execute(query + "ORDER BY sequence").fetchall()
            cls._verify_chain(all_rows)
        else:
            cls._verify_chain(rows)
        return [cls._row_event(row) for row in rows]

    @staticmethod
    def _verify_chain(rows):
        previous = "GENESIS"
        expected_sequence = 1
        for row in rows:
            sequence = row[0]
            previous_hash = row[11]
            event_hash = row[12]
            payload = json.loads(row[13])
            event_for_hash = {
                "event_id": row[1],
                "experience_id": row[2],
                "athlete_id": row[3],
                "event_type": row[4],
                "occurred_at": row[5],
                "recorded_at": row[6],
                "source": {"kind": row[7], "ref": row[8]},
                "supersedes_event_id": row[9],
                "idempotency_key": row[10],
                "payload": payload,
            }
            expected = digest({"previous_hash": previous, "event": event_for_hash})
            if sequence != expected_sequence or previous_hash != previous or event_hash != expected:
                raise ValueError("Experience store integrity failure")
            previous = event_hash
            expected_sequence += 1

    def append(self, event):
        validate_event(event)
        encoded = canonical(event["payload"])
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing = None
            if event["idempotency_key"]:
                existing = db.execute(
                    "SELECT event_id,payload,event_type,experience_id FROM experience_events "
                    "WHERE idempotency_key=?",
                    (event["idempotency_key"],),
                ).fetchone()
            if existing:
                if (
                    existing[0] == event["event_id"]
                    and json.loads(existing[1]) == event["payload"]
                    and existing[2] == event["event_type"]
                    and existing[3] == event["experience_id"]
                ):
                    return existing[0]
                raise ValueError("idempotency key already used for different event")

            rows = db.execute(
                "SELECT sequence,event_id,experience_id,athlete_id,event_type,"
                "occurred_at,recorded_at,source_kind,source_ref,supersedes_event_id,"
                "idempotency_key,previous_hash,event_hash,payload "
                "FROM experience_events ORDER BY sequence"
            ).fetchall()
            self._verify_chain(rows)

            if event["event_type"] == "CORRECTION":
                target = db.execute(
                    "SELECT athlete_id,experience_id,event_type FROM experience_events WHERE event_id=?",
                    (event["supersedes_event_id"],),
                ).fetchone()
                if not target:
                    raise ValueError("correction target does not exist")
                if target[0] != event["athlete_id"] or target[1] != event["experience_id"]:
                    raise ValueError("correction target must belong to same athlete and experience")
                if target[2] == "CORRECTION":
                    raise ValueError("corrections must target original observations")

            previous = rows[-1][12] if rows else "GENESIS"
            sequence = len(rows) + 1
            event_for_hash = {
                "event_id": event["event_id"],
                "experience_id": event["experience_id"],
                "athlete_id": event["athlete_id"],
                "event_type": event["event_type"],
                "occurred_at": event["occurred_at"],
                "recorded_at": event["recorded_at"],
                "source": deepcopy(event["source"]),
                "supersedes_event_id": event["supersedes_event_id"],
                "idempotency_key": event["idempotency_key"],
                "payload": deepcopy(event["payload"]),
            }
            event_hash = digest({"previous_hash": previous, "event": event_for_hash})
            db.execute(
                "INSERT INTO experience_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    sequence,
                    event["event_id"],
                    event["experience_id"],
                    event["athlete_id"],
                    event["event_type"],
                    event["occurred_at"],
                    event["recorded_at"],
                    event["source"]["kind"],
                    event["source"]["ref"],
                    event["supersedes_event_id"],
                    event["idempotency_key"],
                    previous,
                    event_hash,
                    encoded,
                ),
            )
            return event["event_id"]

    def read(self, athlete_id=None):
        with closing(self._connect()) as db:
            if athlete_id:
                return self._read_verified(db, "WHERE athlete_id=?", (athlete_id,))
            return self._read_verified(db)

    def experience_ids(self, athlete_id=None):
        events = self.read(athlete_id)
        return list(dict.fromkeys(event["experience_id"] for event in events))

    def materialize(self, experience_id):
        with closing(self._connect()) as db:
            events = self._read_verified(db, "WHERE experience_id=?", (experience_id,))
        if not events:
            raise KeyError(experience_id)

        originals = {e["event_id"]: e for e in events if e["event_type"] != "CORRECTION"}
        effective = {event_id: deepcopy(event["payload"]) for event_id, event in originals.items()}
        correction_ids = {event_id: [] for event_id in originals}
        for correction in [e for e in events if e["event_type"] == "CORRECTION"]:
            target = correction["supersedes_event_id"]
            if target not in effective:
                raise ValueError("correction target missing from materialized experience")
            effective[target].update(deepcopy(correction["payload"]["set"]))
            correction_ids[target].append(correction["event_id"])

        by_type = {}
        latest = {}
        for event in events:
            if event["event_type"] == "CORRECTION":
                continue
            item = {
                "event_id": event["event_id"],
                "occurred_at": event["occurred_at"],
                "recorded_at": event["recorded_at"],
                "source": deepcopy(event["source"]),
                "payload": effective[event["event_id"]],
                "correction_event_ids": correction_ids[event["event_id"]],
            }
            by_type.setdefault(event["event_type"], []).append(item)
            latest[event["event_type"]] = deepcopy(item["payload"])

        snapshot = {
            "experience_id": experience_id,
            "athlete_id": events[0]["athlete_id"],
            "events": deepcopy(events),
            "by_type": by_type,
            "latest": latest,
        }
        snapshot["outcome_label"] = outcome_label(snapshot)
        return snapshot

    def export_learning_rows(self, athlete_id=None):
        """Export sparse, recomputable learning rows. Unknown remains null."""
        rows = []
        for experience_id in self.experience_ids(athlete_id):
            snapshot = self.materialize(experience_id)
            latest = snapshot["latest"]
            planned = latest.get("PLANNED_EXPOSURE")
            actual = latest.get("ACTUAL_EXPOSURE")
            row = {
                "experience_id": experience_id,
                "athlete_id": snapshot["athlete_id"],
                "planned": planned,
                "actual": actual,
                "subjective_response": latest.get("SUBJECTIVE_RESPONSE"),
                "recovery_response": latest.get("RECOVERY_RESPONSE"),
                "life_context": latest.get("LIFE_CONTEXT"),
                "downstream_outcome": latest.get("DOWNSTREAM_OUTCOME"),
                "benchmark_state": latest.get("BENCHMARK_STATE"),
                "coach_decision": latest.get("COACH_DECISION"),
                "outcome_label": snapshot["outcome_label"],
                "workout_type": (planned or {}).get("workout_type") or (actual or {}).get("workout_type"),
                "sport": (planned or {}).get("sport") or (actual or {}).get("sport"),
                "started_at": (actual or {}).get("started_at"),
            }
            rows.append(row)
        return rows
