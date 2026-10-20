"""compare のテスト。推奨の決定表と、今のバンドルと候補の採点の比較を確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import analyze, compare, contracts, layout, workspace
from tests import support


def row(metric_id: str, priority: str, change: str) -> contracts.CompareRow:
    return contracts.CompareRow(metric_id, metric_id, priority, "higher", 1.0, 0.5, 0.5, change, False)


class CompareTest(unittest.TestCase):
    def test_recommend(self) -> None:
        self.assertEqual(compare.recommend([row("a", "must", "worse"), row("b", "should", "better")])[0], "reject")
        self.assertEqual(compare.recommend([row("a", "should", "better"), row("b", "must", "same")])[0], "adopt")
        self.assertEqual(compare.recommend([row("a", "must", "same")])[0], "reject")

    def test_compare(self) -> None:
        where = support.baseline_scored(self)
        analyze.analyze(where, 1)
        support.act_analyst(where, 1)
        analyze.propose(where, 1)
        support.scored_slot(where, layout.make_slot("candidate", 1), stream="delegated", met=True)
        out = compare.compare(where, 1)
        self.assertIn("推奨: 採用", out)
        comparison = workspace.load_comparison(where, 1)
        delegation = next(item for item in comparison.rows if item.id == "delegation")
        self.assertEqual((delegation.baseline, delegation.candidate, delegation.change), (0.0, 1.0, "better"))


if __name__ == "__main__":
    unittest.main()
