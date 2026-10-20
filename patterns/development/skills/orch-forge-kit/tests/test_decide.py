"""decide のテスト。採用ならバンドルを退避して候補に置き換え、不採用なら変えないことを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import analyze, bundle, compare, decide, fsops, layout, workspace
from forge_kit.errors import StageError
from tests import support


def compared(test: unittest.TestCase) -> layout.Layout:
    where = support.baseline_scored(test)
    analyze.analyze(where, 1)
    support.act_analyst(where, 1)
    analyze.propose(where, 1)
    support.scored_slot(where, layout.make_slot("candidate", 1), stream="delegated", met=True)
    compare.compare(where, 1)
    return where


class DecideTest(unittest.TestCase):
    def test_adopt(self) -> None:
        where = compared(self)
        before = bundle.digest(where.claude_dir, support.SKILL)
        decide.decide(where, 1, adopted=True, today=support.TODAY)
        skill_md = bundle.skill_dir(where.claude_dir, support.SKILL) / layout.SKILL_FILE
        self.assertIn(support.ANALYST_LINE, fsops.read_text(skill_md))
        self.assertEqual(bundle.digest(where.previous_dir(1), support.SKILL), before)
        model, _sha = workspace.approved_charter(where)
        self.assertEqual(workspace.progress(where, model).current_slot, layout.make_slot("candidate", 1))
        with self.assertRaises(StageError):
            decide.decide(where, 1, adopted=False, today=support.TODAY)

    def test_reject(self) -> None:
        where = compared(self)
        before = bundle.digest(where.claude_dir, support.SKILL)
        decide.decide(where, 1, adopted=False, today=support.TODAY)
        self.assertEqual(bundle.digest(where.claude_dir, support.SKILL), before)

    def test_needs_compare(self) -> None:
        where = support.baseline_scored(self)
        analyze.analyze(where, 1)
        support.act_analyst(where, 1)
        analyze.propose(where, 1)
        with self.assertRaises(StageError):
            decide.decide(where, 1, adopted=True, today=support.TODAY)


if __name__ == "__main__":
    unittest.main()
