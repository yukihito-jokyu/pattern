"""score のテスト。事実と採点役の判定から指標を計算し、課題ごと・ホールドアウトに分けることを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import catalog, collect, execute, fsops, layout, prepare, score
from forge_kit.errors import InvalidFileError
from tests import support


class ScoreTest(unittest.TestCase):
    def test_every_catalog_metric_has_calculator(self) -> None:
        self.assertEqual(set(score.CALCULATORS), {metric.id for metric in catalog.METRICS})

    def test_delegation(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        scores = support.scored_slot(where, layout.make_slot("baseline", 1), stream="delegated", met=True)
        found = {item.id: item.value for item in scores.metrics}
        self.assertEqual(found["delegation"], 1.0)
        self.assertTrue(scores.all_must_met)
        where = support.approved_layout(self, support.orch_charter())
        scores = support.scored_slot(where, layout.make_slot("baseline", 1), stream="main-edit", met=True)
        self.assertEqual({item.id: item.value for item in scores.metrics}["delegation"], 0.0)
        self.assertFalse(scores.all_must_met)

    def test_holdout_is_separate(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        scores = support.scored_slot(where, layout.make_slot("final", 0))
        self.assertEqual([entry.task_id for entry in scores.metrics[0].by_task], ["T1"])
        self.assertEqual([entry.task_id for entry in scores.holdout_metrics[0].by_task], ["H1"])

    def test_missing_grade_asks_to_relaunch_grader(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        slot = layout.make_slot("baseline", 1)
        prepare.prepare(where, slot)
        execute.execute(where, slot, support.fake_launcher())
        collect.collect(where, slot, parallel=1)
        with self.assertRaises(InvalidFileError) as caught:
            score.score(where, slot)
        self.assertIn("採点役を、同じプロンプトでもう一度起動してください", caught.exception.message)

    def test_run_notes(self) -> None:
        where = support.baseline_scored(self)
        text = fsops.read_text(where.scores_md_path(layout.make_slot("baseline", 1)))
        self.assertIn("サブエージェントを起動しなかった", text)
        self.assertIn("拒否された操作: Bash", text)


if __name__ == "__main__":
    unittest.main()
