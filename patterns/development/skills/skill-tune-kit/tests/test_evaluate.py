"""evaluate のテスト。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import fsops, layout, plan, workspace


class EvaluateTest(unittest.TestCase):
    def test_command_runs_in_the_sandbox(self) -> None:
        check = support.build_check("K1", "command", run="test -f memo.txt && test ! -e .tune")
        root = support.build_repo(self)
        where = support.write_dataset(root, support.build_plan(checks=[check]), support.build_cases(10))
        for index in range(1, 11):
            fsops.write_text(where.input_dir(f"c{index:02d}") / "memo.txt", "入力")
        support.run_approve(self, root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        summary = workspace.load_summary(where, workspace.load_approved(where), "v0", plan.VAL)
        self.assertEqual(summary.pass_rate, 1)

    def test_grader_prompt_only_when_judged(self) -> None:
        checks = [
            support.build_check("K1", "equals"),
            support.build_check("Q1", "judge", plan.SHOULD, criterion="理由を書く"),
        ]
        root = support.build_approved_repo(self, support.build_plan(checks=checks))
        where = support.build_where(root)
        args = ("--version", "v0", "--splits", "train")
        support.run_ok(self, root, "eval-prepare", *args)
        support.write_responses(where, "v0", (plan.TRAIN,), support.build_answer)
        support.run_ok(self, root, "eval-collect", *args)
        approved = workspace.load_approved(where)
        refs = workspace.list_runs(approved, "v0", (plan.TRAIN,))
        prompt = (where.run_dir(refs[0].key) / layout.GRADER_PROMPT_FILE).read_text(encoding="utf-8")
        self.assertIn("| Q1 | should | 理由を書く | 使わない |", prompt)
        self.assertNotIn("v0", prompt)

    def test_invalid_grade_is_removed(self) -> None:
        checks = [support.build_check("K1", "equals"), support.build_check("Q1", "judge", criterion="理由を書く")]
        root = support.build_approved_repo(self, support.build_plan(checks=checks))
        where = support.build_where(root)
        args = ("--version", "v0", "--splits", "train")
        support.run_ok(self, root, "eval-prepare", *args)
        support.write_responses(where, "v0", (plan.TRAIN,), support.build_answer)
        support.run_ok(self, root, "eval-collect", *args)
        ref = workspace.list_runs(workspace.load_approved(where), "v0", (plan.TRAIN,))[0]
        fsops.write_json(where.run_dir(ref.key) / layout.GRADE_FILE, {"grades": []})
        code, _out, err = support.run_cli(root, "eval-score", *args)
        self.assertEqual(code, 1)
        self.assertIn("grade.json に検査 Q1 の判定がありません", err)
        self.assertFalse((where.run_dir(ref.key) / layout.GRADE_FILE).exists())

    def test_scored_run_dir_is_removed(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN,))
        ref = workspace.list_runs(workspace.load_approved(where), "v0", (plan.TRAIN,))[0]
        self.assertFalse(where.run_dir(ref.key).exists())
        self.assertTrue((where.result_dir("v0", ref.case_id, 1) / layout.RESPONSE_FILE).is_file())
