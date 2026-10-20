"""proc のテスト。検査コマンド、git の基準と差分、実行役の起動と打ち切り、コピーの置き場を確かめる。"""

from __future__ import annotations

import os
import sys
import unittest

from forge_kit import fsops, proc
from forge_kit.errors import CommandError
from tests import support


class ProcTest(unittest.TestCase):
    def test_shell_passes_ci(self) -> None:
        root = support.make_repo(self)
        previous = os.environ.pop("CI", None)
        try:
            result = proc.shell("python3 -c \"import os; print(os.environ['CI'])\"", root, 30)
            self.assertEqual((result.code, result.output.strip()), (0, "1"))
            os.environ["CI"] = "true"
            result = proc.shell("python3 -c \"import os; print(os.environ['CI'])\"", root, 30)
            self.assertEqual((result.code, result.output.strip()), (0, "true"))
        finally:
            if previous is None:
                os.environ.pop("CI", None)
            else:
                os.environ["CI"] = previous
        self.assertEqual(proc.shell("sleep 5", root, 1).code, proc.TIMEOUT_EXIT)

    def test_git_changed_and_patch(self) -> None:
        root = support.make_repo(self)
        proc.git_baseline(root)
        fsops.write_text(root / support.IMPL_FILE, support.IMPL_CODE)
        self.assertEqual(proc.git_changed(root), (support.IMPL_FILE,))
        self.assertIn("+def remove", proc.git_patch(root))

    def test_launch(self) -> None:
        root = support.make_repo(self)
        launched = proc.launch([sys.executable, "-c", "print('ok')"], root, 30)
        self.assertEqual((launched.exit_code, launched.timed_out, launched.stdout.strip()), (0, False, "ok"))
        stopped = proc.launch([sys.executable, "-c", "import time; time.sleep(10)"], root, 1)
        self.assertTrue(stopped.timed_out)
        with self.assertRaises(CommandError):
            proc.launch(["orch-forge-no-such-command"], root, 5)

    def test_copies_root_is_outside_repository(self) -> None:
        root = support.make_repo(self)
        self.assertNotIn(root, proc.copies_root(root).parents)
        self.assertNotEqual(proc.copies_root(root), proc.copies_root(root.parent))

    def test_launch_many_keeps_order(self) -> None:
        self.assertEqual(proc.launch_many([3, 1, 2], 2, lambda value: value * 10), [30, 10, 20])


if __name__ == "__main__":
    unittest.main()
