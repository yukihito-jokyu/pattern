"""catalog のテスト。指標の一覧の id と、独自の指標の扱いを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import catalog


class CatalogTest(unittest.TestCase):
    def test_ids_are_unique_and_found(self) -> None:
        ids = [metric.id for metric in catalog.METRICS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(catalog.find("delegation"), catalog.METRICS[ids.index("delegation")])
        self.assertIsNone(catalog.find("unknown"))

    def test_custom_metric(self) -> None:
        self.assertTrue(catalog.is_custom("custom_1"))
        self.assertFalse(catalog.is_custom("custom_0"))
        metric = catalog.custom_metric("custom_1", "テストを先に書いている")
        self.assertEqual((metric.method, metric.direction), ("grader", "higher"))


if __name__ == "__main__":
    unittest.main()
