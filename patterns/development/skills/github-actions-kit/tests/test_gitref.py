"""gitref（基準の版のファイルを読む）のテスト。一時ディレクトリに git のリポジトリを作る。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gha_kit import gitref
from gha_kit.errors import UsageError
from tests.support import git, write


class GitrefTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "--quiet")
        write(self.root, ".github/workflows/ci.yml", "# 古い版\n")
        write(self.root, ".github/logo.png", "png")
        git(self.root, "add", ".")
        git(self.root, "commit", "--quiet", "-m", "init")
        write(self.root, ".github/workflows/ci.yml", "# 新しい版\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_shows_the_file_at_the_given_ref(self) -> None:
        self.assertEqual(gitref.show(self.root, "HEAD", ".github/workflows/ci.yml"), "# 古い版\n")

    def test_returns_none_for_a_file_missing_at_the_ref(self) -> None:
        self.assertIsNone(gitref.show(self.root, "HEAD", ".github/workflows/new.yml"))

    def test_lists_only_text_files_under_the_base(self) -> None:
        self.assertEqual(gitref.tracked(self.root, "HEAD", ".github"), [".github/workflows/ci.yml"])

    def test_rejects_an_unknown_ref(self) -> None:
        with self.assertRaises(UsageError):
            gitref.tracked(self.root, "no-such-ref", ".github")


if __name__ == "__main__":
    unittest.main()
