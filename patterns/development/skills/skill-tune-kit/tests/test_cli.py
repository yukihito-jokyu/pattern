"""cli のテスト。サブコマンドごとに test_command_<名前> を置く（TEST-03）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests import support
from tune_kit import layout, plan

NEXT = f"次: {layout.CLI} status --target {support.TARGET}"


class CliTest(unittest.TestCase):
    def assert_fails(self, root: Path, message: str, *args: str) -> None:
        code, out, err = support.run_cli(root, *args)
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("エラー: "), err)
        self.assertIn(message, err)

    def test_command_init(self) -> None:
        out = support.run_ok(self, support.build_repo(self), "init", "--skill", support.SKILL_PATH)
        self.assertIn("作成: .tune/targets/sample/plan.json", out)
        self.assertTrue(out.rstrip().endswith(NEXT))

    def test_command_check_plan(self) -> None:
        root = support.build_repo(self)
        support.write_dataset(root, support.build_plan(), support.build_cases(2))
        self.assert_fails(root, "ケースは 3 件以上にしてください", "check-plan")

    def test_command_approve(self) -> None:
        root = support.build_repo(self)
        support.write_dataset(root, support.build_plan(), support.build_cases(10))
        self.assert_fails(root, "check-plan の後に計画が変わりました", "approve")

    def test_command_status(self) -> None:
        out = support.run_ok(self, support.build_repo(self), "status")
        self.assertNotIn(NEXT, out)

    def test_command_eval_prepare(self) -> None:
        root = support.build_approved_repo(self)
        self.assert_fails(root, "--splits は train, val, test", "eval-prepare", "--version", "v0", "--splits", "dev")
        self.assert_fails(root, "版 v9 がありません", "eval-prepare", "--version", "v9", "--splits", "train")
        out = support.run_ok(self, root, "eval-prepare", "--version", "v0", "--splits", "train,val")
        self.assertIn("準備: 8 件", out)

    def test_command_eval_collect(self) -> None:
        root = support.build_approved_repo(self)
        support.run_ok(self, root, "eval-prepare", "--version", "v0", "--splits", "train")
        out = support.run_ok(self, root, "eval-collect", "--version", "v0", "--splits", "train")
        self.assertIn("出力の無い実行が 6 件あります", out)

    def test_command_eval_score(self) -> None:
        root = support.build_approved_repo(self)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN,))
        out = support.run_ok(self, root, "eval-score", "--version", "v0", "--splits", "train")
        self.assertIn("6 / 6 件が記録済み", out)

    def test_command_audit(self) -> None:
        root = support.build_approved_repo(self)
        self.assert_fails(root, "--round <番号> か --final", "audit")
        self.assert_fails(root, "--round <番号> か --final", "audit", "--round", "1", "--final")
        self.assert_fails(root, "評価が終わっていません", "audit", "--round", "1")

    def test_command_audit_check(self) -> None:
        root = support.build_approved_repo(self)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        support.run_ok(self, root, "audit", "--round", "1")
        self.assert_fails(root, "audit.json がありません", "audit-check", "--round", "1")

    def test_command_data_fix(self) -> None:
        root = support.build_approved_repo(self)
        self.assert_fails(root, "--apply '<指摘の ID をカンマ区切り>' か --none", "data-fix", "--round", "1")

    def test_command_learn(self) -> None:
        root = support.build_approved_repo(self)
        support.run_until_learn(self, root)
        self.assert_fails(root, "学習は準備済みです", "learn", "--round", "1")

    def test_command_learn_check(self) -> None:
        root = support.build_approved_repo(self)
        support.run_until_learn(self, root)
        self.assert_fails(root, "proposal.json がありません", "learn-check", "--round", "1")

    def test_command_decide(self) -> None:
        root = support.build_approved_repo(self)
        support.run_until_learn(self, root)
        self.assert_fails(root, "提案が検査されていません", "decide", "--round", "1")

    def test_command_report(self) -> None:
        root = support.build_approved_repo(self)
        self.assert_fails(root, "報告は、最後の評価と最後の監査が終わってから書きます", "report")

    def test_command_apply(self) -> None:
        root = support.build_approved_repo(self)
        self.assert_fails(root, "報告は、最後の評価と最後の監査が終わってから書きます", "apply")

    def test_bad_arguments_exit_with_two(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            support.run_cli(support.build_repo(self), "no-such-command")
        self.assertEqual(raised.exception.code, 2)
