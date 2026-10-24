"""execution のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import execution, fsops, layout, workspace
from h2_kit.errors import StageError
from tests import support


class ExecutionTest(unittest.TestCase):
    def test_run_writes_summaries_and_resumes_without_new_calls(self) -> None:
        log = support.build_repo(self) / "log.jsonl"
        where = support.build_approved(self, ("t1", "t2"), log=log)
        lines: list[str] = []
        execution.run(where, None, lines.append)
        calls = len(support.read_log(log))
        summary = workspace.load_summary(where.task_place(1, "t1"), layout.PARALLEL)
        assert summary is not None
        self.assertEqual(summary.chosen_label, "agg1")
        self.assertEqual(len(summary.rollouts), 4)
        self.assertTrue(summary.lesson)
        self.assertIn("t1/parallel: 選ばれた候補 agg1", lines)
        execution.run(where, None, lines.append)
        self.assertEqual(len(support.read_log(log)), calls)
        self.assertIn("t2: 終わっています", lines)

    def test_later_tasks_read_the_library_of_earlier_tasks(self) -> None:
        where = support.build_approved(self, ("t1", "t2"))
        execution.run(where, None, lambda _line: None)
        later = where.task_place(1, "t2").session_dir(layout.PARALLEL, "inv1", 1) / layout.CONTEXT_DIR
        earlier = where.task_place(1, "t1").session_dir(layout.PARALLEL, "inv1", 1) / layout.CONTEXT_DIR
        self.assertIn("library/t1/EXPERIENCE.md", fsops.list_files(later))
        self.assertFalse((earlier / layout.LIBRARY_DIR).exists())

    def test_run_stops_when_the_skill_changed(self) -> None:
        where = support.build_approved(self)
        fsops.write_text(where.skill_dir(support.SKILL_PATH) / "SKILL.md", "変えた")
        with self.assertRaises(StageError):
            execution.run(where, None, lambda _line: None)

    def test_unknown_task_is_refused(self) -> None:
        with self.assertRaises(StageError):
            execution.run(support.build_approved(self), "none", lambda _line: None)
