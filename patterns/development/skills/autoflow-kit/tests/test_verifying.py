"""verifying のテスト。検査コマンドは見本のリポジトリで本当に実行する。"""

from __future__ import annotations

import unittest

from autoflow_kit import fsops, policy, profile, trail, verifying, workspace
from tests import support

NOW = support.NOW
TEST_CLAMP = {
    "tests/test_clamp.py": (
        "import unittest\n\nimport calc\n\n\nclass ClampTest(unittest.TestCase):\n"
        "    def test_high(self) -> None:\n        self.assertEqual(calc.clamp(11, 0, 10), 10)\n"
    )
}
FIXED = {"calc.py": support.CALC_FEATURE.replace("return max(low, value)", "return min(high, max(low, value))")}


class VerifyingTest(unittest.TestCase):
    def test_baseline(self) -> None:
        where, run_id = support.started(self)
        text = verifying.verify(where, run_id, NOW)
        self.assertIn("期待どおり", text)
        evidence = workspace.load_evidence(where, run_id, 1)
        self.assertEqual(
            (evidence.mode, evidence.passed, [item.id for item in evidence.results]), (trail.BASELINE, True, ["unit"])
        )
        self.assertIn("$ python3 -B -m unittest", fsops.read_text(where.repo_path(evidence.results[0].log)))
        self.assertEqual(support.next_step(where, run_id).step, trail.PLAN)

    def test_baseline_failure_stops(self) -> None:
        settings = profile.make_profile((profile.Command("unit", "exit 1", 10),), ())
        where, run_id = support.started(self, settings)
        verifying.verify(where, run_id, NOW)
        self.assertEqual(support.next_step(where, run_id).step, trail.STOPPED)

    def test_check_runs_criteria(self) -> None:
        where, run_id = support.verified(self)
        evidence = workspace.load_evidence(where, run_id, 2)
        self.assertEqual([item.id for item in evidence.results], ["unit", "criterion-c1"])
        self.assertTrue(evidence.passed)
        self.assertEqual(support.next_step(where, run_id).step, trail.RISK)

    def test_check_that_changes_tree_fails(self) -> None:
        settings = profile.make_profile((profile.Command("unit", "echo x > made.txt", 10),), ())
        where, run_id = support.started(self, settings)
        verifying.verify(where, run_id, NOW)
        evidence = workspace.load_evidence(where, run_id, 1)
        self.assertFalse(evidence.passed)
        self.assertEqual(evidence.results[-1].id, verifying.TREE_CHECK)

    def test_repro_must_fail_first(self) -> None:
        where, run_id = support.planned(self, support.fix_plan())
        support.build(where, run_id, TEST_CLAMP)
        verifying.verify(where, run_id, NOW)
        self.assertTrue(workspace.load_evidence(where, run_id, 2).passed)
        self.assertEqual(support.next_step(where, run_id).reason, trail.FIRST)
        support.build(where, run_id, FIXED)
        verifying.verify(where, run_id, NOW)
        evidence = workspace.load_evidence(where, run_id, 3)
        self.assertEqual(([item.id for item in evidence.results], evidence.passed), (["unit", "repro"], True))

    def test_fix_attempts_escalate(self) -> None:
        where, run_id = support.planned(self)
        broken = {"calc.py": "def multiply(a: int, b: int) -> int:\n    return a + b\n"}
        for _attempt in range(profile.DEFAULT_LIMITS.fix_attempts):
            support.build(where, run_id, broken)
            verifying.verify(where, run_id, NOW)
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.gate), (trail.DECIDE, policy.H2))
