"""views のテスト。人とサブエージェントが読む charter と設計の版、費用の見積もりを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import charter, views, workspace
from tests import support


class ViewsTest(unittest.TestCase):
    def test_render_charter(self) -> None:
        model = charter.parse(support.orch_charter(), "charter.json")
        full = views.render_charter(model, "unapproved", include_holdout=True)
        visible = views.render_charter(model, "approved", include_holdout=False)
        self.assertIn("在庫を空にする関数を足して", full)
        self.assertNotIn("在庫を空にする関数を足して", visible)
        self.assertIn("未承認", full)
        self.assertIn("Bash(python3 check.py)", full)

    def test_estimate(self) -> None:
        model = charter.parse(support.orch_charter(), "charter.json")
        cost = views.estimate(model)
        self.assertEqual((cost.runs_per_slot, cost.final_runs, cost.total_runs), (2, 4, 10))
        self.assertEqual(cost.max_cost_usd, 10.0)

    def test_render_design(self) -> None:
        root = support.make_repo(self)
        where = support.make_where(root, support.SKILL)
        support.approve(where, support.orch_charter())
        support.act_designer(where)
        _data, found = workspace.load_design(where, charter.parse(support.orch_charter(), "charter.json"))
        text = views.render_design(found, "unapproved")
        self.assertIn("dev-orch-implementer", text)
        self.assertIn("既存の書き方に合わせる", text)


if __name__ == "__main__":
    unittest.main()
