"""deciding のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import deciding, policy, trail
from autoflow_kit.errors import StageError
from tests import support

NOW = support.NOW


class DecidingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where, self.run_id = support.planned(self, support.feature_plan(dependencies_to_add=["numpy"]))

    def test_wrong_gate_or_choice(self) -> None:
        with self.assertRaisesRegex(StageError, "今の関所は H1"):
            deciding.decide(self.where, self.run_id, policy.H3, policy.APPROVE, support.ANSWER, NOW)
        with self.assertRaisesRegex(StageError, "proceed, replan, abort"):
            deciding.decide(self.where, self.run_id, policy.H1, policy.APPROVE, support.ANSWER, NOW)

    def test_empty_answer_is_not_a_decision(self) -> None:
        with self.assertRaisesRegex(StageError, "承認にも選択にもしない"):
            deciding.decide(self.where, self.run_id, policy.H1, policy.PROCEED, "  ", NOW)
        self.assertEqual(support.next_step(self.where, self.run_id).step, trail.DECIDE)

    def test_records_answer_tree_and_who(self) -> None:
        deciding.decide(self.where, self.run_id, policy.H1, policy.PROCEED, support.ANSWER, NOW)
        event = support.events(self.where, self.run_id)[-1]
        self.assertEqual(
            (event.gate, event.choice, event.answer, event.who),
            (policy.H1, policy.PROCEED, support.ANSWER, support.EMAIL),
        )
        self.assertEqual(event.tree, support.events(self.where, self.run_id)[0].tree)
        self.assertEqual(support.next_step(self.where, self.run_id).step, trail.BUILD)

    def test_abort_stops(self) -> None:
        deciding.decide(self.where, self.run_id, policy.H1, policy.ABORT, "やめます", NOW)
        self.assertEqual(support.next_step(self.where, self.run_id).step, trail.STOPPED)
        with self.assertRaises(StageError):
            deciding.decide(self.where, self.run_id, policy.H1, policy.PROCEED, support.ANSWER, NOW)
