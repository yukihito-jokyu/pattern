"""cli のテスト。サブコマンドごとに test_command_<名前> を置く（TEST-03）。"""

from __future__ import annotations

import unittest

from h2_kit import layout, skilltree, workspace
from tests import support


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = support.build_repo(self)
        self.where = support.build_where(self.root)

    def prepare(self) -> None:
        support.write_profile(self.where)
        support.write_task(self.where)

    def approve(self) -> None:
        self.prepare()
        support.run_cli(self.root, "check", support.TARGET)
        support.run_cli(self.root, "approve", support.TARGET)

    def run_round(self) -> str:
        self.approve()
        support.run_cli(self.root, "run", support.TARGET)
        summary = workspace.load_summary(self.where.task_place(1, support.TASK_ID), layout.PARALLEL)
        assert summary is not None
        return skilltree.build_confirm_code(summary.chosen_fingerprint)

    def test_command_init(self) -> None:
        code, out, _ = support.run_cli(self.root, "init", support.TARGET, "--skill", support.SKILL_PATH)
        self.assertEqual(code, 0)
        self.assertIn("次:", out)
        self.assertTrue(self.where.profile_path.is_file())

    def test_command_check(self) -> None:
        self.prepare()
        code, out, _ = support.run_cli(self.root, "check", support.TARGET)
        self.assertEqual(code, 0)
        self.assertIn("# 改善の計画（sample）", out)

    def test_command_approve(self) -> None:
        self.prepare()
        support.run_cli(self.root, "check", support.TARGET)
        code, out, _ = support.run_cli(self.root, "approve", support.TARGET)
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("ラウンド 1 を承認しました"))

    def test_command_status(self) -> None:
        code, out, _ = support.run_cli(self.root, "status", support.TARGET)
        self.assertEqual(code, 0)
        self.assertIn("段階: 準備", out)

    def test_command_run(self) -> None:
        self.approve()
        code, out, _ = support.run_cli(self.root, "run", support.TARGET)
        self.assertEqual(code, 0)
        self.assertIn("t1: 基準の実行 1 回", out)
        self.assertIn("| t1 | parallel | agg1 |", out)

    def test_command_show(self) -> None:
        confirm = self.run_round()
        code, out, _ = support.run_cli(self.root, "show", support.TARGET, "--task", support.TASK_ID)
        self.assertEqual(code, 0)
        self.assertIn(f"確認の符号: {confirm}", out)

    def test_command_adopt(self) -> None:
        confirm = self.run_round()
        argv = ["adopt", support.TARGET, "--task", support.TASK_ID, "--mode", layout.PARALLEL, "--confirm", confirm]
        code, out, _ = support.run_cli(self.root, *argv)
        self.assertEqual(code, 0)
        self.assertIn("書き込んだ", out)

    def test_command_judge(self) -> None:
        self.prepare()
        check = {"name": "返答", "command": "test -s {reply_file}", "timeout_sec": 10}
        support.write_checks(self.where, support.TASK_ID, [check])
        support.run_cli(self.root, "check", support.TARGET)
        support.run_cli(self.root, "approve", support.TARGET)
        support.run_cli(self.root, "run", support.TARGET)
        code, out, _ = support.run_cli(self.root, "judge", support.TARGET)
        self.assertEqual(code, 0)
        self.assertIn("| t1 | agg1 | 返答 | 通った |", out)

    def test_kit_error_goes_to_stderr_with_code_1(self) -> None:
        code, out, err = support.run_cli(self.root, "run", support.TARGET)
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("エラー: "))

    def test_bad_target_name_is_an_error(self) -> None:
        self.assertEqual(support.run_cli(self.root, "status", "Bad")[0], 1)
