import unittest

from ai_coach.profile import build_personal_response_profile, render_profile_summary
from ai_coach.profile_runtime import (
    DOSE_PROFILE_COLUMNS,
    PROFILE_STATE_COLUMNS,
    flatten_profile,
)
from tests.unit.test_profile import AS_OF, row


class ProfileRuntimeTests(unittest.TestCase):
    def test_flatten_profile_has_stable_sheet_contract(self):
        profile = build_personal_response_profile([row(1)], AS_OF)
        summary = render_profile_summary(profile, "no")
        flat = flatten_profile(profile, summary, AS_OF)
        self.assertEqual(len(flat["ProfileState"][0]), len(PROFILE_STATE_COLUMNS))
        self.assertTrue(flat["ProfileState"][0][0].startswith("profile:"))
        self.assertEqual(len(flat["DoseProfile"][0]), len(DOSE_PROFILE_COLUMNS))
