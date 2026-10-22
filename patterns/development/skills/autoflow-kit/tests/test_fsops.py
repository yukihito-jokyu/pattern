"""fsops のテスト。"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from autoflow_kit import fsops
from autoflow_kit.errors import KitError


class FsopsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    def test_write_and_read_json(self) -> None:
        path = self.base / "a" / "b.json"
        fsops.write_json(path, {"名前": [1, 2]})
        self.assertEqual(fsops.read_json(path), {"名前": [1, 2]})
        self.assertIn("名前", fsops.read_text(path))

    def test_missing_and_broken_files(self) -> None:
        with self.assertRaisesRegex(KitError, "がありません"):
            fsops.read_text(self.base / "none.txt")
        fsops.write_text(self.base / "bad.json", "{")
        with self.assertRaisesRegex(KitError, "JSON として読めません"):
            fsops.read_json(self.base / "bad.json")

    def test_lines(self) -> None:
        path = self.base / "trail.jsonl"
        fsops.append_line(path, '{"a": 1}')
        fsops.append_line(path, '{"a": 2}\n')
        self.assertEqual(fsops.read_text(path), '{"a": 1}\n{"a": 2}\n')
        self.assertEqual(fsops.read_lines(path), ({"a": 1}, {"a": 2}))
        fsops.append_line(path, "x")
        with self.assertRaisesRegex(KitError, "3 行目"):
            fsops.read_lines(path)

    def test_copy_file(self) -> None:
        fsops.write_text(self.base / "a.txt", "中身")
        fsops.copy_file(self.base / "a.txt", self.base / "sub" / "b.txt")
        self.assertEqual(fsops.read_text(self.base / "sub" / "b.txt"), "中身")
