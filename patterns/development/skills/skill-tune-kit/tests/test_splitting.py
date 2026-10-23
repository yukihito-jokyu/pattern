"""splitting のテスト。分割の再現性と割合を確かめる（STATE-03）。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import plan, splitting

RATIOS = splitting.Ratios(train=0.6, val=0.2, test=0.2)


def build_items(count: int, groups: int = 1) -> list[splitting.SplitItem]:
    return [splitting.SplitItem(case_id=f"c{i:02d}", group=f"g{i % groups}", pinned="") for i in range(1, count + 1)]


class SplittingTest(unittest.TestCase):
    def test_same_input_gives_same_split(self) -> None:
        items = build_items(10)
        self.assertEqual(splitting.compute_split(items, plan.DEFAULT_SEED, RATIOS), support.SPLITS)
        self.assertEqual(splitting.compute_split(list(reversed(items)), plan.DEFAULT_SEED, RATIOS), support.SPLITS)

    def test_counts_follow_ratios(self) -> None:
        result = splitting.compute_split(build_items(10), plan.DEFAULT_SEED, RATIOS)
        counts = {name: list(result.values()).count(name) for name in plan.SPLITS}
        self.assertEqual(counts, {"train": 6, "val": 2, "test": 2})

    def test_every_group_reaches_every_split(self) -> None:
        items = build_items(30, groups=3)
        result = splitting.compute_split(items, plan.DEFAULT_SEED, RATIOS)
        for group in ("g0", "g1", "g2"):
            names = {result[item.case_id] for item in items if item.group == group}
            self.assertEqual(names, set(plan.SPLITS), group)

    def test_pinned_case_keeps_its_split(self) -> None:
        items = [*build_items(9), splitting.SplitItem(case_id="c99", group="g0", pinned="test")]
        result = splitting.compute_split(items, plan.DEFAULT_SEED, RATIOS)
        self.assertEqual(result["c99"], "test")
        self.assertEqual(list(result.values()).count("test"), 2)

    def test_three_cases_fill_each_split(self) -> None:
        result = splitting.compute_split(build_items(3), plan.DEFAULT_SEED, RATIOS)
        self.assertEqual(sorted(result.values()), ["test", "train", "val"])
