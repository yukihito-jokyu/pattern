"""ledger のテスト。R = 4k、P = 3k の恒等式（STATE-07）。"""

from __future__ import annotations

import unittest

from h2_kit import ledger
from h2_kit.errors import StageError

PARALLEL_K2_ROLLOUTS = ["base1", "base2", "inv1", "dom1", "inv2", "dom2", "agg1", "agg2"]
PARALLEL_K2_SESSIONS = ["inv1", "dom1", "inv2", "dom2", "agg1", "agg2"]


class LedgerTest(unittest.TestCase):
    def test_parallel_k2_lands_on_identity(self) -> None:
        book = ledger.build_book(PARALLEL_K2_ROLLOUTS, PARALLEL_K2_SESSIONS)
        self.assertEqual(ledger.check_identity(book, 2), [])
        self.assertEqual((ledger.compute_expected_rollouts(2), ledger.compute_expected_sessions(2)), (8, 6))

    def test_duplicates_are_reported_before_counts(self) -> None:
        book = ledger.build_book([*PARALLEL_K2_ROLLOUTS, "agg1"], PARALLEL_K2_SESSIONS)
        problems = ledger.check_identity(book, 2)
        self.assertEqual(len(problems), 1)
        self.assertIn("agg1", problems[0])

    def test_wrong_count_raises(self) -> None:
        book = ledger.build_book(PARALLEL_K2_ROLLOUTS[:-1], PARALLEL_K2_SESSIONS)
        with self.assertRaises(StageError):
            ledger.require_identity(book, 2)

    def test_budget_counts_base_once_for_all_modes(self) -> None:
        budget = ledger.compute_budget(2, 2, selector=True)
        self.assertEqual((budget.rollouts, budget.sessions, budget.side_sessions), (14, 12, 4))
