"""proc のテスト。本物の git とシェルで確かめる（TEST-02）。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import fsops, proc


class ProcTest(unittest.TestCase):
    def test_changed_lists_new_and_modified_files(self) -> None:
        sandbox = support.build_repo(self)
        fsops.write_text(sandbox / "memo.txt", "前")
        proc.run_git_baseline(sandbox)
        fsops.write_text(sandbox / "memo.txt", "後")
        fsops.write_text(sandbox / "out" / "new.txt", "新")
        self.assertEqual(proc.run_git_changed(sandbox), ("memo.txt", "out/new.txt"))
        self.assertIn("+後", proc.run_git_diff(sandbox))

    def test_command_reports_exit_code_and_tail(self) -> None:
        result = proc.run_command("echo 失敗した; exit 3", support.build_repo(self), 10)
        self.assertEqual(result.code, 3)
        self.assertIn("失敗した", result.tail)

    def test_command_times_out(self) -> None:
        result = proc.run_command("sleep 5", support.build_repo(self), 1)
        self.assertEqual(result.code, proc.TIMEOUT_EXIT)
