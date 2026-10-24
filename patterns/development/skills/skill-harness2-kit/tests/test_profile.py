"""profile のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import profile
from tests import support


class ProfileTest(unittest.TestCase):
    def test_default_with_texts_is_valid(self) -> None:
        found, problems = profile.parse_profile(support.build_profile())
        self.assertEqual(problems, [])
        assert found is not None
        self.assertEqual((found.k, found.modes, found.obs_trunc), (1, ("parallel",), 50000))

    def test_obs_trunc_below_ten_thousand_is_rejected(self) -> None:
        self.assertIsNone(profile.parse_profile(support.build_profile(obs_trunc=9999))[0])
        self.assertIsNotNone(profile.parse_profile(support.build_profile(obs_trunc=10000))[0])

    def test_other_schema_version_is_rejected(self) -> None:
        found, problems = profile.parse_profile(support.build_profile(schema_version=2))
        self.assertIsNone(found)
        self.assertTrue(any("schema_version" in problem for problem in problems))

    def test_measurement_words_in_method_texts_are_rejected(self) -> None:
        for field in ("work", "inv_levers", "dom_levers", "yardstick", "selection_checks"):
            with self.subTest(field=field):
                self.assertIsNone(profile.parse_profile(support.build_profile(**{field: "採点で満点を取る"}))[0])

    def test_problems_are_all_collected(self) -> None:
        data = support.build_profile(k=9, modes=["wide"], skill="../outside", width=0)
        found, problems = profile.parse_profile(data)
        self.assertIsNone(found)
        self.assertEqual(len(problems), 4)

    def test_modes_follow_the_fixed_order(self) -> None:
        found, _ = profile.parse_profile(support.build_profile(modes=["sequential", "parallel"]))
        assert found is not None
        self.assertEqual(found.modes, ("parallel", "sequential"))
