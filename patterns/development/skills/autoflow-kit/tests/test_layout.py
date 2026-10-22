"""layout のテスト。"""

from __future__ import annotations

import unittest
from pathlib import Path

from autoflow_kit import layout
from autoflow_kit.errors import KitError
from autoflow_kit.layout import Layout


class LayoutTest(unittest.TestCase):
    def test_make_run_id(self) -> None:
        self.assertEqual(layout.make_run_id("2026-10-21T14:30:00+09:00", "PROJ-123"), "20261021-143000-proj-123")
        self.assertEqual(layout.make_run_id("2026-10-21T14:30:00+09:00", ""), "20261021-143000")
        self.assertEqual(layout.make_run_id("2026-10-21T14:30:00+09:00", "#42 ログイン"), "20261021-143000-42")

    def test_make_run_id_rejects_bad_time(self) -> None:
        with self.assertRaises(KitError):
            layout.make_run_id("昨日", "x")

    def test_run_dir_rejects_bad_id(self) -> None:
        with self.assertRaises(KitError):
            Layout(Path("/repo")).run_dir("../etc")

    def test_paths(self) -> None:
        where = Layout(Path("/repo"))
        run_id = "20261021-143000"
        self.assertEqual(where.relative(where.trail_path(run_id)), f".autoflow/runs/{run_id}/trail.jsonl")
        self.assertEqual(where.relative(where.plan_path(run_id, 2)), f".autoflow/runs/{run_id}/plan/2/plan.json")
        self.assertEqual(
            where.relative(where.finder_prompt_path(run_id, 1, "security")),
            f".autoflow/runs/{run_id}/review/round-1/finder-security-prompt.md",
        )
        self.assertEqual(where.relative(where.gate_path(run_id, "H2", 1)), f".autoflow/runs/{run_id}/gates/h2-1.md")
        self.assertEqual(
            where.relative(where.evidence_log_path(run_id, 3, "unit")), f".autoflow/runs/{run_id}/evidence/3-unit.log"
        )
        self.assertEqual(layout.make_branch(run_id), f"autoflow/{run_id}")
