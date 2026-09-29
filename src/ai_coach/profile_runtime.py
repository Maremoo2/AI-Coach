"""Flatten a Personal Response Profile into stable private-ledger table rows."""
from __future__ import annotations

import json

PROFILE_STATE_COLUMNS = [
    "snapshot_key",
    "as_of",
    "profile_version",
    "athlete_id",
    "current_experiences",
    "actual_coverage",
    "subjective_coverage",
    "recovery_coverage",
    "downstream_coverage",
    "summary_json",
    "created_at_utc",
]

DOSE_PROFILE_COLUMNS = [
    "snapshot_key",
    "scope",
    "profile_key",
    "workout_type",
    "sport",
    "lifetime_exposures",
    "current_56d_exposures",
    "recent_28d_exposures",
    "absorption_known",
    "good",
    "poor",
    "unknown",
    "good_rate_known",
    "weighted_good_rate_180d",
    "evidence_state",
    "confidence",
    "dose_signature_json",
]

SEQUENCE_PROFILE_COLUMNS = [
    "snapshot_key",
    "pattern_key",
    "current_56d_exposures",
    "recent_28d_exposures",
    "known",
    "good",
    "poor",
    "unknown",
    "poor_rate_known",
    "baseline_known",
    "baseline_poor_rate",
    "poor_rate_difference",
    "comparison_signal",
    "evidence_state",
    "confidence",
]

TOLERANCE_PROFILE_COLUMNS = [
    "snapshot_key",
    "week",
    "sessions",
    "duration_min_known_total",
    "sport_counts_json",
    "absorption_known",
    "good",
    "poor",
    "unknown",
    "well_observed_and_absorbed",
]

DECISION_PROFILE_COLUMNS = [
    "snapshot_key",
    "decision_key",
    "history_180d_decisions",
    "current_56d_decisions",
    "known_outcomes",
    "good_outcomes",
    "poor_outcomes",
    "unknown_outcomes",
    "good_rate_known",
    "evaluation_state",
]


def snapshot_key(profile):
    return f"profile:{profile['as_of']}:{profile['profile_version']}"


def flatten_profile(profile, summary=None, created_at_utc=None):
    key = snapshot_key(profile)
    quality = profile["data_quality"]
    summary = summary or []
    state = [[
        key,
        profile["as_of"],
        profile["profile_version"],
        profile["athlete_id"],
        quality.get("current_experiences"),
        quality.get("actual_coverage"),
        quality.get("subjective_coverage"),
        quality.get("recovery_coverage"),
        quality.get("downstream_coverage"),
        json.dumps(summary, ensure_ascii=False, separators=(",", ":")),
        created_at_utc or profile["as_of"],
    ]]

    dose = []
    for item in profile["dose_profiles"]:
        absorption = item["absorption"]
        dose.append([
            key,
            item["scope"],
            item["key"],
            item["workout_type"],
            item["sport"],
            item["lifetime_exposures"],
            item["current_56d_exposures"],
            item["recent_28d_exposures"],
            absorption["known"],
            absorption["good"],
            absorption["poor"],
            absorption["unknown"],
            absorption["good_rate_known"],
            absorption["weighted_good_rate_180d"],
            item["evidence_state"],
            item["confidence"],
            json.dumps(item.get("dose_signature"), sort_keys=True, separators=(",", ":"))
            if item.get("dose_signature") is not None else None,
        ])

    sequence = []
    for item in profile["sequence_profiles"]:
        sequence.append([
            key,
            item["pattern_key"],
            item["current_56d_exposures"],
            item["recent_28d_exposures"],
            item["known"],
            item["good"],
            item["poor"],
            item["unknown"],
            item["poor_rate_known"],
            item["baseline_known"],
            item["baseline_poor_rate"],
            item["poor_rate_difference"],
            item["comparison_signal"],
            item["evidence_state"],
            item["confidence"],
        ])

    tolerance = []
    for item in profile["weekly_tolerance"]:
        tolerance.append([
            key,
            item["week"],
            item["sessions"],
            item["duration_min_known_total"],
            json.dumps(item["sport_counts"], sort_keys=True, separators=(",", ":")),
            item["absorption_known"],
            item["good"],
            item["poor"],
            item["unknown"],
            item["well_observed_and_absorbed"],
        ])

    decisions = []
    for item in profile["decision_profiles"]:
        decisions.append([
            key,
            item["decision_key"],
            item["history_180d_decisions"],
            item["current_56d_decisions"],
            item["known_outcomes"],
            item["good_outcomes"],
            item["poor_outcomes"],
            item["unknown_outcomes"],
            item["good_rate_known"],
            item["evaluation_state"],
        ])

    return {
        "ProfileState": state,
        "DoseProfile": dose,
        "SequenceProfile": sequence,
        "ToleranceProfile": tolerance,
        "DecisionProfile": decisions,
    }
