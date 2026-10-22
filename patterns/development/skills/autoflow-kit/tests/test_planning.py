"""planning のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import deciding, fsops, planning, policy, trail, verifying, workspace
from autoflow_kit.errors import InvalidFileError, StageError
from tests import support

NOW = support.NOW


class PlanningTest(unittest.TestCase):
    def test_plan_new_writes_prompt(self) -> None:
        where, run_id = support.started(self)
        verifying.verify(where, run_id, NOW)
        planning.plan_new(where, run_id, NOW)
        prompt = fsops.read_text(where.plan_prompt_path(run_id, 1))
        self.assertIn(where.relative(where.task_path(run_id)), prompt)
        self.assertIn(where.relative(where.plan_path(run_id, 1)), prompt)
        self.assertEqual(support.next_step(where, run_id).prompted, trail.PLANNER)

    def test_check_needs_prompt(self) -> None:
        where, run_id = support.started(self)
        verifying.verify(where, run_id, NOW)
        with self.assertRaisesRegex(StageError, "plan-new"):
            planning.plan_check(where, run_id, NOW)

    def test_check_writes_flow(self) -> None:
        where, run_id = support.planned(self)
        flow = workspace.load_flow(where, run_id, 1)
        self.assertEqual((flow.kind, flow.h1_reasons), ("feature", ()))
        self.assertIn("# 計画", fsops.read_text(where.plan_md_path(run_id, 1)))
        self.assertEqual(support.next_step(where, run_id).reason, trail.FIRST)

    def test_invalid_plan(self) -> None:
        where, run_id = support.started(self)
        verifying.verify(where, run_id, NOW)
        planning.plan_new(where, run_id, NOW)
        support.act_planner(where, run_id, support.feature_plan(criteria=[]))
        with self.assertRaises(InvalidFileError):
            planning.plan_check(where, run_id, NOW)

    def test_planner_must_not_edit(self) -> None:
        where, run_id = support.started(self)
        verifying.verify(where, run_id, NOW)
        planning.plan_new(where, run_id, NOW)
        support.act_planner(where, run_id)
        support.write_files(where, {"calc.py": "x = 1\n"})
        with self.assertRaisesRegex(StageError, "作業ツリーが変わりました"):
            planning.plan_check(where, run_id, NOW)

    def test_replan_feedback(self) -> None:
        where, run_id = support.planned(self, support.feature_plan(dependencies_to_add=["numpy"]))
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.gate), (trail.DECIDE, policy.H1))
        deciding.decide(where, run_id, policy.H1, policy.REPLAN, "依存を足さずに書いて", NOW)
        planning.plan_new(where, run_id, NOW)
        self.assertIn("- 依存を足さずに書いて", fsops.read_text(where.plan_prompt_path(run_id, 2)))
