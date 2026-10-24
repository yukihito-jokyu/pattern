"""adoption のテスト。確認の符号と、承認したスキルからの変化（PROC-07、OPS-04）。"""

from __future__ import annotations

import unittest

from h2_kit import adoption, execution, layout, skilltree, workspace
from h2_kit.errors import StageError
from tests import support


class AdoptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where = support.build_approved(self)
        execution.run(self.where, None, lambda _line: None)
        summary = workspace.load_summary(self.where.task_place(1, support.TASK_ID), layout.PARALLEL)
        assert summary is not None
        self.summary = summary
        self.code = skilltree.build_confirm_code(summary.chosen_fingerprint)

    def test_wrong_code_changes_nothing(self) -> None:
        before = support.read_skill(self.where)
        with self.assertRaises(StageError):
            adoption.adopt(self.where, support.TASK_ID, layout.PARALLEL, "000000000000", support.TODAY)
        self.assertEqual(support.read_skill(self.where), before)

    def test_right_code_writes_the_chosen_tree_once(self) -> None:
        adoption.adopt(self.where, support.TASK_ID, layout.PARALLEL, self.code, support.TODAY)
        self.assertEqual(skilltree.compute_fingerprint(support.read_skill(self.where)), self.summary.chosen_fingerprint)
        adopted = workspace.load_adoptions(self.where)
        self.assertEqual([(item.round, item.label) for item in adopted], [(1, "agg1")])
        with self.assertRaises(StageError):
            adoption.adopt(self.where, support.TASK_ID, layout.PARALLEL, self.code, support.TODAY)

    def test_unfinished_mode_is_refused(self) -> None:
        with self.assertRaises(StageError):
            adoption.adopt(self.where, support.TASK_ID, layout.SEQUENTIAL, self.code, support.TODAY)
