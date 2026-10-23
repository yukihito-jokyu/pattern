"""metrics のテスト。指標と採否の規則を確かめる（ADR 0008）。"""

from __future__ import annotations

import unittest
from fractions import Fraction

from tune_kit import metrics


def build_summary(*runs: tuple[str, bool, bool]) -> metrics.Summary:
    """(ケース, must の合否, 検査 Q の合否) の並びから指標を作る。"""
    scores = [metrics.RunScore(case_id=c, must_passed=m, checks=(("K", m), ("Q", q))) for c, m, q in runs]
    return metrics.compute_summary(scores)


class MetricsTest(unittest.TestCase):
    def test_summary_averages_case_rates(self) -> None:
        summary = build_summary(("a", True, True), ("a", False, True), ("b", True, False))
        self.assertEqual(summary.pass_rate, Fraction(3, 4))
        self.assertEqual(summary.check_rate, Fraction(4, 6))
        self.assertFalse(metrics.is_perfect(summary))

    def test_adopts_when_val_pass_rate_rises(self) -> None:
        before = build_summary(("a", False, True), ("b", True, True))
        after = build_summary(("a", True, True), ("b", True, True))
        decision = metrics.compute_decision(before, after, before, after)
        self.assertTrue(decision.adopted)

    def test_rejects_regression_even_if_rate_rises(self) -> None:
        before = build_summary(("a", True, True), ("b", False, True), ("c", False, True))
        after = build_summary(("a", False, True), ("b", True, True), ("c", True, True))
        decision = metrics.compute_decision(before, after, before, after)
        self.assertFalse(decision.adopted)
        self.assertEqual(decision.regressions, ("a",))

    def test_tie_is_broken_by_check_rate(self) -> None:
        before = build_summary(("a", True, False))
        after = build_summary(("a", True, True))
        self.assertTrue(metrics.compute_decision(before, after, before, after).adopted)
        self.assertFalse(metrics.compute_decision(after, after, after, after).adopted)

    def test_marks_overfit_when_only_train_improves(self) -> None:
        val = build_summary(("v", False, True))
        train_before = build_summary(("t", False, True))
        train_after = build_summary(("t", True, True))
        decision = metrics.compute_decision(val, val, train_before, train_after)
        self.assertFalse(decision.adopted)
        self.assertTrue(decision.overfit)
