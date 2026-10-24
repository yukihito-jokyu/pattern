"""results のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import execution, layout, results, skilltree, workspace
from h2_kit.errors import StageError
from tests import support


class ResultsTest(unittest.TestCase):
    def test_show_needs_an_approval(self) -> None:
        with self.assertRaises(StageError):
            results.show(support.build_where(support.build_repo(self)), None, None)

    def test_show_gives_the_diff_and_the_adopt_command(self) -> None:
        where = support.build_approved(self)
        self.assertIn("表示できる結果がありません", results.show(where, None, None))
        execution.run(where, None, lambda _line: None)
        summary = workspace.load_summary(where.task_place(1, support.TASK_ID), layout.PARALLEL)
        assert summary is not None
        code = skilltree.build_confirm_code(summary.chosen_fingerprint)
        text = results.show(where, support.TASK_ID, layout.PARALLEL)
        self.assertIn(f"adopt sample --task t1 --mode parallel --confirm {code}`", text)
        self.assertIn("+++ b/references/", text)
        self.assertIn("| 実行 | 4 | R = 4k = 4 |", text)
        self.assertIn("k = 1 のため選択役を起動していない", text)
