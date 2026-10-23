"""fsops のテスト。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import fsops


class FsopsTest(unittest.TestCase):
    def test_json_round_trips_with_japanese(self) -> None:
        path = support.build_repo(self) / "a" / "b.json"
        fsops.write_json(path, {"文": "日本語"})
        self.assertEqual(fsops.read_json(path), {"文": "日本語"})
        self.assertIn("日本語", fsops.read_text(path))

    def test_broken_json_is_a_problem_not_an_error(self) -> None:
        path = support.build_repo(self) / "x.json"
        fsops.write_text(path, "{")
        data, problems = fsops.read_json_problems(path)
        self.assertIsNone(data)
        self.assertTrue(problems[0].startswith("x.json は JSON として読めません"))

    def test_tree_sha_follows_content(self) -> None:
        root = support.build_repo(self)
        skill = root / support.SKILL_PATH
        before = fsops.compute_tree_sha(skill)
        fsops.write_text(skill / "SKILL.md", "変えた")
        self.assertNotEqual(before, fsops.compute_tree_sha(skill))

    def test_copy_repo_skips_tune_dir(self) -> None:
        root = support.build_repo(self)
        fsops.write_text(root / ".tune" / "x.txt", "作業場所")
        fsops.write_text(root / "node_modules" / "y.js", "依存")
        fsops.copy_repo(root, root / ".tune" / "copy")
        copied = fsops.list_files(root / ".tune" / "copy")
        self.assertIn(f"{support.SKILL_PATH}/SKILL.md", copied)
        self.assertFalse(any(name.startswith((".tune", "node_modules")) for name in copied))
