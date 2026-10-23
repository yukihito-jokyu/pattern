"""audit のテスト。監査とデータの直しを確かめる（ADR 0009）。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import layout, plan, workspace


class AuditTest(unittest.TestCase):
    def test_audit_prompt_lists_failing_cases(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        out = support.run_ok(self, root, "audit", "--round", "1")
        self.assertIn("不合格のケース 2 件（c01, c03）", out)
        evidence = (where.round_dir(1) / layout.AUDIT_EVIDENCE_FILE).read_text(encoding="utf-8")
        self.assertIn(f'"prompt": "{support.build_prompt("c01")}"', evidence)
        self.assertNotIn("c04", evidence)

    def test_invalid_audit_is_removed_and_prompt_updated(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        support.run_ok(self, root, "audit", "--round", "1")
        support.write_audit(where, 1, [support.build_finding(1, "c01")])
        code, _out, err = support.run_cli(root, "audit-check", "--round", "1")
        self.assertEqual(code, 1)
        self.assertIn("ケース c03 の指摘がありません", err)
        self.assertFalse((where.round_dir(1) / layout.AUDIT_FILE).exists())
        self.assertIn(
            "ケース c03 の指摘がありません", (where.round_dir(1) / layout.AUDIT_PROMPT_FILE).read_text(encoding="utf-8")
        )

    def test_data_fix_applies_chosen_fix_and_reapproves(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        support.run_ok(self, root, "audit", "--round", "1")
        fixed = support.build_case("c01", expected=support.WRONG)
        findings = [support.build_finding(1, "c01", "expected", {"case": fixed}), support.build_finding(2, "c03")]
        support.write_audit(where, 1, findings)
        support.run_ok(self, root, "audit-check", "--round", "1")
        code, _out, err = support.run_cli(root, "data-fix", "--round", "1", "--apply", "F2")
        self.assertEqual(code, 1)
        self.assertIn("F2 は直しの提案ではありません", err)
        out = support.run_ok(self, root, "data-fix", "--round", "1", "--apply", "F1")
        self.assertIn("適用 1 件", out)
        approved = workspace.load_approved(where)
        self.assertEqual(approved.approval.history[-1].kind, "data-fix")
        self.assertFalse(approved.approval.history[-1].test_changed)
        refs = workspace.list_runs(approved, "v0", (plan.TRAIN,))
        states = {ref.case_id: workspace.compute_run_state(where, approved, ref) for ref in refs}
        self.assertEqual(states["c01"], workspace.UNPREPARED)
        self.assertIn("今の版 v0 の評価", support.find_line(support.list_status(root), "段階: "))

    def test_no_failures_skips_final_audit(self) -> None:
        root = support.build_approved_repo(self)
        support.run_until_learn(self, root)
        support.run_round(self, root, 1)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TEST,))
        support.run_eval(self, root, "v1", (plan.TEST,))
        out = support.run_ok(self, root, "audit", "--final")
        self.assertIn("監査を省きました", out)
