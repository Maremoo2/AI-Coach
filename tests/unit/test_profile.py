import unittest

from ai_coach.profile import absorption_label, build_personal_response_profile, recency_weight, render_profile_summary

AS_OF = "2026-10-20T12:00:00Z"


def row(i, workout_type="RUN_THRESHOLD", days_ago=5, absorption="GOOD", execution="A", quality=0.9, decision=None):
    day = 20 - days_ago
    started = f"2026-10-{day:02d}T10:00:00Z"
    recovery = None
    downstream = None
    if absorption == "GOOD":
        recovery = {"recovery_24h": "NORMAL", "recovery_48h": None}
        downstream = {"next_session_quality": "GOOD"}
    elif absorption == "POOR":
        recovery = {"recovery_24h": "POOR", "recovery_48h": None}
        downstream = {"next_session_quality": None}
    sport = "RUN" if workout_type.startswith("RUN") else ("BIKE" if workout_type.startswith("BIKE") else "MIXED")
    return {
        "experience_id": f"e{i}",
        "athlete_id": "a",
        "planned": {
            "workout_type": workout_type,
            "sport": sport,
            "dose_signature": {"workout_type": workout_type, "duration_min": 60, "intervals": 3, "work_min": 10, "intensity": "HARD"},
        },
        "actual": {"started_at": started, "duration_min": 60, "execution": execution, "quality": quality},
        "subjective_response": None,
        "recovery_response": recovery,
        "life_context": None,
        "downstream_outcome": downstream,
        "benchmark_state": None,
        "coach_decision": decision,
        "outcome_label": absorption,
        "workout_type": workout_type,
        "sport": sport,
        "started_at": started,
    }


class AbsorptionTests(unittest.TestCase):
    def test_good_execution_without_recovery_is_unknown_absorption(self):
        self.assertEqual(absorption_label(row(1, absorption="UNKNOWN")), "UNKNOWN")

    def test_poor_recovery_is_poor_absorption(self):
        self.assertEqual(absorption_label(row(1, absorption="POOR")), "POOR")


class RecencyTests(unittest.TestCase):
    def test_recency_weights_decay(self):
        self.assertEqual(recency_weight(10), 1.0)
        self.assertEqual(recency_weight(40), 0.75)
        self.assertEqual(recency_weight(70), 0.50)
        self.assertEqual(recency_weight(120), 0.25)
        self.assertEqual(recency_weight(200), 0.0)


class ProfileTests(unittest.TestCase):
    def test_single_outcome_stays_observation(self):
        profile = build_personal_response_profile([row(1)], AS_OF)
        item = next(x for x in profile["dose_profiles"] if x["scope"] == "WORKOUT_TYPE")
        self.assertEqual(item["evidence_state"], "OBSERVATION")
        self.assertFalse(item["can_write_plan"])

    def test_four_consistent_outcomes_become_candidate_not_established(self):
        rows = [row(i, days_ago=i + 1) for i in range(4)]
        profile = build_personal_response_profile(rows, AS_OF)
        item = next(x for x in profile["dose_profiles"] if x["scope"] == "WORKOUT_TYPE")
        self.assertEqual(item["evidence_state"], "CANDIDATE_PATTERN")
        self.assertEqual(item["absorption"]["good"], 4)

    def test_six_consistent_recent_outcomes_can_become_established(self):
        rows = [row(i, days_ago=i + 1) for i in range(6)]
        profile = build_personal_response_profile(rows, AS_OF)
        item = next(x for x in profile["dose_profiles"] if x["scope"] == "WORKOUT_TYPE")
        self.assertEqual(item["evidence_state"], "ESTABLISHED_PERSONAL_RULE")

    def test_mixed_pattern_is_not_promoted(self):
        rows = [
            row(1, days_ago=1, absorption="GOOD"),
            row(2, days_ago=2, absorption="POOR"),
            row(3, days_ago=3, absorption="GOOD"),
            row(4, days_ago=4, absorption="POOR"),
        ]
        profile = build_personal_response_profile(rows, AS_OF)
        item = next(x for x in profile["dose_profiles"] if x["scope"] == "WORKOUT_TYPE")
        self.assertEqual(item["evidence_state"], "MIXED_PATTERN")

    def test_unknowns_reduce_coverage_and_are_not_counted_as_good(self):
        rows = [row(1, absorption="GOOD"), row(2, absorption="UNKNOWN")]
        profile = build_personal_response_profile(rows, AS_OF)
        item = next(x for x in profile["dose_profiles"] if x["scope"] == "WORKOUT_TYPE")
        self.assertEqual(item["absorption"]["known"], 1)
        self.assertEqual(item["absorption"]["unknown"], 1)
        self.assertLess(item["confidence"], 0.5)

    def test_decision_profile_evaluates_only_known_outcomes(self):
        rows = [
            row(1, decision={"state": "KEEP"}, absorption="GOOD"),
            row(2, decision={"state": "KEEP"}, absorption="POOR"),
            row(3, decision={"state": "KEEP"}, absorption="UNKNOWN"),
        ]
        profile = build_personal_response_profile(rows, AS_OF)
        decision = profile["decision_profiles"][0]
        self.assertEqual(decision["known_outcomes"], 2)
        self.assertEqual(decision["unknown_outcomes"], 1)
        self.assertEqual(decision["evaluation_state"], "INSUFFICIENT_EVIDENCE")

    def test_norwegian_summary_uses_known_denominator(self):
        rows = [row(1, absorption="GOOD"), row(2, absorption="GOOD"), row(3, absorption="POOR"), row(4, absorption="UNKNOWN")]
        profile = build_personal_response_profile(rows, AS_OF)
        summary = render_profile_summary(profile, "no")
        self.assertIn("2 av 3 kjente responser", summary[0])


class SequenceProfileTests(unittest.TestCase):
    def test_sequence_keeps_good_and_poor_and_requires_baseline(self):
        rows = [
            row(1, "CROSSFIT", days_ago=8, absorption="GOOD"),
            row(2, "BIKE_THRESHOLD", days_ago=7, absorption="POOR"),
            row(3, "CROSSFIT", days_ago=6, absorption="GOOD"),
            row(4, "BIKE_THRESHOLD", days_ago=5, absorption="POOR"),
            row(5, "CROSSFIT", days_ago=4, absorption="GOOD"),
            row(6, "BIKE_THRESHOLD", days_ago=3, absorption="POOR"),
        ]
        for idx, item in enumerate(rows):
            item["started_at"] = f"2026-10-{10+idx:02d}T10:00:00Z"
            item["actual"]["started_at"] = item["started_at"]
        profile = build_personal_response_profile(rows, AS_OF)
        seq = next(x for x in profile["sequence_profiles"] if x["pattern_key"].startswith("CROSSFIT->BIKE_THRESHOLD"))
        self.assertEqual(seq["poor"], 3)
        self.assertEqual(seq["comparison_signal"], "INSUFFICIENT_BASELINE")
