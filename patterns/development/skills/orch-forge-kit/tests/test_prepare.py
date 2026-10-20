"""prepare のテスト。評価用のコピーにバンドルを入れ、道具のスキルを除き、実行役のプロンプトを書くことを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import bundle, fsops, layout, prepare, workspace
from forge_kit.errors import InvalidFileError, StageError
from tests import support


class PrepareTest(unittest.TestCase):
    def test_prepare(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        fsops.write_text(where.claude_dir / "skills/forge-run/SKILL.md", "道具\n")
        slot = layout.make_slot("baseline", 1)
        self.assertIn("実行 2 件", prepare.prepare(where, slot))
        plan = workspace.load_plan(where, slot)
        self.assertEqual([run.run_id for run in plan.runs], ["T1-a1", "T1-a2"])
        copy = where.copy_dir(slot, "T1-a1")
        self.assertTrue(bundle.has_bundle(copy / layout.CLAUDE_DIR, support.SKILL))
        self.assertFalse((copy / ".claude/skills/forge-run").exists())
        self.assertFalse((copy / ".forge").exists())
        self.assertEqual(fsops.read_text(where.prompt_path(slot, "T1-a1")).strip(), f"/dev-orch {support.TASK_PROMPT}")
        self.assertIn("既定:", fsops.read_text(where.system_path(slot, "T1-a1")))
        with self.assertRaises(StageError):
            prepare.prepare(where, slot)

    def test_final_includes_holdout(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        slot = layout.make_slot("final", 0)
        prepare.prepare(where, slot)
        self.assertEqual({run.task_id for run in workspace.load_plan(where, slot).runs}, {"T1", "H1"})

    def test_candidate_needs_checked_proposal(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        with self.assertRaises(StageError):
            prepare.prepare(where, layout.make_slot("candidate", 1))

    def test_bundle_must_follow_rules(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        fsops.remove_tree(where.claude_dir / "agents/dev-orch-reviewer.md")
        with self.assertRaises(InvalidFileError):
            prepare.prepare(where, layout.make_slot("baseline", 1))


if __name__ == "__main__":
    unittest.main()
