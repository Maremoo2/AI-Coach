"""Adaptive subjective sampling: ask only when the expected information value is high."""
from __future__ import annotations


PROMPTS_NO = {
    "rpe": "Hvor hard var økta totalt (RPE 0–10)?",
    "quality": "Hvordan var kvaliteten på hovedarbeidet (0–1 eller A/B/C)?",
    "pain": "Noe smerte eller unormalt ubehag under/etter økta?",
    "modified_reason_code": "Hva var hovedårsaken til at økta ble endret eller avbrutt?",
    "recovery_24h": "Er restitusjonen normal omtrent 24 timer etter økta?",
    "recovery_48h": "Er restitusjonen normal omtrent 48 timer etter økta?",
    "context_cause": "Var det en tydelig ytre årsak til den svake responsen (søvn, stress, sykdom, reise eller tid)?",
}

PROMPTS_EN = {
    "rpe": "How hard was the session overall (RPE 0–10)?",
    "quality": "How was the quality of the main work (0–1 or A/B/C)?",
    "pain": "Any pain or unusual discomfort during or after the session?",
    "modified_reason_code": "What was the main reason the session was modified or stopped?",
    "recovery_24h": "Is recovery normal about 24 hours after the session?",
    "recovery_48h": "Is recovery normal about 48 hours after the session?",
    "context_cause": "Was there a clear external cause for the poor response (sleep, stress, illness, travel or time)?",
}


def _latest(snapshot, event_type):
    return snapshot.get("latest", {}).get(event_type) or {}


def _high_information(snapshot):
    planned = _latest(snapshot, "PLANNED_EXPOSURE")
    actual = _latest(snapshot, "ACTUAL_EXPOSURE")
    subjective = _latest(snapshot, "SUBJECTIVE_RESPONSE")
    reasons = []

    if planned.get("key_session"):
        reasons.append("KEY_SESSION")
    if planned.get("benchmark"):
        reasons.append("BENCHMARK")
    if planned.get("novel_dose"):
        reasons.append("NOVEL_DOSE")
    intensity = (planned.get("dose") or {}).get("intensity")
    if intensity == "HARD":
        reasons.append("HARD_SESSION")
    if actual.get("execution") in {"B", "C"}:
        reasons.append("MODIFIED_EXECUTION")
    quality = subjective.get("quality", actual.get("quality"))
    if isinstance(quality, (int, float)) and quality < 0.75:
        reasons.append("LOW_QUALITY")
    pain = subjective.get("pain", actual.get("pain"))
    if isinstance(pain, (int, float)) and pain > 0:
        reasons.append("PAIN_SIGNAL")
    return list(dict.fromkeys(reasons))


def adaptive_capture_questions(snapshot, stage="POST_WORKOUT", history_count=0, language="no"):
    """Return a short list of missing questions worth asking now.

    Routine easy sessions are intentionally quiet after the initial baseline.
    """
    prompts = PROMPTS_NO if language == "no" else PROMPTS_EN
    actual = _latest(snapshot, "ACTUAL_EXPOSURE")
    subjective = _latest(snapshot, "SUBJECTIVE_RESPONSE")
    recovery = _latest(snapshot, "RECOVERY_RESPONSE")
    context = _latest(snapshot, "LIFE_CONTEXT")
    reasons = _high_information(snapshot)
    high_value = bool(reasons)
    keys = []

    if stage == "POST_WORKOUT":
        if high_value or history_count < 2:
            if subjective.get("rpe") is None and actual.get("rpe") is None:
                keys.append("rpe")
            if subjective.get("quality") is None and actual.get("quality") is None:
                keys.append("quality")
            if subjective.get("pain") is None and actual.get("pain") is None:
                keys.append("pain")
        if actual.get("execution") in {"B", "C"} and not subjective.get("modified_reason_code"):
            keys.append("modified_reason_code")

    elif stage == "24H":
        if high_value and recovery.get("recovery_24h") is None:
            keys.append("recovery_24h")
        if any(reason in reasons for reason in ("LOW_QUALITY", "PAIN_SIGNAL", "MODIFIED_EXECUTION")):
            if not any(
                context.get(key) is not None
                for key in ("sleep_status", "stress_status", "illness_signal", "injury_signal", "travel")
            ):
                keys.append("context_cause")

    elif stage == "48H":
        if any(reason in reasons for reason in ("KEY_SESSION", "BENCHMARK", "NOVEL_DOSE", "HARD_SESSION", "PAIN_SIGNAL")):
            if recovery.get("recovery_48h") is None:
                keys.append("recovery_48h")
    else:
        raise ValueError("stage must be POST_WORKOUT, 24H or 48H")

    keys = list(dict.fromkeys(keys))
    return {
        "stage": stage,
        "reason_codes": reasons or ["ROUTINE_LOW_INFORMATION"],
        "questions": [{"field": key, "prompt": prompts[key]} for key in keys],
        "max_questions": len(keys),
    }
