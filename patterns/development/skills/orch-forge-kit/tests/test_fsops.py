"""fsops のテスト。リポジトリの写し（除く名前とリンク）と、ファイルの一覧・指紋・JSON の読み込みを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import fsops
from forge_kit.errors import KitError
from tests import support


class FsopsTest(unittest.TestCase):
    def test_copy_repo(self) -> None:
        root = support.make_repo(self)
        fsops.write_text(root / "node_modules/lib.js", "x\n")
        fsops.write_text(root / ".forge/work/x.txt", "x\n")
        fsops.write_text(root / "dist/out.txt", "x\n")
        copy = root.parent / "copy"
        fsops.copy_repo(root, copy, ["/dist"], ["node_modules"])
        self.assertTrue((copy / "check.py").is_file())
        self.assertTrue((copy / "node_modules").is_symlink())
        self.assertFalse((copy / ".forge").exists())
        self.assertFalse((copy / "dist").exists())

    def test_list_files_and_fingerprint(self) -> None:
        root = support.make_repo(self)
        files = fsops.list_files(root, [], [])
        self.assertIn("inventory/stock.py", files)
        before = fsops.fingerprint(root, [], [])
        fsops.write_text(root / "inventory/stock.py", "変えた\n")
        self.assertNotEqual(before, fsops.fingerprint(root, [], []))

    def test_read_json(self) -> None:
        root = support.make_repo(self)
        fsops.write_text(root / "bad.json", "{")
        with self.assertRaises(KitError):
            fsops.read_json(root / "bad.json")
        fsops.write_json(root / "good.json", {"キー": [1]})
        self.assertEqual(fsops.read_json(root / "good.json"), {"キー": [1]})


if __name__ == "__main__":
    unittest.main()
