"""sandbox のテスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h2_kit import fsops, sandbox, skilltree


class SandboxTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name)
        fsops.write_text(self.source / "memo.md", "古い\n")
        fsops.write_text(self.source / "gone.md", "消える\n")
        fsops.write_text(self.source / ".claude" / "skills" / "other" / "SKILL.md", "別のスキル")
        fsops.write_text(self.source / ".git" / "HEAD", "ref")
        self.place = sandbox.write_sandbox(self.source, skilltree.build_tree({"SKILL.md": "s"}), "sample")
        self.addCleanup(sandbox.remove_sandbox, self.place)

    def test_sandbox_has_only_the_candidate_skill(self) -> None:
        self.assertEqual(fsops.list_files(self.place / ".claude"), ["skills/sample/SKILL.md"])
        self.assertFalse((self.place / ".git").exists())
        self.assertTrue((self.place / "memo.md").is_file())

    def test_changes_compare_with_the_material(self) -> None:
        fsops.write_text(self.place / "memo.md", "新しい\n")
        fsops.write_text(self.place / "answer.md", "答え\n")
        fsops.remove_file(self.place / "gone.md")
        changes = {change.path: change for change in sandbox.read_changes(self.source, self.place)}
        self.assertEqual(sorted(changes), ["answer.md", "gone.md", "memo.md"])
        self.assertEqual(changes["answer.md"].body, "答え\n")
        self.assertIn("+新しい", changes["memo.md"].body)
        self.assertEqual(changes["gone.md"].kind, skilltree.REMOVED)
