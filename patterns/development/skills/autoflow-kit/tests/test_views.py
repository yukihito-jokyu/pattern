"""views のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import contracts, policy, profile, views
from tests import support


def kept(tag: str = policy.IMPORTANT) -> contracts.Kept:
    finding = contracts.parse_findings(
        {"findings": [support.finding(other_locations=["calc.py:20"])]}, policy.REVIEW.categories, []
    )[0]
    return contracts.Kept("R1-1", tag, 2, 3, ("correctness",), finding)


class ViewsTest(unittest.TestCase):
    def test_plan_shows_repro_only_for_fix(self) -> None:
        plan = contracts.parse_plan(support.fix_plan(), [kind.name for kind in policy.KINDS], [])
        settings = profile.make_profile((support.UNIT,), ())
        text = views.render_plan(plan, policy.compose(plan, settings))
        self.assertIn("## 再現と原因", text)
        feature = contracts.parse_plan(support.feature_plan(), [kind.name for kind in policy.KINDS], [])
        self.assertNotIn("## 再現と原因", views.render_plan(feature, policy.compose(feature, settings)))

    def test_profile_lists_commands(self) -> None:
        text = views.render_profile(profile.make_profile((support.UNIT,), ()))
        self.assertIn(f"`{support.UNIT.run}`", text)
        self.assertIn("`.claude/**`", text)

    def test_finding_line(self) -> None:
        self.assertEqual(
            views.finding_line(kept()),
            "R1-1 [Important] 負の数の扱いが決まっていない — `calc.py:14`、種類 境界の値"
            "（同じ種類の他の箇所: calc.py:20）",
        )

    def test_review(self) -> None:
        result = contracts.ReviewResult(2, "b" * 40, "a" * 40, "standard", (kept(policy.NIT),), ("R2-2",))
        text = views.render_review(result)
        self.assertIn("# レビュー ラウンド 2", text)
        self.assertIn("| R1-1 | Nit |", text)
        self.assertIn("票で落ちた候補: R2-2", text)

    def test_gate(self) -> None:
        text = views.render_gate(policy.H2, ("h2_too_many_failures",), ("続いた検査の失敗: 3 回",))
        self.assertIn("# H2 行き詰まり", text)
        for option in policy.gate_of(policy.H2).options:
            self.assertIn(f"`{option.name}`", text)

    def test_kinds_and_tiers(self) -> None:
        for kind in policy.KINDS:
            self.assertIn(f"`{kind.name}`", views.render_kinds())
        for tier in policy.TIERS:
            self.assertIn(f"`{tier.name}`", views.render_tiers())
