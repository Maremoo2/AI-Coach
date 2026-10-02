"""Application use cases; observes facts and proposes changes without plan writes."""
from copy import deepcopy
from datetime import timedelta

from .app_contracts import validate_app
from .coaching import compile_proposal, local_date, overview, coach_reply
from .contracts import digest, instant, require, validate_request
from .engine import evaluate
from .journal import utc_now
from .provenance import manifest


class CoachService:
    def __init__(self, journal, clock=utc_now):
        self.journal = journal
        self.clock = clock

    def snapshot(self):
        return overview(self.journal.state(), self.clock())

    def save(self, kind, value, expected_revision):
        require(kind in ("profile", "goal", "checkin"), "Unsupported record")
        validate_app(kind, value)
        as_of = self.clock()
        with self.journal.transaction(expected_revision) as (db, state):
            if kind == "profile":
                if state["profile"]:
                    require(value["athlete_id"] == state["profile"]["athlete_id"], "Use a separate database for another athlete")
                key = value["athlete_id"]
            else:
                require(state["profile"] and value["athlete_id"] == state["profile"]["athlete_id"], "Athlete mismatch")
                today = local_date(state["profile"], as_of)
                key = value["id"]
                if kind == "goal":
                    require(value["start_date"] <= today.isoformat(), "Baseline date is in the future")
                    require(all(m["date"] <= today.isoformat() for m in value["measurements"]), "Future goal measurement")
                elif kind == "checkin":
                    require(instant(value["observed_at"]) <= instant(as_of), "Future checkin")
                    known = {s["id"]: s for p in state["plans"].values() for s in p["sessions"]}
                    for snapshot in state.get("source_snapshots", {}).values():
                        for planned in snapshot["athlete_data"]["planned"]:
                            known.setdefault(planned["id"], {"date": planned["local_date"]})
                        for actual in snapshot["athlete_data"]["activities"]:
                            known.setdefault("actual-" + actual["id"], {"date": actual["local_date"]})
                    session = known.get(value["session_id"])
                    require(session is not None, "Checkin needs a known HQ session")
                    observed_date = local_date(state["profile"], value["observed_at"])
                    require(session["date"] <= observed_date.isoformat(), "Observation precedes planned session date")
                    previous = state["checkins"].get(value["session_id"])
                    require(not previous or instant(previous["observed_at"]) <= instant(value["observed_at"]), "Older checkin cannot replace newer response")
                    key = value["session_id"]
            self.journal.append(db, kind.upper(), key, deepcopy(value), as_of)
        return self.snapshot()

    def propose(self, expected_revision, week_start=None):
        as_of = self.clock()
        with self.journal.transaction(expected_revision) as (db, state):
            proposal = compile_proposal(state, as_of, week_start)
            proposal["manifest"] = manifest()
            proposal["id"] = digest(proposal)[:24]
            self.journal.append(db, "PROPOSAL", proposal["id"], proposal, as_of)
        return proposal

    def import_evidence(self, request, expected_revision):
        validate_request(request)
        as_of = self.clock()
        require(instant(request["as_of"]) <= instant(as_of), "Future evidence snapshot")
        recommendation = evaluate(request)
        target = next(r for r in request["athlete_data"]["sessions"] if r["planned"]["session_id"] == request["target_session_id"])
        with self.journal.transaction(expected_revision) as (db, state):
            require(state["profile"] and request["athlete_data"]["athlete_id"] == state["profile"]["athlete_id"], "Evidence athlete mismatch")
            key = recommendation["input_hash"]
            if key in state["imports"]:
                return {"status": "ALREADY_IMPORTED", "recommendation": recommendation}
            self.journal.append(db, "IMPORT", key, deepcopy(request), as_of)
            self.journal.append(db, "EVALUATION", key,
                                {"recommendation": recommendation, "workout_type": target["planned"]["workout_type"],
                                 "planned_dose": target["planned"]["dose"]}, as_of)
        return {"status": "IMPORTED", "recommendation": recommendation}

    def chat(self, message):
        require(isinstance(message, str) and 0 < len(message) <= 2000, "Message must be 1–2000 characters")
        return {"message": coach_reply(self.journal.state(), message, self.clock()), "mode": "DETERMINISTIC_COACH", "plan_changed": False}

    def health(self):
        state = self.journal.state()
        mismatches = []
        for key, request in state["imports"].items():
            if evaluate(request) != state["evaluations"][key]["recommendation"]:
                mismatches.append(key)
        return {"journal_integrity": "PASS", "replay": "FAIL" if mismatches else "PASS" if state["imports"] else "NO_EVIDENCE",
                "source_snapshots": len(state.get("source_snapshots", {})),
                "source_collected_at": (state.get("source_snapshot") or {}).get("collected_at"),
                "replayed": len(state["imports"]), "mismatches": mismatches,
                "effectiveness": "NOT_VALIDATED", "auto_promotion": False, "plan_authority": "HQ"}
