"""targets（検査の対象のファイルを集める）のテスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gha_kit import targets
from tests.support import write


class DiscoverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in (
            ".github/workflows/ci.yml",
            ".github/workflows/deploy/prod.yaml",
            ".github/actions/setup/action.yml",
            ".github/actions/setup/helper.sh",
            ".github/scripts/build.sh",
            ".github/dependabot.yml",
        ):
            write(self.root, rel, "# x\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_finds_misplaced_files_in_subdirectories(self) -> None:
        found = targets.discover(self.root)

        self.assertEqual(found.workflows, (".github/workflows/ci.yml", ".github/workflows/deploy/prod.yaml"))
        self.assertEqual(found.actions, (".github/actions/setup/action.yml",))
        self.assertEqual(found.dependabot, (".github/dependabot.yml",))
        self.assertEqual(found.scripts, (".github/scripts/build.sh",))

    def test_selects_only_the_given_paths(self) -> None:
        chosen = targets.select(targets.discover(self.root), ["./.github/workflows/ci.yml"])

        self.assertEqual(chosen.all_files(), (".github/workflows/ci.yml",))


if __name__ == "__main__":
    unittest.main()
