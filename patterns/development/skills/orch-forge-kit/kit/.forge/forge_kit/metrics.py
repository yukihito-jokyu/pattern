"""指標の計算（集合の一致度、割合、平均、閾値との比較）を、副作用の無い関数で行う。"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

DIGITS = 3


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), DIGITS)


def rate(flags: Sequence[bool]) -> float | None:
    return mean([1.0 if flag else 0.0 for flag in flags])


def ratio(part: int, whole: int) -> float | None:
    """part / whole。whole が0なら測れないので None。"""
    return None if whole == 0 else part / whole


def pairwise_agreement(sets: Sequence[frozenset[str]]) -> float | None:
    """実行どうしの集合の一致度。比べる相手がいない（1件以下）なら None。"""
    pairs = list(itertools.combinations(sets, 2))
    return mean([jaccard(left, right) for left, right in pairs])


def is_met(value: float | None, threshold: float, direction: str) -> bool:
    if value is None:
        return False
    return value >= threshold if direction == "higher" else value <= threshold


def change_of(baseline: float | None, candidate: float | None, direction: str) -> str:
    """候補の値が baseline より良いか。比べられない（どちらかが None）なら unknown。"""
    if baseline is None or candidate is None:
        return "unknown"
    if candidate == baseline:
        return "same"
    improved = candidate > baseline if direction == "higher" else candidate < baseline
    return "better" if improved else "worse"
