"""status のテスト。行の書き出し（OPS-01）と、テスト用を使う時期（STATE-03）を確かめる。"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests import support
from tune_kit import layout, plan, status


class StatusTest(unittest.TestCase):
    def assert_line_kinds(self, root: Path) -> list[str]:
        lines = support.list_status(root)
        for line in lines:
            self.assertTrue(line.startswith(status.LINE_KINDS), line)
        return lines

    def test_no_plan_points_to_init(self) -> None:
        lines = self.assert_line_kinds(support.build_repo(self))
        self.assertEqual(lines[0], "段階: 計画が無い")

    def test_broken_plan_lists_problems(self) -> None:
        root = support.build_repo(self)
        support.write_dataset(root, support.build_plan(), support.build_cases(2))
        lines = self.assert_line_kinds(root)
        self.assertTrue(support.find_line(lines, "問題: ").startswith("問題: "))

    def test_every_stage_uses_line_kinds(self) -> None:
        root = support.build_repo(self)
        support.write_dataset(root, support.build_plan(), support.build_cases(10))
        self.assert_line_kinds(root)
        support.run_ok(self, root, "check-plan")
        self.assertTrue(support.find_line(self.assert_line_kinds(root), "承認なら: "))
        support.run_ok(self, root, "approve")
        support.run_ok(self, root, "eval-prepare", "--version", "v0", "--splits", "train,val")
        lines = self.assert_line_kinds(root)
        self.assertEqual(len([line for line in lines if line.startswith("job tune-executor ")]), 4)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        support.run_ok(self, root, "audit", "--round", "1")
        self.assertTrue(support.find_line(self.assert_line_kinds(root), "job tune-auditor audit-1 "))
        support.write_audit(
            support.build_where(root), 1, [support.build_finding(1, "c01"), support.build_finding(2, "c03")]
        )
        support.run_ok(self, root, "audit-check", "--round", "1")
        support.run_ok(self, root, "data-fix", "--round", "1", "--none")
        support.run_ok(self, root, "learn", "--round", "1")
        self.assertTrue(support.find_line(self.assert_line_kinds(root), "job tune-learner learn-1 "))
        support.run_round(self, root, 1)
        support.run_final(self, root, "v1")
        support.run_ok(self, root, "report")
        self.assertTrue(support.find_line(self.assert_line_kinds(root), "適用するなら: "))
        support.run_ok(self, root, "apply")
        self.assertIn("段階: 完了", self.assert_line_kinds(root))

    def test_test_split_waits_for_the_loop(self) -> None:
        root = support.build_approved_repo(self)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        lines = support.list_status(root)
        self.assertNotIn("--splits test", "\n".join(lines))
        code, _out, err = support.run_cli(root, "eval-prepare", "--version", "v0", "--splits", "test")
        self.assertEqual(code, 1)
        self.assertIn("テスト用は、ラウンドが終わった後の最後の評価でだけ使います", err)

    def test_fix_proposals_ask_the_human(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        support.run_ok(self, root, "audit", "--round", "1")
        fixed = support.build_case("c01", expected=support.WRONG)
        support.write_audit(
            where, 1, [support.build_finding(1, "c01", "expected", {"case": fixed}), support.build_finding(2, "c03")]
        )
        support.run_ok(self, root, "audit-check", "--round", "1")
        lines = support.list_status(root)
        self.assertIn("AskUserQuestion", support.find_line(lines, "次: "))
        self.assertIn("--apply '<適用する指摘の ID をカンマ区切り>'", support.find_line(lines, "適用するなら: "))
