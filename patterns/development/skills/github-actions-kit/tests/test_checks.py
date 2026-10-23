"""checks（構造の検査と外部ツールのまとめ）のテスト。外部ツールは FakeRunner に置き換える。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gha_kit import checks
from tests.support import FakeRunner, write

LATEST = "# 目的\njobs:\n  build:\n    runs-on: ubuntu-latest\n"


class RunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root, ".github/workflows/build.yml", LATEST)
        write(self.root, ".github/workflows/lint.yml", LATEST)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_reports_only_findings_of_the_given_paths(self) -> None:
        findings = checks.run(self.root, [".github/workflows/build.yml"], runner=FakeRunner())

        self.assertEqual({f.path for f in findings}, {".github/workflows/build.yml"})
        self.assertIn("NAM-06", {f.rule for f in findings})

    def test_reports_a_missing_dependabot_only_when_checking_everything(self) -> None:
        everything = checks.run(self.root, runner=FakeRunner())
        one = checks.run(self.root, [".github/workflows/build.yml"], runner=FakeRunner())

        self.assertIn((".github/dependabot.yml", "PROC-03"), {(f.path, f.rule) for f in everything})
        self.assertNotIn("PROC-03", {f.rule for f in one})


if __name__ == "__main__":
    unittest.main()
