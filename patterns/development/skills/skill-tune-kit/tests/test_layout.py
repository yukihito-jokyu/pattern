"""layout のテスト。"""

from __future__ import annotations

import unittest
from pathlib import Path

from tune_kit import errors, layout


class LayoutTest(unittest.TestCase):
    def test_target_id_must_be_lower_kebab(self) -> None:
        with self.assertRaises(errors.KitError):
            layout.build_layout(Path("/repo"), "My_Target")

    def test_run_key_hides_version(self) -> None:
        first = layout.build_run_key("v0", "c01", 1, "sha")
        second = layout.build_run_key("v1", "c01", 1, "sha")
        self.assertNotEqual(first, second)
        self.assertNotIn("v0", first)

    def test_display_is_relative_inside_repo(self) -> None:
        where = layout.build_layout(Path("/repo"), "sample")
        self.assertEqual(where.display(where.plan_path), ".tune/targets/sample/plan.json")
        self.assertEqual(where.display(Path("/other/file")), "/other/file")

    def test_final_audit_lives_in_final_dir(self) -> None:
        where = layout.build_layout(Path("/repo"), "sample")
        self.assertEqual(where.audit_dir(None), where.final_dir)
        self.assertEqual(where.audit_dir(2), where.round_dir(2))
