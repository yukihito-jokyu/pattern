"""proc のテスト。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from h2_kit import proc
from h2_kit.errors import CommandError

HERE = Path(__file__).resolve().parent


class ProcTest(unittest.TestCase):
    def test_returns_code_and_output(self) -> None:
        done = proc.run_command(
            [sys.executable, "-c", "import sys; print(sys.stdin.read()); sys.exit(3)"], HERE, "入力", 30
        )
        self.assertEqual((done.code, done.stdout.strip(), done.timed_out), (3, "入力", False))

    def test_timeout_is_a_result_not_an_error(self) -> None:
        done = proc.run_command([sys.executable, "-c", "import time; time.sleep(5)"], HERE, "", 1)
        self.assertTrue(done.timed_out)

    def test_missing_command_is_a_command_error(self) -> None:
        with self.assertRaises(CommandError):
            proc.run_command([str(HERE / "no-such-command")], HERE, "", 5)
