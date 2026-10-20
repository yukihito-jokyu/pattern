"""status のテスト。作業領域のファイルから段階を求め、次の手の行を決まった書き出しで出すことを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import fsops, status
from tests import support


class StatusTest(unittest.TestCase):
    def assert_kinds(self, text: str) -> None:
        for line in text.splitlines():
            self.assertTrue(line.startswith(status.LINE_KINDS) or line.startswith("  - "), line)

    def test_without_charter(self) -> None:
        root = support.make_repo(self)
        text = status.status(support.make_where(root, support.SKILL))
        self.assertIn("（forge-goals）", text)
        self.assert_kinds(text)

    def test_unapproved_charter(self) -> None:
        root = support.make_repo(self)
        where = support.make_where(root, support.SKILL)
        fsops.write_json(where.charter_path, support.orch_charter())
        self.assertIn("charter が未承認", status.status(where))

    def test_build_steps(self) -> None:
        where = support.approved_layout(self, support.orch_charter(support.NEW_SKILL))
        text = status.status(where)
        self.assertIn("design-new --target new-orch", text)
        self.assert_kinds(text)

    def test_evaluation_steps(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        text = status.status(where)
        self.assertIn("prepare --target dev-orch --variant baseline --round 1", text)
        self.assertIn("改善のラウンド: 0 / 2 回が決定済み", text)
        self.assert_kinds(text)

    def test_bundle_problems(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        fsops.remove_tree(where.claude_dir / "agents/dev-orch-reviewer.md")
        text = status.status(where)
        self.assertIn("バンドルの決まりを満たしていない", text)
        self.assertIn("  - B09 ", text)
        self.assert_kinds(text)


if __name__ == "__main__":
    unittest.main()
