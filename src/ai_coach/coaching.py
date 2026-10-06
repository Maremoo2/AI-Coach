"""Pure coaching summaries and proposal compiler. Never writes a plan."""
from copy import deepcopy
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from .contracts import digest, instant
from .taxonomy import WORKOUTS

COACH_POLICY = "coach-1.0.0"
TITLES = {"RUN_EASY": "Rolig løp", "RUN_THRESHOLD": "Terskel løp",
          "BIKE_AEROBIC": "Rolig sykkel", "BIKE_SWEETSPOT": "Sweetspot sykkel",
          "BIKE_THRESHOLD": "Terskel sykkel", "SWIM_TECHNIQUE": "Svømmeteknikk",
          "SWIM_CSS": "CSS-svømming", "STRENGTH_GENERAL": "Styrke", "CROSSFIT": "CrossFit"}
EASY = {"RUN_EASY", "BIKE_AEROBIC", "SWIM_TECHNIQUE"}
TITLES.update({"RUN_LONG": "Langtur løp", "RUN_INTERVAL": "Løpsintervaller",
               "RUN_HILLS": "Bakkeløp", "RUN_BRICK": "Kombinasjonsløp",
               "BIKE_ENDURANCE": "Langtur sykkel", "BIKE_VO2": "Sykkelintervaller",
               "BIKE_BRICK": "Kombinasjonssykkel", "SWIM_ENDURANCE": "Utholdenhetssvømming",
               "SWIM_OPEN_WATER": "Åpent vann", "STRENGTH_FULLBODY": "Helkroppsstyrke",
               "STRENGTH_LOWER": "Underkroppsstyrke", "STRENGTH_UPPER": "Overkroppsstyrke",
               "MOBILITY": "Mobilitet", "RECOVERY": "Restitusjon"})


def local_date(profile, as_of):
    return instant(as_of).astimezone(ZoneInfo(profile["timezone"])).date()


def goal_progress(goal, today):
    measurements = sorted((m for m in goal["measurements"] if m["date"] <= today.isoformat()), key=lambda m: m["date"])
    latest = measurements[-1] if measurements else None
    current = latest["value"] if latest else goal["baseline"]
    fraction = (current - goal["baseline"]) / (goal["target"] - goal["baseline"])
    start, end = date.fromisoformat(goal["start_date"]), date.fromisoformat(goal["target_date"])
    milestones = [{"date": (start + timedelta(days=round((end - start).days * part / 4))).isoformat(),
                   "reference_value": round(goal["baseline"] + (goal["target"] - goal["baseline"]) * part / 4, 2)}
                  for part in (1, 2, 3, 4)]
    status = "ACHIEVED" if latest and fraction >= 1 else "NO_MEASUREMENT" if not latest else "OVERDUE" if today > end else "TRACKING"
    return {**goal, "current": current, "latest_measurement": latest,
            "progress_percent": round(max(0, min(100, fraction * 100)), 1), "tracking_status": status,
            "days_remaining": (end - today).days, "milestones": milestones,
            "milestone_note": "Lineære referansepunkter for oppfølging, ikke en prognose eller treningsdose."}


def recent_checkins(state, as_of, days=7):
    cutoff = instant(as_of)
    return sorted((c for c in state["checkins"].values()
                   if cutoff - timedelta(days=days) <= instant(c["observed_at"]) <= cutoff),
                  key=lambda c: (instant(c["observed_at"]), c["id"]))


def alerts(state, as_of):
    recent = recent_checkins(state, as_of)
    result = []
    if any(c["pain"] is not None and c["pain"] > 0 for c in recent):
        result.append("PAIN_REPORTED")
    if any(c["recovery"] == "POOR" for c in recent):
        result.append("RECOVERY_REVIEW")
    if not recent:
        result.append("NO_RECENT_CHECKIN")
    elif any(c["rpe"] is None or c["quality"] is None or c["pain"] is None
             or c["recovery"] == "UNKNOWN" for c in recent):
        result.append("INCOMPLETE_RECENT_CHECKIN")
    return result


def plan_constraints(plan, profile):
    errors = []
    if profile["weekly_minutes"] is None or profile["max_session_minutes"] is None:
        return ["AVAILABILITY_NOT_CONFIRMED"]
    total = sum(s["duration_min"] for s in plan["sessions"])
    if total > profile["weekly_minutes"]:
        errors.append("WEEKLY_TIME_BUDGET")
    by_day = {}
    for s in plan["sessions"]:
        day = date.fromisoformat(s["date"])
        if day.weekday() not in profile["available_days"]:
            errors.append(f"UNAVAILABLE_DAY:{s['id']}")
        if s["duration_min"] > profile["max_session_minutes"]:
            errors.append(f"SESSION_TIME_BUDGET:{s['id']}")
        if s["workout_type"] in profile["blocked_workouts"]:
            errors.append(f"BLOCKED_WORKOUT:{s['id']}")
        by_day.setdefault(s["date"], []).append(s)
    for day, sessions in by_day.items():
        if len(sessions) > 1:
            errors.append(f"STACKED_SESSIONS:{day}")
    hard = sorted(date.fromisoformat(s["date"]) for s in plan["sessions"] if s["intensity"] == "HARD")
    if any((b - a).days < 2 for a, b in zip(hard, hard[1:])):
        errors.append("ADJACENT_HARD_SESSIONS")
    return errors


def compile_proposal(state, as_of, week_start=None):
    profile = state["profile"]
    if profile is None:
        raise ValueError("Registrer profilen først.")
    if profile["weekly_minutes"] is None or profile["max_session_minutes"] is None:
        raise ValueError("Bekreft tilgjengelig tid før nye planforslag.")
    if (state.get("source_snapshot") or state.get("garmin_sync")) and state["plan"] is None:
        raise ValueError("Ekstern HQ-plan er importert som kildesnapshot. HQ må eksplisitt opprette lokal plan før doseforslag.")
    today = local_date(profile, as_of)
    current = state["plan"]
    target_week = date.fromisoformat(week_start) if week_start else date.fromisoformat(current["week_start"]) if current else today - timedelta(days=today.weekday())
    if target_week.weekday() != 0:
        raise ValueError("Uken må starte på en mandag.")
    if target_week + timedelta(days=6) < today:
        raise ValueError("Velg inneværende eller kommende uke.")
    extending = current is None or current["week_start"] != target_week.isoformat()
    changes, reasons = [], []
    if extending and current is not None:
        shift = target_week - date.fromisoformat(current["week_start"])
        if shift.days <= 0:
            raise ValueError("Kan bare videreføre planen til en senere uke.")
        sessions = deepcopy(current["sessions"])
        for i, session in enumerate(sessions):
            session["id"] = f"w{target_week.isoformat()}-{i}"
            session["date"] = (date.fromisoformat(session["date"]) + shift).isoformat()
        reasons.append("CARRY_FORWARD_APPROVED_STRUCTURE_NO_AUTOMATIC_PROGRESSION")
    elif extending:
        days = [target_week + timedelta(days=d) for d in profile["available_days"] if target_week + timedelta(days=d) >= today]
        days.sort()
        duration = min(30, profile["max_session_minutes"], profile["weekly_minutes"] // max(1, len(days)))
        workouts = [w for w in profile["preferred_workouts"] if w in EASY and w not in profile["blocked_workouts"]]
        if not days or duration < 5 or not workouts:
            raise ValueError("Trenger tilgjengelig dag, minst fem minutter og en foretrukket rolig økttype. HQ må angi øvrige økter.")
        sessions = [{"id": f"w{target_week.isoformat()}-{i}", "date": d.isoformat(),
                     "workout_type": workouts[i % len(workouts)], "duration_min": duration,
                     "intensity": "EASY", "purpose": "Startutkast til HQ: bygg kontinuitet og registrer respons.", "locked": False}
                    for i, d in enumerate(days)]
        reasons.append("STARTER_DRAFT_REQUIRES_HQ_REVIEW")
    else:
        sessions = deepcopy(current["sessions"])
    flags = alerts(state, as_of)
    reasons.extend(flags)
    processed_types = set()
    for session in sessions:
        if session["locked"] or session["date"] < today.isoformat() or session["id"] in state["checkins"]:
            continue
        before = deepcopy(session)
        action = None
        if "PAIN_REPORTED" in flags:
            reasons.append("PAIN_REQUIRES_HQ_REVIEW_NO_AUTOMATIC_DOSE")
        elif "RECOVERY_REVIEW" in flags:
            if session["workout_type"] in EASY:
                session["duration_min"] = max(5, round(session["duration_min"] * 0.8))
                action = "REDUCE"
            else:
                reasons.append("NON_EASY_RECOVERY_CHANGE_REQUIRES_HQ")
        elif not extending and session["workout_type"] not in processed_types:
            # At most one progression per type/week. Only exact, continuous easy dose.
            candidates = [e for e in state["evaluations"].values()
                          if e["workout_type"] == session["workout_type"]
                          and 0 <= (instant(as_of) - instant(e["recommendation"]["as_of"])).total_seconds() <= 7 * 86400
                          and e["planned_dose"]["duration_min"] == session["duration_min"]
                          and e["planned_dose"]["intervals"] == 0
                          and e["planned_dose"]["volume"] is None
                          and e["planned_dose"]["intensity"] == session["intensity"]]
            evidence = max(candidates, key=lambda e: (instant(e["recommendation"]["as_of"]), e["recommendation"]["input_hash"])) if candidates else None
            if evidence and session["workout_type"] in EASY and not flags:
                recommendation = evidence["recommendation"]
                if recommendation["state"] == "PROGRESS":
                    session["duration_min"] += min(5, max(1, round(session["duration_min"] * 0.05)))
                    action = "PROGRESS"
                elif recommendation["state"] == "REDUCE":
                    session["duration_min"] = max(5, round(session["duration_min"] * 0.8))
                    action = "REDUCE"
                elif recommendation["state"] in ("MOVE", "AVOID_COMBINATION"):
                    reasons.append("SPACING_SIGNAL_REQUIRES_HQ_REVIEW")
            if not evidence:
                reasons.append("NO_CURRENT_COMPARABLE_EVIDENCE_KEEP_DOSE")
        if before != session:
            changes.append({"session_id": session["id"], "before": before, "after": deepcopy(session), "state": action})
            processed_types.add(session["workout_type"])
    candidate = {"athlete_id": profile["athlete_id"], "week_start": target_week.isoformat(), "sessions": sessions}
    blockers = plan_constraints(candidate, profile)
    if "PAIN_REPORTED" in flags:
        blockers.append("PAIN_REQUIRES_HQ_REVIEW")
    for item in changes:
        if item["state"] == "PROGRESS" and blockers:
            session = next(s for s in sessions if s["id"] == item["session_id"])
            session.update(item["before"])
    changes = [c for c in changes if c["after"] == next(s for s in sessions if s["id"] == c["session_id"])]
    blockers = plan_constraints(candidate, profile) + (["PAIN_REQUIRES_HQ_REVIEW"] if "PAIN_REPORTED" in flags else [])
    payload = {"created_at": as_of, "base_revision": state["revision"],
               "base_plan_version": current["version"] if current else None,
               "policy_version": COACH_POLICY, "status": "PENDING_HQ", "candidate": candidate,
               "changes": changes, "reason_codes": sorted(set(reasons)) or ["KEEP_EXISTING_PLAN"],
               "blockers": blockers, "requires_hq_approval": True,
               "evidence_hashes": sorted(e["recommendation"]["input_hash"] for e in state["evaluations"].values())}
    payload["id"] = digest(payload)[:24]
    return payload


def overview(state, as_of):
    profile = state["profile"]
    if profile is None:
        return {"needs_onboarding": True, "revision": state["revision"], "profile": None}
    today = local_date(profile, as_of)
    recent = recent_checkins(state, as_of)
    flags = alerts(state, as_of)
    upcoming = [s for s in (state["plan"] or {}).get("sessions", []) if s["date"] >= today.isoformat() and s["id"] not in state["checkins"]]
    upcoming.sort(key=lambda s: (s["date"], s["id"]))
    done = sum(c["status"] == "DONE" for c in recent)
    if "PAIN_REPORTED" in flags:
        message = "Du har meldt smerte. Det er viktig informasjon, ikke et nederlag. Avklar videre belastning med HQ før progresjon."
    elif "RECOVERY_REVIEW" in flags:
        message = "Restitusjonen fortjener plass. Et lettere forslag ligger innenfor målet om kontinuitet. Ikke ta igjen tapte økter ved å stable dem."
    elif done:
        message = f"Du har registrert {done} fullførte økter siste sju dager. Fortsett å beskrive responsen ærlig; kvalitet teller mer enn å fylle kalenderen."
    else:
        message = "Start med én gjennomførbar økt og en ærlig innsjekk. Små, gjentatte steg gir et bedre beslutningsgrunnlag."
    if profile["coaching_tone"] == "DIRECT":
        message = "Neste steg: registrer respons og følg den godkjente planen. " + message
    elif profile["coaching_tone"] == "ENCOURAGING":
        message = "Vi tar dette steg for steg. " + message
    missing = sum(c["rpe"] is None or c["quality"] is None or c["pain"] is None or c["recovery"] == "UNKNOWN" for c in recent)
    from .onboarding import source_overview
    from .garmin import merged_snapshot
    source_context = source_overview(merged_snapshot(state), as_of, profile["timezone"])
    return {"needs_onboarding": False, "as_of": as_of, "revision": state["revision"], "profile": profile,
            "source_context": source_context,
            "today": today.isoformat(), "plan": state["plan"], "upcoming": upcoming,
            "goals": [goal_progress(g, today) for g in state["goals"].values()],
            "checkins": list(state["checkins"].values()), "proposals": list(state["proposals"].values()),
            "evaluations": list(state["evaluations"].values()),
            "weekly_review": {"window_days": 7, "completed": done, "partial": sum(c["status"] == "PARTIAL" for c in recent),
                              "skipped": sum(c["status"] == "SKIPPED" for c in recent),
                              "actual_minutes": sum(c["duration_min"] for c in recent), "incomplete_checkins": missing},
            "coach_message": message, "alerts": flags,
            "health": {"journal": "VERIFIED", "athlete_effectiveness": "NOT_VALIDATED",
                       "live_sync": "NOT_CONNECTED", "auto_plan_write": False,
                       "data_quality": "MISSING" if not recent else "INCOMPLETE" if missing else "RECORDED"}}


def coach_reply(state, message, as_of):
    data = overview(state, as_of)
    if data["needs_onboarding"]:
        return "Legg inn navn, tilgjengelig tid og foretrukne økter først. Deretter kan vi sette et målbart mål."
    lower = message.casefold()
    if any(word in lower for word in ("smerte", "vondt", "pain", "skade")):
        return "Registrer smerte og hva du merket i innsjekken. Jeg kan ikke diagnostisere dette. HQ må vurdere belastningen; jeg gir ikke et progresjonsforslag ut fra denne meldingen."
    if any(word in lower for word in ("mål", "goal", "progres")):
        if data.get("source_context"):
            return " ".join(g["description"] for g in data["source_context"]["goals"]) + " Måldato og fremgangsprosent beregnes ikke uten bekreftet konkurranse og baseline."
        active = [g for g in data["goals"] if g["status"] == "ACTIVE"]
        if not active:
            return "Sett ett målbart mål: utgangspunkt, ønsket verdi, enhet og dato. Milepælene blir kontrollpunkter, ikke løfter om fremgang."
        g = active[0]
        return f"Målet ditt er {g['title']}: {g['target']} {g['unit']} innen {g['target_date']}. Sist registrert: {g['current']} {g['unit']}. Legg inn en ny måling for å følge utviklingen."
    if any(word in lower for word in ("uke", "week", "oppsummer")):
        if data.get("source_context"):
            s = data["source_context"]
            return f"Importerte Tredict-data til {s['latest_activity_date']}: {s['recent_count']} aktiviteter og {s['recent_minutes']} registrerte aktivitetsminutter siste sju dager. {s['assessment']} Dette er et datert snapshot, ikke kontinuerlig synk."
        w = data["weekly_review"]
        return f"Siste sju dager: {w['completed']} fullførte, {w['partial']} delvise og {w['skipped']} droppede økter; {w['actual_minutes']} registrerte minutter. {w['incomplete_checkins']} innsjekker mangler responsdata. " + data["coach_message"]
    if any(word in lower for word in ("dag", "økt", "today", "plan")):
        if data.get("source_context") and not data["plan"]:
            if data["source_context"]["today_rest"]:
                return "HQ har eksplisitt registrert denne datoen som hvile i det importerte plangrunnlaget. Det opprettes ingen ekstra økt. Sjekk siste HQ-vurdering hvis planen siden er endret."
            upcoming = data["source_context"]["upcoming"]
            if upcoming:
                s = upcoming[0]
                return f"Neste økt i importert HQ/Tredict-plan: {s['title']}, {s['local_date']}. {s['dose_note']} Planen er et datert kildesnapshot; sjekk siste HQ-vurdering før gjennomføring."
            return "Ingen kommende økt i importens dekningsperiode. Dette betyr ikke at HQ har bestemt hvile."
        if data["upcoming"]:
            s = data["upcoming"][0]
            return f"Neste godkjente økt: {TITLES[s['workout_type']]}, {s['duration_min']} minutter, {s['date']}. {s['purpose']} " + data["coach_message"]
        return "Ingen kommende økt er godkjent i den lokale HQ-planen. Lag et forslag og få det vurdert av HQ."
    return data["coach_message"] + " Jeg kan oppsummere uken, vise neste økt eller følge målet ditt."
