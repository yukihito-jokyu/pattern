"""fsops のテスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h2_kit import fsops
from h2_kit.errors import InvalidFileError


class FsopsTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_write_creates_parents_and_reads_back(self) -> None:
        fsops.write_json(self.root / "a" / "b.json", {"k": "値"})
        self.assertEqual(fsops.read_json(self.root / "a" / "b.json"), {"k": "値"})

    def test_broken_json_is_an_invalid_file(self) -> None:
        fsops.write_text(self.root / "x.json", "{")
        with self.assertRaises(InvalidFileError):
            fsops.read_json(self.root / "x.json")

    def test_copy_tree_skips_names_at_any_depth(self) -> None:
        fsops.write_text(self.root / "src" / "keep.md", "k")
        fsops.write_text(self.root / "src" / "d" / ".git" / "x", "g")
        fsops.write_text(self.root / "src" / "__pycache__" / "y.pyc", "c")
        fsops.copy_tree(self.root / "src", self.root / "dst", skip=frozenset({".git"}))
        self.assertEqual(fsops.list_files(self.root / "dst"), ["keep.md"])

    def test_tree_hash_follows_contents(self) -> None:
        fsops.write_text(self.root / "t" / "a.md", "1")
        before = fsops.compute_tree_sha256(self.root / "t")
        fsops.write_text(self.root / "t" / "a.md", "2")
        self.assertNotEqual(before, fsops.compute_tree_sha256(self.root / "t"))
        fsops.remove_tree(self.root / "t")
        self.assertEqual(fsops.list_files(self.root / "t"), [])
