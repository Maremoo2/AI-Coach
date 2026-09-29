"""The only application component permitted to commit training-plan versions."""
import hmac
from copy import deepcopy
from datetime import timedelta

from .app_contracts import validate_app
from .coaching import COACH_POLICY, local_date, plan_constraints
from .contracts import digest, instant, require
from .journal import ConflictError
from .provenance import manifest


class HQAuthority:
    def __init__(self, journal, token):
        self.journal = journal
        self._token = token

    def authorize(self, supplied):
        if not self._token or not supplied or not hmac.compare_digest(self._token, supplied):
            raise PermissionError("HQ approval credential required")

    def decide(self, proposal_id, decision, supplied_token, expected_revision, as_of):
        self.authorize(supplied_token)
        require(decision in ("APPROVED", "REJECTED"), "Unknown HQ decision")
        with self.journal.transaction(expected_revision) as (db, state):
            proposal = state["proposals"].get(proposal_id)
            require(proposal is not None and proposal["status"] == "PENDING_HQ", "Proposal absent or already decided")
            if decision == "APPROVED":
                if state["revision"] != proposal["base_revision"] + 1:
                    raise ConflictError("Evidence or profile changed since this proposal; create a fresh proposal")
                current_version = state["plan"]["version"] if state["plan"] else None
                require(current_version == proposal["base_plan_version"], "Plan changed since proposal")
                require(proposal["policy_version"] == COACH_POLICY, "Policy changed; regenerate proposal")
                require(proposal.get("manifest") == manifest(), "Code or schema changed; regenerate proposal")
                require(instant(proposal["created_at"]) <= instant(as_of) <= instant(proposal["created_at"]) + timedelta(days=7), "Proposal expired")
                require(not proposal["blockers"], "Proposal has unresolved blockers")
                plan = deepcopy(proposal["candidate"])
                plan.update(authority="HQ", version="hq-" + digest({"proposal": proposal_id, "revision": state["revision"]})[:16])
                validate_app("plan", plan)
                require(not plan_constraints(plan, state["profile"]), "Plan violates profile constraints")
                today = local_date(state["profile"], as_of).isoformat()
                prior = {s["id"]: s for s in (state["plan"] or {}).get("sessions", [])}
                for session in plan["sessions"]:
                    if session["date"] < today:
                        require(prior.get(session["id"]) == session, "A new or changed session is now in the past")
                self.journal.append(db, "HQ_PLAN", plan["version"], plan, as_of)
            self.journal.append(db, "HQ_DECISION", proposal_id,
                                {"decision": decision, "actor": "HQ", "proposal_hash": digest(proposal)}, as_of)
        return self.journal.state()

    def import_plan(self, plan, supplied_token, expected_revision, as_of):
        """Explicit HQ-authored import, not callable by the recommendation engine."""
        self.authorize(supplied_token)
        validate_app("plan", plan)
        with self.journal.transaction(expected_revision) as (db, state):
            require(state["profile"] and plan["athlete_id"] == state["profile"]["athlete_id"], "Plan athlete mismatch")
            require(plan["version"] not in state["plans"], "Plan version already exists")
            require(not plan_constraints(plan, state["profile"]), "Plan violates profile constraints")
            self.journal.append(db, "HQ_PLAN", plan["version"], plan, as_of)
        return self.journal.state()
