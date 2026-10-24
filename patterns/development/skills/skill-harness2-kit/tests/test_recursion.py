"""recursion のテスト。差し戻し、fell_back、台帳の恒等式（STATE-06、STATE-07）。"""

from __future__ import annotations

import unittest
from collections.abc import Sequence

from h2_kit import fsops, layout, recursion, workspace
from tests import support


class RecursionTest(unittest.TestCase):
    def build_env(self, mode: str = layout.PARALLEL, behaviors: Sequence[str] = (), k: int = 1) -> recursion.Env:
        where = support.build_approved(self, behaviors=behaviors, k=k, width=2)
        approved = workspace.load_approved(where)
        task = approved.tasks[0]
        place = where.task_place(approved.round, task.task_id)
        tree = support.read_skill(where)
        base = recursion.run_base(approved.profile, task, place, tree)
        return recursion.Env(approved.profile, task, place, mode, tree, tuple(base), None, where.templates_dir)

    def test_parallel_k2_lands_on_identity(self) -> None:
        result = recursion.run_mode(self.build_env(k=2))
        self.assertEqual(len(result.book.rollouts), 8)
        self.assertEqual(result.book.sessions, ("inv1", "dom1", "inv2", "dom2", "agg1", "agg2"))
        self.assertEqual([stage.label for stage in result.finals], ["agg1", "agg2"])

    def test_sequential_k2_lands_on_identity(self) -> None:
        env = self.build_env(mode=layout.SEQUENTIAL, k=2)
        result = recursion.run_mode(env)
        self.assertEqual(len(result.book.rollouts), 8)
        self.assertEqual(result.book.sessions, ("inv1", "dom1", "c1", "inv2", "dom2", "c2"))
        self.assertTrue(env.place.decision_path(layout.SEQUENTIAL, "c2").is_file())

    def test_rejected_candidate_is_retried_once_with_the_reason(self) -> None:
        env = self.build_env(behaviors=("invalid-once",))
        result = recursion.run_mode(env)
        stage = result.stages[0]
        self.assertFalse(stage.fell_back)
        self.assertIn("references/inv-check.md", stage.tree.paths)
        retry = env.place.session_dir(env.mode, "inv1", 2)
        self.assertIn("前の試みは却下された", fsops.read_text(retry / layout.MISSION_FILE))
        self.assertTrue((retry / layout.CONTEXT_DIR / layout.HARNESS_DIR / "scripts" / "check.py").is_file())

    def test_second_rejection_falls_back_to_the_input(self) -> None:
        env = self.build_env(behaviors=("invalid",))
        stage = recursion.run_mode(env).stages[0]
        self.assertTrue(stage.fell_back)
        self.assertEqual(stage.tree, env.base_tree)
        self.assertIn("コンパイル", stage.error)
        self.assertFalse(env.place.session_dir(env.mode, "inv1", 3).exists())

    def test_off_surface_tree_is_not_written_back(self) -> None:
        env = self.build_env(behaviors=("off-surface",))
        stage = recursion.run_mode(env).stages[0]
        self.assertTrue(stage.fell_back)
        retry = env.place.session_dir(env.mode, "inv1", 2) / layout.CONTEXT_DIR / layout.HARNESS_DIR
        self.assertFalse((retry / "notes.txt").exists())

    def test_keep_base_is_a_valid_answer(self) -> None:
        result = recursion.run_mode(self.build_env(behaviors=("keep",)))
        self.assertTrue(all(stage.kept_base and not stage.fell_back for stage in result.stages))

    def test_failed_session_falls_back(self) -> None:
        stage = recursion.run_mode(self.build_env(behaviors=("fail-inv",))).stages[0]
        self.assertTrue(stage.fell_back)
        self.assertTrue(stage.error)
