"""risking のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import deciding, fsops, policy, risking, trail, verifying
from autoflow_kit.errors import StageError
from tests import support

NOW = support.NOW


class RiskingTest(unittest.TestCase):
    def test_risk_new_writes_diff_and_rule_tier(self) -> None:
        where, run_id = support.verified(self)
        text = risking.risk_new(where, run_id, NOW)
        self.assertIn("規則の段: medium", text)
        self.assertIn("+def multiply", fsops.read_text(where.risk_diff_path(run_id, 1)))
        self.assertIn("規則に当たらない通常の変更", fsops.read_text(where.risk_prompt_path(run_id, 1)))

    def test_ai_cannot_lower_tier(self) -> None:
        where, run_id = support.risked(self, policy.LOW)
        event = support.events(where, run_id)[-1]
        self.assertEqual((event.kind, event.tier, event.human_required), (trail.RISKED, policy.MEDIUM, False))

    def test_ai_can_raise_tier(self) -> None:
        where, run_id = support.risked(self, policy.HIGH)
        self.assertEqual(support.events(where, run_id)[-1].tier, policy.HIGH)

    def test_human_paths_require_human(self) -> None:
        where, run_id = support.planned(self, support.feature_plan(scope=["calc.py", "REVIEW.md"]))
        self.assertEqual(support.next_step(where, run_id).gate, policy.H1)
        deciding.decide(where, run_id, policy.H1, policy.PROCEED, support.ANSWER, NOW)
        support.build(where, run_id, {**support.FEATURE_FILES, "REVIEW.md": "境界の値を確かめる\n"})
        verifying.verify(where, run_id, NOW)
        risking.risk_new(where, run_id, NOW)
        support.act_risk(where, run_id)
        risking.risk_check(where, run_id, NOW)
        event = support.events(where, run_id)[-1]
        self.assertTrue(event.human_required)

    def test_check_needs_same_tree(self) -> None:
        where, run_id = support.verified(self)
        risking.risk_new(where, run_id, NOW)
        support.act_risk(where, run_id)
        support.write_files(where, {"calc.py": "x = 1\n"})
        with self.assertRaisesRegex(StageError, "作業ツリーが変わりました"):
            risking.risk_check(where, run_id, NOW)
