"""workspace のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import workspace
from h2_kit.errors import InvalidFileError, StageError
from tests import support


class WorkspaceTest(unittest.TestCase):
    def test_tasks_are_read_in_name_order(self) -> None:
        where = support.build_where(support.build_repo(self))
        for task_id in ("b", "a"):
            support.write_task(where, task_id)
        self.assertEqual([task.task_id for task in workspace.load_tasks(where)], ["a", "b"])

    def test_task_order_is_sorted_or_seeded(self) -> None:
        ids = ["c", "a", "b", "d", "e"]
        self.assertEqual(workspace.compute_task_order(ids, None, "x"), ["a", "b", "c", "d", "e"])
        seeded = workspace.compute_task_order(ids, 7, "x")
        self.assertEqual(seeded, workspace.compute_task_order(ids, 7, "x"))
        self.assertEqual(sorted(seeded), ["a", "b", "c", "d", "e"])

    def test_approved_stops_when_the_profile_changes(self) -> None:
        where = support.build_approved(self)
        self.assertEqual(workspace.load_approved(where).round, 1)
        support.write_profile(where, k=2)
        with self.assertRaises(StageError):
            workspace.load_approved(where)

    def test_checks_are_validated(self) -> None:
        where = support.build_where(support.build_repo(self))
        support.write_task(where)
        support.write_checks(where, "t1", [{"name": "a", "command": "true", "timeout_sec": 5}])
        self.assertEqual(workspace.load_checks(where.checks_path("t1"))[0].name, "a")
        support.write_checks(where, "t1", [{"name": "a", "command": "", "timeout_sec": 5}])
        with self.assertRaises(InvalidFileError):
            workspace.load_checks(where.checks_path("t1"))

    def test_progress_counts_task_and_mode_pairs(self) -> None:
        where = support.build_approved(self, ("t1", "t2"), modes=["parallel", "sequential"])
        progress = workspace.compute_progress(where, workspace.load_approved(where))
        self.assertEqual((progress.total, progress.finished), (4, 0))
        self.assertEqual(progress.pending[0], "t1/parallel")
