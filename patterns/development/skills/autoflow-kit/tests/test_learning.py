"""learning のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import deciding, fsops, handoff, learning, policy, trail, verifying
from autoflow_kit.errors import StageError
from autoflow_kit.layout import Layout
from tests import support

NOW = support.NOW


class LearningTest(unittest.TestCase):
    def committed(self) -> tuple[Layout, str]:
        where, run_id = support.risked(self)
        support.review_round(where, run_id, {"correctness": [support.finding()]})
        declined = {"finding_id": "R1-1", "status": "declined", "reason": "負の数は仕様の外", "locations": []}
        support.build(where, run_id, {"README.md": "x\n"}, resolutions=[declined])
        verifying.verify(where, run_id, NOW)
        support.review_round(where, run_id)
        handoff.handoff(where, run_id, NOW)
        deciding.decide(where, run_id, policy.H3, policy.APPROVE, "承認します", NOW)
        handoff.commit(where, run_id, NOW)
        return where, run_id

    def test_metrics(self) -> None:
        where, run_id = self.committed()
        text = learning.metrics(where)
        self.assertIn("| 最初の H3 で承認された割合 | 100% |", text)
        self.assertIn(f"| {run_id} | コミット | 1 | approve | 2 | 0 | 0 |", text)

    def test_incident_only_after_commit(self) -> None:
        where, run_id = support.started(self)
        with self.assertRaisesRegex(StageError, "コミットしていません"):
            learning.incident(where, run_id, "壊れた", NOW)

    def test_learn(self) -> None:
        where, run_id = self.committed()
        learning.incident(where, run_id, "multiply(-1, 2) が落ちた", NOW)
        self.assertEqual(support.events(where, run_id)[-1].kind, trail.INCIDENT)
        text = learning.learn(where)
        self.assertIn("| 境界の値 | 1 |", text)
        self.assertIn(f"- {run_id} R1-1: 負の数は仕様の外", text)
        self.assertIn(f"- {run_id}: multiply(-1, 2) が落ちた", text)
        self.assertIn("| インシデント | 1 |", learning.metrics(where))

    def test_broken_trail_is_warned(self) -> None:
        where, run_id = support.started(self)
        fsops.append_line(where.trail_path(run_id), "{")
        self.assertIn(f"WARN 実行 {run_id} の記録を読めないので飛ばす", learning.metrics(where))
