"""Materialize longitudinal experience rows into an explainable personal response profile."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from statistics import mean

from .sequences import build_sequence_observations

PROFILE_VERSION = "1.0"
CURRENT_WINDOW_DAYS = 56
RECENT_WINDOW_DAYS = 28
HISTORY_WINDOW_DAYS = 180

EVIDENCE_STATES = {
    "INSUFFICIENT_EVIDENCE",
    "OBSERVATION",
    "EARLY_PATTERN",
    "MIXED_PATTERN",
    "CANDIDATE_PATTERN",
    "ESTABLISHED_PERSONAL_RULE",
}


def _instant(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include an offset")
    return parsed.astimezone(timezone.utc)


def _as_of(value):
    parsed = _instant(value)
    if parsed is None:
        raise ValueError("as_of is required")
    return parsed


def _age_days(as_of, started_at):
    started = _instant(started_at)
    if started is None:
        return None
    return max(0.0, (as_of - started).total_seconds() / 86400)


def recency_weight(age_days):
    if age_days is None:
        return 0.0
    if age_days <= 28:
        return 1.0
    if age_days <= 56:
        return 0.75
    if age_days <= 84:
        return 0.50
    if age_days <= 180:
        return 0.25
    return 0.0


def absorption_label(row):
    """GOOD requires recovery/downstream evidence; execution alone is insufficient."""
    recovery = row.get("recovery_response") or {}
    downstream = row.get("downstream_outcome") or {}
    values = [
        recovery.get("recovery_24h"),
        recovery.get("recovery_48h"),
        downstream.get("next_session_quality"),
    ]
    known = [value for value in values if value is not None]
    if not known:
        return "UNKNOWN"
    if any(value == "POOR" for value in known):
        return "POOR"
    if all(value in {"NORMAL", "GOOD"} for value in known):
        return "GOOD"
    return "UNKNOWN"


def execution_label(row):
    actual = row.get("actual") or {}
    subjective = row.get("subjective_response") or {}
    execution = actual.get("execution")
    quality = subjective.get("quality", actual.get("quality"))
    pain = subjective.get("pain", actual.get("pain"))
    if execution == "C" or (isinstance(quality, (int, float)) and quality < 0.60) or (
        isinstance(pain, (int, float)) and pain > 0
    ):
        return "POOR"
    if execution == "A" and isinstance(quality, (int, float)) and quality >= 0.80:
        return "GOOD"
    return "UNKNOWN"


def _dose_signature(row):
    planned = row.get("planned") or {}
    actual = row.get("actual") or {}
    signature = planned.get("dose_signature") or actual.get("dose_signature")
    if signature:
        return deepcopy(signature)
    dose = planned.get("dose") or {}
    values = {
        "workout_type": row.get("workout_type"),
        "duration_min": dose.get("duration_min") or actual.get("duration_min"),
        "intervals": dose.get("intervals"),
        "work_min": dose.get("work_min"),
        "rest_min": dose.get("rest_min"),
        "intensity": dose.get("intensity"),
        "volume": deepcopy(dose.get("volume") or actual.get("volume")),
    }
    return {key: value for key, value in values.items() if value is not None}


def _dose_key(row):
    return json.dumps(_dose_signature(row), sort_keys=True, separators=(",", ":"))


def _completeness(row):
    present = sum(
        row.get(key) is not None
        for key in ("actual", "subjective_response", "recovery_response", "downstream_outcome")
    )
    return round(present / 4, 3)


def _evidence_state(known, good, poor, recent_known):
    if known == 0:
        return "INSUFFICIENT_EVIDENCE"
    if known == 1:
        return "OBSERVATION"
    dominant = max(good, poor) / known
    if known <= 3:
        return "EARLY_PATTERN"
    if known >= 6 and dominant >= 0.80 and recent_known >= 2:
        return "ESTABLISHED_PERSONAL_RULE"
    if known >= 4 and dominant >= 0.70:
        return "CANDIDATE_PATTERN"
    return "MIXED_PATTERN"


def _confidence(known, unknown, dominant_rate, recent_known):
    total = known + unknown
    if total == 0:
        return 0.0
    coverage = known / total
    sample = min(1.0, known / 8)
    consistency = 0.5 + 0.5 * dominant_rate
    recency = min(1.0, recent_known / max(known, 1) + 0.25)
    return round(min(0.95, sample * coverage * consistency * recency), 3)


def _aggregate_group(rows, as_of, *, scope, key):
    rows = sorted(rows, key=lambda row: row.get("started_at") or "")
    current = []
    recent = []
    history = []
    for row in rows:
        age = _age_days(as_of, row.get("started_at"))
        if age is None:
            continue
        if age <= HISTORY_WINDOW_DAYS:
            history.append(row)
        if age <= CURRENT_WINDOW_DAYS:
            current.append(row)
        if age <= RECENT_WINDOW_DAYS:
            recent.append(row)

    labels = [absorption_label(row) for row in current]
    recent_labels = [absorption_label(row) for row in recent]
    known = sum(label != "UNKNOWN" for label in labels)
    good = labels.count("GOOD")
    poor = labels.count("POOR")
    unknown = labels.count("UNKNOWN")
    recent_known = sum(label != "UNKNOWN" for label in recent_labels)
    dominant = max(good, poor) / known if known else 0.0

    execution = [execution_label(row) for row in current]
    exec_known = sum(label != "UNKNOWN" for label in execution)
    executions = [((row.get("actual") or {}).get("execution")) for row in current]
    plan_a_denominator = sum(value in {"A", "B", "C"} for value in executions)
    plan_a_count = executions.count("A")

    recovery24 = [
        (row.get("recovery_response") or {}).get("recovery_24h")
        for row in current
    ]
    recovery24_known = [value for value in recovery24 if value is not None]
    downstream = [
        (row.get("downstream_outcome") or {}).get("next_session_quality")
        for row in current
    ]
    downstream_known = [value for value in downstream if value is not None]

    weighted_good = weighted_poor = 0.0
    for row in history:
        weight = recency_weight(_age_days(as_of, row.get("started_at")))
        label = absorption_label(row)
        if label == "GOOD":
            weighted_good += weight
        elif label == "POOR":
            weighted_poor += weight
    weighted_known = weighted_good + weighted_poor

    first = rows[0] if rows else {}
    return {
        "scope": scope,
        "key": key,
        "workout_type": first.get("workout_type"),
        "sport": first.get("sport"),
        "dose_signature": _dose_signature(first) if scope == "DOSE_SIGNATURE" else None,
        "lifetime_exposures": len(rows),
        "history_180d_exposures": len(history),
        "current_56d_exposures": len(current),
        "recent_28d_exposures": len(recent),
        "absorption": {
            "known": known,
            "good": good,
            "poor": poor,
            "unknown": unknown,
            "good_rate_known": round(good / known, 3) if known else None,
            "weighted_good_rate_180d": round(weighted_good / weighted_known, 3)
            if weighted_known else None,
        },
        "execution": {
            "known": exec_known,
            "good": execution.count("GOOD"),
            "poor": execution.count("POOR"),
            "unknown": execution.count("UNKNOWN"),
            "plan_a_rate_known": round(plan_a_count / plan_a_denominator, 3)
            if plan_a_denominator else None,
        },
        "recovery": {
            "recovery_24h_known": len(recovery24_known),
            "normal_24h": recovery24_known.count("NORMAL"),
            "normal_24h_rate": round(recovery24_known.count("NORMAL") / len(recovery24_known), 3)
            if recovery24_known else None,
            "next_session_known": len(downstream_known),
            "good_next_session": downstream_known.count("GOOD"),
            "good_next_session_rate": round(downstream_known.count("GOOD") / len(downstream_known), 3)
            if downstream_known else None,
        },
        "data_completeness_mean": round(mean(_completeness(row) for row in current), 3)
        if current else 0.0,
        "evidence_state": _evidence_state(known, good, poor, recent_known),
        "confidence": _confidence(known, unknown, dominant, recent_known),
        "can_write_plan": False,
        "source_experience_ids": sorted(row["experience_id"] for row in history),
    }


def build_dose_profiles(rows, as_of):
    by_type = defaultdict(list)
    by_dose = defaultdict(list)
    for row in rows:
        if not row.get("workout_type") or not row.get("started_at"):
            continue
        by_type[row["workout_type"]].append(row)
        by_dose[(row["workout_type"], _dose_key(row))].append(row)
    profiles = []
    for key in sorted(by_type):
        profiles.append(_aggregate_group(by_type[key], as_of, scope="WORKOUT_TYPE", key=key))
    for workout_type, dose_key in sorted(by_dose):
        profiles.append(_aggregate_group(
            by_dose[(workout_type, dose_key)],
            as_of,
            scope="DOSE_SIGNATURE",
            key=f"{workout_type}:{dose_key}",
        ))
    return profiles


def _sequence_profile(pattern_key, observations, rows_by_id, as_of):
    current = []
    recent = []
    for obs in observations:
        row = rows_by_id[obs["target_experience_id"]]
        age = _age_days(as_of, row.get("started_at"))
        if age is not None and age <= CURRENT_WINDOW_DAYS:
            current.append(obs)
            if age <= RECENT_WINDOW_DAYS:
                recent.append(obs)

    known = [obs for obs in current if obs["outcome"] in {"GOOD", "POOR"}]
    good = sum(obs["outcome"] == "GOOD" for obs in known)
    poor = sum(obs["outcome"] == "POOR" for obs in known)
    unknown = len(current) - len(known)
    recent_known = sum(obs["outcome"] in {"GOOD", "POOR"} for obs in recent)
    dominant = max(good, poor) / len(known) if known else 0.0

    target_type = pattern_key.split("->", 1)[1].split(":", 1)[0]
    exposed_target_ids = {obs["target_experience_id"] for obs in current}
    baseline = []
    for row in rows_by_id.values():
        age = _age_days(as_of, row.get("started_at"))
        if (
            age is not None
            and age <= CURRENT_WINDOW_DAYS
            and row.get("workout_type") == target_type
            and row["experience_id"] not in exposed_target_ids
        ):
            label = absorption_label(row)
            if label in {"GOOD", "POOR"}:
                baseline.append(label)

    poor_rate = poor / len(known) if known else None
    baseline_poor = baseline.count("POOR") / len(baseline) if baseline else None
    if len(known) >= 3 and len(baseline) >= 3 and poor_rate is not None and baseline_poor is not None:
        difference = poor_rate - baseline_poor
        if poor_rate >= 2 / 3 and baseline_poor <= 1 / 3 and difference >= 0.40:
            comparison_signal = "POSSIBLE_NEGATIVE_SPACING_SIGNAL"
        elif abs(difference) < 0.20:
            comparison_signal = "NO_CLEAR_DIFFERENCE"
        else:
            comparison_signal = "DESCRIPTIVE_DIFFERENCE"
    else:
        difference = None if poor_rate is None or baseline_poor is None else poor_rate - baseline_poor
        comparison_signal = "INSUFFICIENT_BASELINE"

    return {
        "pattern_key": pattern_key,
        "current_56d_exposures": len(current),
        "recent_28d_exposures": len(recent),
        "known": len(known),
        "good": good,
        "poor": poor,
        "unknown": unknown,
        "good_rate_known": round(good / len(known), 3) if known else None,
        "poor_rate_known": round(poor_rate, 3) if poor_rate is not None else None,
        "baseline_known": len(baseline),
        "baseline_poor_rate": round(baseline_poor, 3) if baseline_poor is not None else None,
        "poor_rate_difference": round(difference, 3) if difference is not None else None,
        "comparison_signal": comparison_signal,
        "evidence_state": _evidence_state(len(known), good, poor, recent_known),
        "confidence": _confidence(len(known), unknown, dominant, recent_known),
        "can_write_plan": False,
        "source_observation_ids": sorted(obs["id"] for obs in current),
    }


def build_sequence_profiles(rows, as_of):
    rows_for_sequence = []
    rows_by_id = {}
    for row in rows:
        copy = deepcopy(row)
        copy["outcome_label"] = absorption_label(row)
        rows_for_sequence.append(copy)
        rows_by_id[row["experience_id"]] = copy
    observations = build_sequence_observations(rows_for_sequence)
    grouped = defaultdict(list)
    for observation in observations:
        grouped[observation["pattern_key"]].append(observation)
    return [_sequence_profile(key, grouped[key], rows_by_id, as_of) for key in sorted(grouped)]


def build_weekly_tolerance(rows, as_of):
    cutoff = as_of - timedelta(days=56)
    buckets = defaultdict(list)
    for row in rows:
        started = _instant(row.get("started_at"))
        if started is None or started < cutoff or started > as_of:
            continue
        year, week, _ = started.isocalendar()
        buckets[f"{year}-W{week:02d}"].append(row)

    result = []
    for week in sorted(buckets):
        items = buckets[week]
        sport_counts = Counter(row.get("sport") for row in items if row.get("sport"))
        durations = [
            (row.get("actual") or {}).get("duration_min")
            for row in items
            if isinstance((row.get("actual") or {}).get("duration_min"), (int, float))
        ]
        labels = [absorption_label(row) for row in items]
        known = [label for label in labels if label != "UNKNOWN"]
        result.append({
            "week": week,
            "sessions": len(items),
            "duration_min_known_total": round(sum(durations), 1) if durations else None,
            "sport_counts": dict(sorted(sport_counts.items())),
            "absorption_known": len(known),
            "good": known.count("GOOD"),
            "poor": known.count("POOR"),
            "unknown": labels.count("UNKNOWN"),
            "well_observed_and_absorbed": bool(len(known) >= 2 and known.count("POOR") == 0),
        })
    return result


def build_decision_profiles(rows, as_of):
    grouped = defaultdict(list)
    for row in rows:
        decision = row.get("coach_decision") or {}
        key = decision.get("state") or decision.get("decision")
        age = _age_days(as_of, row.get("started_at"))
        if key and age is not None and age <= HISTORY_WINDOW_DAYS:
            grouped[key].append(row)

    result = []
    for key in sorted(grouped):
        items = grouped[key]
        current = [row for row in items if (_age_days(as_of, row.get("started_at")) or 0) <= CURRENT_WINDOW_DAYS]
        labels = [absorption_label(row) for row in current]
        known = [label for label in labels if label in {"GOOD", "POOR"}]
        result.append({
            "decision_key": key,
            "history_180d_decisions": len(items),
            "current_56d_decisions": len(current),
            "known_outcomes": len(known),
            "good_outcomes": known.count("GOOD"),
            "poor_outcomes": known.count("POOR"),
            "unknown_outcomes": labels.count("UNKNOWN"),
            "good_rate_known": round(known.count("GOOD") / len(known), 3) if known else None,
            "evaluation_state": "EVALUABLE" if len(known) >= 3 else "INSUFFICIENT_EVIDENCE",
            "can_write_plan": False,
        })
    return result


def _data_quality(rows, as_of):
    current = [
        row for row in rows
        if row.get("started_at") and (_age_days(as_of, row["started_at"]) or 0) <= CURRENT_WINDOW_DAYS
    ]
    denominator = len(current)
    return {
        "current_experiences": denominator,
        "actual_coverage": round(sum(row.get("actual") is not None for row in current) / denominator, 3)
        if denominator else None,
        "subjective_coverage": round(sum(row.get("subjective_response") is not None for row in current) / denominator, 3)
        if denominator else None,
        "recovery_coverage": round(sum(row.get("recovery_response") is not None for row in current) / denominator, 3)
        if denominator else None,
        "downstream_coverage": round(sum(row.get("downstream_outcome") is not None for row in current) / denominator, 3)
        if denominator else None,
        "missing_is_never_normal": True,
    }


def build_personal_response_profile(rows, as_of, athlete_id=None):
    as_of_dt = _as_of(as_of)
    clean = []
    for row in rows:
        if athlete_id and row.get("athlete_id") != athlete_id:
            continue
        if not row.get("experience_id"):
            raise ValueError("every learning row requires experience_id")
        clean.append(deepcopy(row))

    inferred_athletes = sorted({row.get("athlete_id") for row in clean if row.get("athlete_id")})
    if athlete_id is None:
        if len(inferred_athletes) > 1:
            raise ValueError("profile may only contain one athlete")
        athlete_id = inferred_athletes[0] if inferred_athletes else "unknown"

    return {
        "schema_version": "1.0",
        "profile_version": PROFILE_VERSION,
        "athlete_id": athlete_id,
        "as_of": as_of,
        "authority": "DESCRIPTIVE_ADVISORY_ONLY",
        "can_write_plan": False,
        "windows_days": {
            "recent": RECENT_WINDOW_DAYS,
            "current": CURRENT_WINDOW_DAYS,
            "history": HISTORY_WINDOW_DAYS,
        },
        "data_quality": _data_quality(clean, as_of_dt),
        "dose_profiles": build_dose_profiles(clean, as_of_dt),
        "sequence_profiles": build_sequence_profiles(clean, as_of_dt),
        "weekly_tolerance": build_weekly_tolerance(clean, as_of_dt),
        "decision_profiles": build_decision_profiles(clean, as_of_dt),
        "constraints": [
            "HQ_REMAINS_SOLE_PLAN_AUTHORITY",
            "UNKNOWN_IS_NOT_NORMAL",
            "RECENT_EVIDENCE_WEIGHS_MORE_THAN_OLD_EVIDENCE",
            "NO_RULE_FROM_SINGLE_EXPOSURE",
            "NO_ML_IN_PROFILE_V1",
        ],
    }


def render_profile_summary(profile, language="no", max_items=8):
    statements = []
    for item in profile.get("dose_profiles", []):
        if item["scope"] != "WORKOUT_TYPE":
            continue
        absorption = item["absorption"]
        known = absorption["known"]
        if known == 0:
            continue
        good = absorption["good"]
        poor = absorption["poor"]
        unknown = absorption["unknown"]
        if language == "no":
            text = (
                f"{item['workout_type']}: {good} av {known} kjente responser er godt absorbert "
                f"({poor} dårlige"
                + (f", {unknown} fortsatt ukjente" if unknown else "")
                + f"). Evidens: {item['evidence_state']}."
            )
        else:
            text = (
                f"{item['workout_type']}: {good}/{known} known responses were well absorbed "
                f"({poor} poor"
                + (f", {unknown} still unknown" if unknown else "")
                + f"). Evidence: {item['evidence_state']}."
            )
        statements.append(text)

    for item in profile.get("sequence_profiles", []):
        if item["known"] == 0:
            continue
        if language == "no":
            text = (
                f"{item['pattern_key']}: {item['good']} gode og {item['poor']} dårlige "
                f"av {item['known']} kjente eksponeringer"
                + (f", {item['unknown']} ukjente" if item["unknown"] else "")
                + f". Signal: {item['comparison_signal']}."
            )
        else:
            text = (
                f"{item['pattern_key']}: {item['good']} good and {item['poor']} poor "
                f"of {item['known']} known exposures"
                + (f", {item['unknown']} unknown" if item["unknown"] else "")
                + f". Signal: {item['comparison_signal']}."
            )
        statements.append(text)

    if not statements:
        statements.append(
            "For lite komplett responsdata til en personlig responsprofil ennå."
            if language == "no"
            else "Not enough complete response data for a personal response profile yet."
        )
    return statements[:max_items]
