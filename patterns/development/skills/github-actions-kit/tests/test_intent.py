"""intent（作り直しの前後の棚卸し）のテスト。"""

from __future__ import annotations

import unittest
from pathlib import Path

from gha_kit import intent, yamlnode

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class InventoryTest(unittest.TestCase):
    def test_lists_triggers_secrets_actions_commands_and_artifacts(self) -> None:
        items = intent.inventory(yamlnode.load(FIXTURES, "intent/old.yml"))

        self.assertEqual(items["trigger"], {"schedule"})
        self.assertEqual(items["secret"], {"DEPLOY_TOKEN"})
        self.assertEqual(items["uses"], {"actions/checkout", "actions/upload-artifact"})
        self.assertEqual(items["run"], {"npm ci", "npm run build"})
        self.assertEqual(items["artifact"], {"dist"})
        self.assertEqual(items["environment"], {"prod"})


class CompareTest(unittest.TestCase):
    def test_returns_facts_missing_from_the_rebuilt_workflow(self) -> None:
        old = yamlnode.load(FIXTURES, "intent/old.yml")
        new = yamlnode.load(FIXTURES, "intent/new.yml")

        missing = intent.compare(old, new)

        self.assertIn(("secrets", "DEPLOY_TOKEN"), missing)
        self.assertIn(("コマンド", "npm run build"), missing)
        self.assertIn(("成果物", "dist"), missing)
        self.assertNotIn(("コマンド", "npm ci"), missing)


if __name__ == "__main__":
    unittest.main()
