"""planning のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import fsops, planning, workspace
from h2_kit.errors import StageError
from tests import support


class PlanningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where = support.build_where(support.build_repo(self))

    def test_init_writes_the_profile_once(self) -> None:
        planning.init(self.where, support.SKILL_PATH)
        self.assertIn(f'"skill": "{support.SKILL_PATH}"', fsops.read_text(self.where.profile_path))
        with self.assertRaises(StageError):
            planning.init(self.where, support.SKILL_PATH)

    def test_init_needs_a_skill(self) -> None:
        with self.assertRaises(StageError):
            planning.init(self.where, ".claude/skills/none")

    def test_check_writes_the_budget(self) -> None:
        support.write_profile(self.where, k=2, modes=["parallel", "sequential"])
        support.write_task(self.where)
        text = planning.check(self.where)
        self.assertIn("| 実行 | 14 |", text)
        self.assertEqual(
            fsops.read_text(self.where.plan_path) + "\n次: plan.md を人に見せ、承認を得てから approve を実行する", text
        )

    def test_check_refuses_answers_in_the_task(self) -> None:
        support.write_profile(self.where, leak_globs=["answers/*"])
        support.write_task(self.where, files={"answers/key.md": "答え"})
        with self.assertRaises(StageError):
            planning.check(self.where)

    def test_approve_needs_the_current_plan(self) -> None:
        support.write_profile(self.where)
        support.write_task(self.where)
        with self.assertRaises(StageError):
            planning.approve(self.where, support.TODAY)
        planning.check(self.where)
        support.write_task(self.where, "t2")
        with self.assertRaises(StageError):
            planning.approve(self.where, support.TODAY)

    def test_approve_counts_rounds(self) -> None:
        support.write_profile(self.where)
        support.write_task(self.where)
        for expected in (1, 2):
            planning.check(self.where)
            planning.approve(self.where, support.TODAY)
            approval = workspace.load_approval(self.where)
            assert approval is not None
            self.assertEqual(approval.round, expected)
            self.assertTrue(self.where.base_skill_dir(expected).is_dir())
