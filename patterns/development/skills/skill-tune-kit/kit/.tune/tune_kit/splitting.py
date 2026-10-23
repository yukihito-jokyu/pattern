"""ケースを学習用・検証用・テスト用に決定的に分ける（ADR 0007）。"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

# 分割の名前。同点のときは前にあるものを優先する（テスト用と検証用を先に埋める）
ORDER = ("test", "val", "train")


@dataclass(frozen=True)
class SplitItem:
    """分割の入力。pinned は利用者が固定した分割（固定しないなら空文字）。"""

    case_id: str
    group: str
    pinned: str


@dataclass(frozen=True)
class Ratios:
    train: float
    val: float
    test: float


def compute_targets(total: int, ratios: Ratios) -> dict[str, int]:
    """分割ごとの目標の件数。検証用とテスト用は round(総数 × 比率)（最低1）、学習用は残り（最低1）。"""
    val = max(1, round(total * ratios.val))
    test = max(1, round(total * ratios.test))
    while total - val - test < 1 and (val > 1 or test > 1):
        if test >= val and test > 1:
            test -= 1
        else:
            val -= 1
    return {"train": total - val - test, "val": val, "test": test}


def _compute_rank(seed: str, case_id: str) -> str:
    return hashlib.sha256(f"{seed}:{case_id}".encode()).hexdigest()


def compute_order(items: Sequence[SplitItem], seed: str) -> list[SplitItem]:
    """group ごとにハッシュの順に並べ、各 group が列の中に均等に散らばるように混ぜる。"""
    groups: dict[str, list[SplitItem]] = {}
    for item in items:
        groups.setdefault(item.group, []).append(item)
    keyed: list[tuple[Fraction, str, SplitItem]] = []
    for name in sorted(groups):
        members = sorted(groups[name], key=lambda item: (_compute_rank(seed, item.case_id), item.case_id))
        size = len(members)
        keyed += [(Fraction(2 * index + 1, 2 * size), name, item) for index, item in enumerate(members)]
    return [item for _key, _name, item in sorted(keyed, key=lambda entry: (entry[0], entry[1]))]


def compute_split(items: Sequence[SplitItem], seed: str, ratios: Ratios) -> dict[str, str]:
    """ケースの ID から分割の名前への対応を返す。同じ入力からは常に同じ分割になる。"""
    targets = compute_targets(len(items), ratios)
    result = {item.case_id: item.pinned for item in items if item.pinned}
    for name in result.values():
        targets[name] = max(0, targets[name] - 1)
    free = [item for item in items if not item.pinned]
    if not free:
        return result
    total = sum(targets.values())
    if total != len(free):
        targets["train"] = max(0, len(free) - targets["val"] - targets["test"])
        total = sum(targets.values())
    assigned = dict.fromkeys(ORDER, 0)
    for position, item in enumerate(compute_order(free, seed), start=1):
        name = max(
            ORDER, key=lambda split: (Fraction(targets[split] * position, total) - assigned[split], -ORDER.index(split))
        )
        assigned[name] += 1
        result[item.case_id] = name
    return result
