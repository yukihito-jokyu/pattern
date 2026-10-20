"""goals のテスト。対象の一覧、charter のひな形・検査・承認の記録を確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import fsops, goals, workspace
from forge_kit.errors import KitError
from tests import support


class GoalsTest(unittest.TestCase):
    def test_targets(self) -> None:
        root = support.make_repo(self)
        fsops.write_text(root / ".claude/skills/forge-run/SKILL.md", "description: 道具\n")
        text = goals.targets(root)
        self.assertIn("dev-orch", text)
        self.assertNotIn("forge-run", text)

    def test_metric_catalog(self) -> None:
        self.assertIn("delegation", goals.metric_catalog())

    def test_charter_new(self) -> None:
        root = support.make_repo(self)
        where = support.make_where(root, support.NEW_SKILL)
        self.assertIn("forge-build", goals.charter_new(where, support.NEW_SKILL))
        with self.assertRaises(KitError):
            goals.charter_new(where, support.NEW_SKILL)

    def test_charter_check_and_approve(self) -> None:
        root = support.make_repo(self)
        where = support.make_where(root, support.SKILL)
        data = support.orch_charter()
        data["tasks"] = [
            {"id": "T1", "prompt": "在庫から数を減らす関数を足して", "acceptance": ["在庫を減らす関数がある"]}
        ]
        fsops.write_json(where.charter_path, data)
        self.assertIn("WARN ホールドアウト", goals.charter_check(where))
        goals.charter_approve(where, support.TODAY)
        model, _sha = workspace.approved_charter(where)
        self.assertEqual(model.approval.approved_on if model.approval else "", support.TODAY)


if __name__ == "__main__":
    unittest.main()
