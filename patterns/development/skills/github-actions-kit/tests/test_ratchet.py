"""ratchet（基準の版より指摘が増えたか）のテスト。一時ディレクトリの git のリポジトリと FakeRunner を使う。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gha_kit import ratchet
from tests.support import FakeRunner, git, write

BUILD = ".github/workflows/build.yml"
ONE_JOB = "# 目的\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
TWO_JOBS = ONE_JOB + "  test:\n    runs-on: ubuntu-latest\n"


class CompareTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".gha").mkdir()
        git(self.root, "init", "--quiet")
        write(self.root, BUILD, ONE_JOB)
        git(self.root, "add", ".")
        git(self.root, "commit", "--quiet", "-m", "init")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_allows_existing_findings_that_did_not_increase(self) -> None:
        self.assertEqual(ratchet.compare(self.root, "HEAD", [BUILD], FakeRunner()), [])

    def test_reports_a_rule_whose_findings_increased(self) -> None:
        write(self.root, BUILD, TWO_JOBS)

        increases = ratchet.compare(self.root, "HEAD", [BUILD], FakeRunner())

        runner_rule = [i for i in increases if i.rule == "NAM-06"]
        self.assertEqual([(i.path, i.before, i.after) for i in runner_rule], [(BUILD, 1, 2)])


if __name__ == "__main__":
    unittest.main()
