"""judging のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import execution, fsops, judging, layout, planning
from tests import support


class JudgingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where = support.build_where(support.build_repo(self))
        support.write_profile(self.where)
        support.write_task(self.where)
        check = {"name": "答え", "command": "test -f {task_dir}/answer.md", "timeout_sec": 10}
        support.write_checks(self.where, support.TASK_ID, [check])
        planning.check(self.where)
        planning.approve(self.where, support.TODAY)

    def test_runs_checks_on_base_and_chosen(self) -> None:
        execution.run(self.where, None, lambda _line: None)
        text = judging.judge(self.where, None)
        self.assertIn("| t1 | base1 | 答え | 落ちた |", text)
        self.assertIn("| t1 | agg1 | 答え | 通った |", text)
        judged = fsops.read_text(self.where.task_place(1, support.TASK_ID).judged_path)
        self.assertIn('"h2_judged": true', judged)

    def test_run_without_output_is_still_judged(self) -> None:
        execution.run(self.where, None, lambda _line: None)
        place = self.where.task_place(1, support.TASK_ID)
        fsops.remove_tree(place.rollout_dir(layout.BASE, "base1") / layout.OUTPUT_DIR)
        fsops.remove_file(place.rollout_dir(layout.BASE, "base1") / layout.REPLY_FILE)
        self.assertIn("| t1 | base1 | 答え | 落ちた |", judging.judge(self.where, support.TASK_ID))

    def test_nothing_to_judge_before_run(self) -> None:
        self.assertIn("動かした検査はありません", judging.judge(self.where, None))
