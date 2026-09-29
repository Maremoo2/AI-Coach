"""Premium-coach orchestration over an HQ-owned plan."""

from copy import deepcopy

from .progression import adaptation_proposal
from .spot_checks import due_spot_check
from .tool_policy import choose_venue, runtime_reads
from .workout_library import prescribe, template

COACH_POLICY_VERSION = "coach-1.0.0"
GATES = {"GREEN", "AMBER", "RED"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_context(context):
    _require(context.get("schema_version") == "1.0", "Unsupported coach context schema")
    _require(context.get("athlete_id"), "athlete_id is required")
    _require(context.get("as_of"), "as_of is required")
    plan = context.get("hq_plan")
    _require(isinstance(plan, dict) and plan.get("plan_version"), "HQ plan snapshot is required")
    gate = context.get("execution_gate", {})
    _require(gate.get("status") in GATES, "execution_gate.status must be GREEN, AMBER or RED")
    adherence = context.get("adherence", {})
    for key in ("planned_14d", "completed_a", "completed_b", "completed_c", "missed"):
        _require(isinstance(adherence.get(key), int) and adherence[key] >= 0, f"Invalid adherence.{key}")
    today = plan.get("today")
    if today:
        _require(today.get("session_id"), "today.session_id is required")
        _require(today.get("variants", {}).get("A"), "HQ must define a Plan A template")
        for value in today["variants"].values():
            if value is not None:
                template(value)
    return context


def _select_variant(today, gate):
    if not today:
        return "NONE", None
    variants = today["variants"]
    if gate == "GREEN":
        return "A", variants["A"]
    if gate == "AMBER":
        if variants.get("B"):
            return "B", variants["B"]
        if variants.get("C"):
            return "C", variants["C"]
        return "REVIEW", None
    if variants.get("C"):
        return "C", variants["C"]
    return "REVIEW", None


def _motivation(context, selected_variant):
    a = context["adherence"]
    completed = a["completed_a"] + a["completed_b"] + a["completed_c"]
    planned = max(a["planned_14d"], 1)
    rate = completed / planned
    feedback = (context.get("feedback") or {}).get("state")
    lang = context.get("language", "no")

    if lang == "en":
        if selected_variant == "REVIEW":
            return "Protect the long game today. The plan needs an HQ adjustment before you train."
        if a["missed"] > 0 and rate < 0.8:
            return f"The priority is rhythm, not catching up. You completed {completed}/{a['planned_14d']} planned sessions; execute today's approved version cleanly."
        if feedback == "PROGRESS":
            return "Your recent response supports progression. Earn the next step by executing today's session with the same control."
        return "Execute the plan you have, collect clean data, and make the next decision from evidence."

    if selected_variant == "REVIEW":
        return "Beskytt langtidsmålet i dag. Planen trenger en HQ-justering før du trener."
    if a["missed"] > 0 and rate < 0.8:
        return f"Prioriteten er rytme, ikke å ta igjen alt. Du har gjennomført {completed}/{a['planned_14d']} planlagte økter; gjør dagens godkjente variant skikkelig."
    if feedback == "PROGRESS":
        return "Responsen din støtter progresjon. Fortjen neste steg ved å gjennomføre dagens økt med samme kontroll."
    if feedback in ("REDUCE", "CONSOLIDATE"):
        return "Målet i dag er å absorbere treningen, ikke bevise form. En kontrollert økt er fremgang når belastningen krever det."
    return "Gjør planen som står, samle gode data og la neste beslutning bygge på det du faktisk tåler."


def _accountability(context):
    a = context["adherence"]
    completed = a["completed_a"] + a["completed_b"] + a["completed_c"]
    planned = a["planned_14d"]
    return {
        "planned_14d": planned,
        "completed_14d": completed,
        "missed_14d": a["missed"],
        "execution_rate": round(completed / planned, 3) if planned else None,
        "action": "RETURN_TO_RHYTHM" if a["missed"] >= 2 else "STAY_ON_PLAN",
        "no_makeup_stacking": True,
    }


def _performance_actions(context):
    performance = context.get("performance_context", {})
    actions = []
    if performance.get("sleep") == "AMBER":
        actions.append("PROTECT_SLEEP_WINDOW")
    elif performance.get("sleep") == "RED":
        actions.append("HQ_REVIEW_SLEEP_RELATED_LOAD")
    if performance.get("stress") in ("AMBER", "RED"):
        actions.append("REDUCE_NONESSENTIAL_LOAD")
    if performance.get("fueling") == "AMBER":
        actions.append("FUEL_AROUND_KEY_SESSION")
    elif performance.get("fueling") == "RED":
        actions.append("HQ_REVIEW_FUELING_BEFORE_QUALITY")
    if performance.get("travel") is True:
        actions.append("USE_TRAVEL_COMPATIBLE_VARIANT")
    return actions


def build_daily_brief(context):
    context = deepcopy(context)
    validate_context(context)
    plan = context["hq_plan"]
    gate = context["execution_gate"]["status"]
    today = plan.get("today")
    variant, template_id = _select_variant(today, gate)
    hq_actions = []
    workout = None
    adaptation = None

    if template_id:
        rendered = template(template_id)
        venue = choose_venue(rendered, context.get("environment", {}))
        workout = prescribe(template_id, context.get("capacities", {}), venue)
        if context.get("feedback"):
            adaptation = adaptation_proposal(context["feedback"], template_id)
    elif today:
        hq_actions.append("HQ_REVIEW_TODAY_VARIANT")

    spot_check = due_spot_check(
        context["as_of"],
        context.get("benchmarks", []),
        context.get("goal_sports", []),
        gate,
        context.get("days_since_quality", 99),
    )
    if spot_check and today and workout and workout.get("quality"):
        spot_check["status"] = "DEFER_UNTIL_HQ_PLACES_AS_KEY_SESSION"
    elif spot_check:
        spot_check["status"] = "CANDIDATE_FOR_HQ_PLACEMENT"

    return {
        "schema_version": "1.0",
        "coach_policy_version": COACH_POLICY_VERSION,
        "athlete_id": context["athlete_id"],
        "as_of": context["as_of"],
        "authority": "COACH_ADVISORY_HQ_PLAN_ONLY",
        "requires_hq_approval_for_plan_changes": True,
        "plan_version": plan["plan_version"],
        "execution_gate": deepcopy(context["execution_gate"]),
        "selected_variant": variant,
        "workout": workout,
        "motivation": _motivation(context, variant),
        "accountability": _accountability(context),
        "performance_actions": _performance_actions(context),
        "spot_check": spot_check,
        "adaptation_proposal": adaptation,
        "runtime_reads": runtime_reads("DAILY"),
        "post_workout_prompt": (
            "Etter økta: registrer execution A/B/C, RPE, kvalitet, smerte og relevante avvik. "
            "Neste coaching-syklus sammenligner plan → actual → response."
            if context.get("language", "no") == "no"
            else "After training: record execution A/B/C, RPE, quality, pain and relevant deviations. "
                 "The next coaching cycle compares plan → actual → response."
        ),
        "hq_actions": hq_actions,
        "constraints": [
            "NO_DIRECT_PLAN_WRITE", "NO_CATCHUP_STACKING",
            "BENCHMARKS_COUNT_AS_QUALITY", "USER_CORRECTIONS_OVERRIDE_INFERRED_PREFERENCES",
        ],
    }


def post_workout_feedback(evaluation, language="no"):
    state = evaluation["state"]
    evidence = evaluation["evidence"]
    n = evidence["complete_sessions"]
    if language == "en":
        messages = {
            "PROGRESS": f"Good execution and recovery pattern across {n} comparable sessions. HQ can review a one-step progression.",
            "KEEP": f"The dose is working. Keep it stable and collect more clean evidence ({n} complete comparable sessions).",
            "CONSOLIDATE": "The signal is mixed or incomplete. Repeat or absorb before increasing the dose.",
            "REDUCE": "Recent response argues for less load or a simpler version before the next hard exposure.",
            "MOVE": "The workout itself may be fine, but its placement is repeatedly associated with poorer response. HQ should review spacing.",
            "AVOID_COMBINATION": "Repeated evidence links this combination with poorer response than the comparable baseline. HQ should avoid it as a default.",
            "INSUFFICIENT_EVIDENCE": "Not enough comparable evidence yet. Do not overreact to a single session.",
        }
    else:
        messages = {
            "PROGRESS": f"God gjennomføring og recovery-mønster over {n} sammenlignbare økter. HQ kan vurdere ett lite progresjonssteg.",
            "KEEP": f"Dosen fungerer. Behold den stabil og samle mer ren evidens ({n} komplette sammenlignbare økter).",
            "CONSOLIDATE": "Signalet er blandet eller ufullstendig. Gjenta eller absorber før belastningen økes.",
            "REDUCE": "Den siste responsen taler for lavere belastning eller en enklere variant før neste harde eksponering.",
            "MOVE": "Selve økta kan være riktig, men plasseringen er gjentatte ganger koblet til svakere respons. HQ bør se på spacing.",
            "AVOID_COMBINATION": "Gjentatt evidens kobler denne kombinasjonen til svakere respons enn sammenlignbar baseline. HQ bør unngå den som standard.",
            "INSUFFICIENT_EVIDENCE": "Vi har ikke nok sammenlignbar evidens ennå. Ikke overreager på én enkelt økt.",
        }
    return {
        "state": state, "message": messages[state], "confidence": evaluation["confidence"],
        "reason_codes": evaluation["reason_codes"], "requires_hq_approval": True,
    }
