"""evidence のテスト。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import evidence, layout, plan, workspace


class EvidenceTest(unittest.TestCase):
    def test_case_shows_checks_runs_and_response(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_eval(self, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
        approved = workspace.load_approved(where)
        case = approved.find_case("c01")
        assert case is not None
        results = workspace.load_results(where, approved, "v0", (plan.TRAIN,))
        text = evidence.render_case(where, approved.model, case, plan.TRAIN, [r for r in results if r.case_id == "c01"])
        self.assertIn("## ケース c01（分割 train、グループ memo、合格 0 / 1）", text)
        self.assertIn("| K1 | equals | must | response |", text)
        self.assertIn(support.WRONG, text)
        self.assertIn(support.ANSWER, text)
