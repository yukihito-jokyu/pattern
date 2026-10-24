"""context のテスト。証拠の木の中身（STATE-03）。"""

from __future__ import annotations

import unittest

from h2_kit import context, fsops, layout, rollout, skilltree
from h2_kit.errors import LeakError
from tests import support


class ContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.where = support.build_where(support.build_repo(self))
        self.task = support.write_task(self.where, files={"memo.md": "材料\n", "answers/key.md": "答え\n"})
        self.tree = support.read_skill(self.where)
        model = support.build_model()
        job = rollout.Job("base1", self.where.repo / "r" / "base1", self.tree, self.task, model)
        self.view = rollout.run_rollout(job)
        self.root = self.where.repo / "s" / layout.CONTEXT_DIR

    def test_all_evidence_is_written_as_files(self) -> None:
        changed = skilltree.build_replaced(self.tree, "references/new.md", "# 新しい\n")
        evidence = context.Evidence(
            prompt=self.task.prompt,
            source=self.task.directory / layout.TASK_WORKSPACE_DIR,
            rollouts=(self.view,),
            harness=self.tree,
            pool=(context.PoolEntry("inv1", changed, self.view),),
            decisions=(("inv1", "references/new.md を足した"),),
        )
        built = context.write_context(self.root, evidence, ["answers/*"])
        expected = [
            "decisions/inv1.md",
            "deliverables/base1.md",
            "harness/SKILL.md",
            "pool/inv1/harness.diff",
            "pool/inv1/harness/references/new.md",
            "pool/inv1/produced.md",
            "pool/inv1/rollout.md",
            "rollouts/base1.md",
            "source/memo.md",
            "task.md",
        ]
        files = fsops.list_files(self.root)
        for path in expected:
            self.assertIn(path, files)
        self.assertNotIn("source/answers/key.md", files)
        self.assertIn("+# 新しい", fsops.read_text(self.root / "pool" / "inv1" / "harness.diff"))
        self.assertIn("`context/pool/`: inv1", built.layout)
        self.assertEqual(fsops.read_text(self.root / "rollouts" / "base1.md"), rollout.read_trajectory(self.view))

    def test_empty_parts_are_not_listed(self) -> None:
        built = context.write_context(self.root, context.Evidence(prompt="依頼", source=self.where.repo / "none"), [])
        self.assertEqual(built.layout, "- `context/task.md`")

    def test_grader_marker_stops_the_session(self) -> None:
        evidence = context.Evidence(
            prompt="依頼", source=self.where.repo / "none", decisions=(("x", '"pass_rate": 1'),)
        )
        with self.assertRaises(LeakError):
            context.write_context(self.root, evidence, [])
