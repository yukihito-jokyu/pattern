"""skilltree のテスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h2_kit import fsops, skilltree

SKILL = "---\nname: s\ndescription: 一行目\n  二行目\n---\n\n# 本文\n"


class SkilltreeTest(unittest.TestCase):
    def test_surface_is_the_skill_parts(self) -> None:
        for path in ("SKILL.md", "references/a.md", "scripts/check.py", "scripts/run.sh", "assets/t.json"):
            with self.subTest(path=path):
                self.assertTrue(skilltree.is_on_surface(path))
        for path in ("notes.txt", "references/deep/a.md", "scripts/x.js", "hooks/h.py"):
            with self.subTest(path=path):
                self.assertFalse(skilltree.is_on_surface(path))

    def test_read_tree_rejects_files_off_the_surface(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fsops.write_text(root / "SKILL.md", SKILL)
            fsops.write_text(root / "notes.txt", "外")
            tree, rejected = skilltree.read_tree(root)
        self.assertEqual(tree.paths, ("SKILL.md",))
        self.assertEqual(rejected, ["notes.txt"])

    def test_frontmatter_joins_a_folded_description(self) -> None:
        found = skilltree.parse_frontmatter(SKILL)
        assert found is not None
        self.assertEqual(found.description, "一行目 二行目")
        self.assertEqual(found.entries, ("name: s",))
        self.assertIsNone(skilltree.parse_frontmatter("# 本文だけ"))

    def test_changes_and_diff(self) -> None:
        before = skilltree.build_tree({"SKILL.md": "a\n", "references/old.md": "o\n"})
        after = skilltree.build_tree({"SKILL.md": "b\n", "references/new.md": "n\n"})
        kinds = [(change.kind, change.path) for change in skilltree.compute_changes(before, after)]
        self.assertEqual(
            kinds, [("modified", "SKILL.md"), ("added", "references/new.md"), ("removed", "references/old.md")]
        )
        diff = skilltree.compute_diff(before, after)
        self.assertIn("--- /dev/null\n+++ b/references/new.md", diff)
        self.assertEqual(skilltree.compute_diff(before, before), "")

    def test_diversity_and_confirm_code(self) -> None:
        same = skilltree.build_tree({"SKILL.md": "a\nb\n"})
        other = skilltree.build_tree({"SKILL.md": "a\nc\n"})
        self.assertEqual(skilltree.compute_diversity([same, same]), 1.0)
        self.assertEqual(skilltree.compute_diversity([same, other]), round(1 / 3, 4))
        self.assertEqual(skilltree.compute_diversity([same]), 1.0)
        self.assertEqual(len(skilltree.build_confirm_code(skilltree.compute_fingerprint(same))), 12)
