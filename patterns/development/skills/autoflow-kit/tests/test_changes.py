"""changes のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import changes, fsops
from tests import support


class ChangesTest(unittest.TestCase):
    def test_snapshot_includes_untracked(self) -> None:
        where = support.make_repo(self)
        before = changes.snapshot(where.root)
        self.assertEqual(changes.snapshot(where.root), before)
        fsops.write_text(where.repo_path("new.py"), "x = 1\n")
        after = changes.snapshot(where.root)
        self.assertNotEqual(after, before)
        self.assertEqual(changes.changed_files(where.root, before, after), ("new.py",))

    def test_ignored_files_do_not_change_tree(self) -> None:
        where = support.make_repo(self)
        before = changes.snapshot(where.root)
        fsops.write_text(where.runs_dir / "20261021-143000" / "trail.jsonl", "{}\n")
        self.assertEqual(changes.snapshot(where.root), before)

    def test_stats_and_diff(self) -> None:
        where = support.make_repo(self)
        before = changes.snapshot(where.root)
        support.write_files(where, support.FEATURE_FILES)
        after = changes.snapshot(where.root)
        found = changes.stats(where.root, before, after)
        self.assertEqual([stat.path for stat in found], ["calc.py", "tests/test_calc.py"])
        self.assertEqual(changes.line_count(found), 7)
        self.assertIn("+def multiply", changes.diff_text(where.root, before, after))
        self.assertEqual(changes.branch(where.root), "main")
