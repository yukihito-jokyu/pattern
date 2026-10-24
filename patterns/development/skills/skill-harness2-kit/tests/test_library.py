"""library のテスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h2_kit import contracts, fsops, layout, library, skilltree
from h2_kit.errors import LeakError

TREE = skilltree.build_tree({"SKILL.md": "a\n", "references/x.md": "x\n"})
LESSON = contracts.Experience("書き忘れ", "確かめを足す", "inv1", "low")


class LibraryTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_entry_keeps_the_whole_tree_and_rebuilds_the_index(self) -> None:
        library.write_entry(self.root / "lib", TREE, library.Entry("t1", "agg1", "理由", "verdict: helped", LESSON))
        self.assertEqual(
            fsops.list_files(self.root / "lib" / "t1" / layout.ENTRY_SKILL_DIR), ["SKILL.md", "references/x.md"]
        )
        index = fsops.read_text(self.root / "lib" / layout.INDEX_FILE)
        self.assertIn("## `t1/`", index)
        self.assertIn("cue: 書き忘れ", index)

    def test_later_tasks_see_only_earlier_entries(self) -> None:
        for task_id in ("t1", "t2"):
            library.write_entry(self.root / "lib", TREE, library.Entry(task_id, "agg1", "", "", LESSON))
        copied = library.copy_earlier(self.root / "lib", ["t1"], self.root / "view")
        self.assertEqual(fsops.list_dirs(self.root / "view"), ["t1"])
        self.assertEqual(copied, self.root / "view")
        self.assertIsNone(library.copy_earlier(self.root / "lib", [], self.root / "none"))

    def test_marked_tree_is_refused(self) -> None:
        marked = skilltree.build_tree({"SKILL.md": '"pass_rate"'})
        with self.assertRaises(LeakError):
            library.write_entry(self.root / "lib", marked, library.Entry("t1", "agg1", "", "", LESSON))
