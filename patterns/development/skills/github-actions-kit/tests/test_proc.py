"""proc（外部コマンドの起動）のテスト。実行中の Python を外部コマンドとして使う。"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

from gha_kit import proc
from gha_kit.errors import ToolError


class RunTest(unittest.TestCase):
    def test_returns_the_exit_code_and_output(self) -> None:
        result = proc.run([sys.executable, "-c", "print('out'); raise SystemExit(3)"], Path.cwd())

        self.assertEqual((result.code, result.stdout), (3, "out\n"))

    def test_puts_the_extra_path_first(self) -> None:
        code = "import os; print(os.environ['PATH'].split(os.pathsep)[0])"

        result = proc.run([sys.executable, "-c", code], Path.cwd(), extra_path=Path("/kit/bin"))

        self.assertEqual(result.stdout.strip(), os.path.normpath("/kit/bin"))

    def test_raises_a_tool_error_for_a_missing_command(self) -> None:
        with self.assertRaises(ToolError):
            proc.run(["gha-kit-no-such-command"], Path.cwd())


if __name__ == "__main__":
    unittest.main()
