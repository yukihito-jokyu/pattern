"""metrics のテスト。平均・割合・一致度・判定・変化の計算を確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import metrics


class MetricsTest(unittest.TestCase):
    def test_mean_rate_ratio(self) -> None:
        self.assertEqual(metrics.mean([1.0, 0.0, 0.5]), 0.5)
        self.assertIsNone(metrics.mean([]))
        self.assertEqual(metrics.rate([True, False]), 0.5)
        self.assertIsNone(metrics.ratio(0, 0))
        self.assertEqual(metrics.ratio(1, 4), 0.25)

    def test_pairwise_agreement(self) -> None:
        same = frozenset({"a.py"})
        self.assertEqual(metrics.pairwise_agreement([same, same]), 1.0)
        self.assertEqual(metrics.pairwise_agreement([same, frozenset({"b.py"})]), 0.0)
        self.assertIsNone(metrics.pairwise_agreement([same]))

    def test_meets_and_change_of(self) -> None:
        self.assertTrue(metrics.is_met(1.0, 1.0, "higher"))
        self.assertFalse(metrics.is_met(None, 0.0, "higher"))
        self.assertTrue(metrics.is_met(1.0, 2.0, "lower"))
        self.assertEqual(metrics.change_of(0.5, 1.0, "higher"), "better")
        self.assertEqual(metrics.change_of(0.5, 1.0, "lower"), "worse")
        self.assertEqual(metrics.change_of(0.5, 0.5, "higher"), "same")
        self.assertEqual(metrics.change_of(None, 0.5, "higher"), "unknown")


if __name__ == "__main__":
    unittest.main()
