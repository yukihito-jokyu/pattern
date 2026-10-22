"""context のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import context, trail
from autoflow_kit.errors import StageError
from tests import support


class ContextTest(unittest.TestCase):
    def test_begin_checks_step(self) -> None:
        where, run_id = support.started(self)
        self.assertEqual(context.begin(where, run_id, trail.VERIFY).next.mode, trail.BASELINE)
        with self.assertRaisesRegex(StageError, "今は plan の番ではなく verify の番です"):
            context.begin(where, run_id, trail.PLAN)

    def test_peek_requires_work_branch(self) -> None:
        where, run_id = support.started(self)
        support.git(where.root, "switch", "-q", "main")
        with self.assertRaisesRegex(StageError, "autoflow/20261021-143000 に切り替えて"):
            context.peek(where, run_id)

    def test_peek_reads_snapshot_profile(self) -> None:
        where, run_id = support.started(self)
        ctx = context.peek(where, run_id)
        self.assertEqual(ctx.profile.verify.commands, (support.UNIT,))
        self.assertEqual(ctx.start.kind, trail.STARTED)
        self.assertEqual(ctx.tree, ctx.start.tree)

    def test_require_prompted(self) -> None:
        where, run_id = support.started(self)
        ctx = context.peek(where, run_id)
        with self.assertRaisesRegex(StageError, "plan-new --run"):
            context.require_prompted(ctx, trail.PLANNER, "plan-new")

    def test_require_same_tree(self) -> None:
        context.require_same_tree("a" * 40, "a" * 40)
        with self.assertRaisesRegex(StageError, "作業ツリーが変わりました"):
            context.require_same_tree("a" * 40, "b" * 40)
