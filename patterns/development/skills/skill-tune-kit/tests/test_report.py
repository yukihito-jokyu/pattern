"""report のテスト。報告と適用を確かめる（OPS-04）。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import fsops, layout


class ReportTest(unittest.TestCase):
    def test_report_summarizes_test_results(self) -> None:
        root = support.build_approved_repo(self)
        support.run_to_report(self, root)
        text = support.build_where(root).report_path.read_text(encoding="utf-8")
        self.assertIn("最良の版 v1 はテスト用でも元の版より良い。適用を勧める", text)
        self.assertIn("| テスト用の合格率 | 50.0% | 100.0% |", text)
        self.assertIn("| 1 | v0 → v1 |", text)

    def test_apply_replaces_target_skill(self) -> None:
        root = support.build_approved_repo(self)
        support.run_to_report(self, root)
        support.run_ok(self, root, "apply")
        skill = (root / support.SKILL_PATH / layout.SKILL_FILE).read_text(encoding="utf-8")
        self.assertIn(support.LINE, skill)

    def test_apply_refuses_changed_target(self) -> None:
        root = support.build_approved_repo(self)
        support.run_to_report(self, root)
        fsops.write_text(root / support.SKILL_PATH / "extra.md", "人が足した")
        code, _out, err = support.run_cli(root, "apply")
        self.assertEqual(code, 1)
        self.assertIn("承認の後に対象スキル", err)

    def test_skip_keeps_target_skill(self) -> None:
        root = support.build_approved_repo(self)
        support.run_to_report(self, root)
        support.run_ok(self, root, "apply", "--skip")
        skill = (root / support.SKILL_PATH / layout.SKILL_FILE).read_text(encoding="utf-8")
        self.assertNotIn(support.LINE, skill)
        self.assertIn("段階: 完了", support.list_status(root))
