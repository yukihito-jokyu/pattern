"""cli の出力の形と終了コードのテスト（KIT-04）。外部ツールは FakeRunner に置き換える。"""

from __future__ import annotations

import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from gha_kit import cli
from tests.support import FakeRunner, git, write

FINDING_LINE = re.compile(r"^[A-Z]+-\d{2} \S+:\d+ \S")


class MainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv, root=self.root, runner=FakeRunner())
        return code, out.getvalue(), err.getvalue()

    def test_prints_one_line_per_finding_and_the_count_and_exits_1(self) -> None:
        write(self.root, ".github/workflows/build.yml", "# 目的\njobs:\n  build:\n    runs-on: ubuntu-latest\n")

        code, out, _ = self.run_cli("check", ".github/workflows/build.yml")

        *findings, summary = out.splitlines()
        self.assertEqual(code, 1)
        self.assertTrue(findings)
        self.assertTrue(all(FINDING_LINE.match(line) for line in findings), findings)
        self.assertEqual(summary, f"gha check: 指摘 {len(findings)} 件")

    def test_exits_0_without_findings(self) -> None:
        self.assertEqual(self.run_cli("check")[:2], (0, "gha check: 指摘 0 件\n"))

    def test_compares_a_renamed_workflow_with_its_old_path(self) -> None:
        git(self.root, "init", "--quiet")
        write(
            self.root, ".github/workflows/test.yml", "on:\n  push:\njobs:\n  test:\n    steps:\n      - run: npm test\n"
        )
        git(self.root, "add", ".")
        git(self.root, "commit", "--quiet", "-m", "init")
        write(
            self.root, ".github/workflows/ci.yml", "on:\n  push:\njobs:\n  test:\n    steps:\n      - run: make test\n"
        )

        code, out, _ = self.run_cli(
            "intent", ".github/workflows/ci.yml", "--compare-ref", "HEAD", "--from", ".github/workflows/test.yml"
        )

        self.assertEqual(code, 0)
        self.assertIn("| コマンド | `npm test` | |", out)

    def test_exits_2_on_a_usage_error(self) -> None:
        code, _, err = self.run_cli("pin")

        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("エラー: "))


if __name__ == "__main__":
    unittest.main()
