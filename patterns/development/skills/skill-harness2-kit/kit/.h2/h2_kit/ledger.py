"""1つのタスク・モードの台帳。実行 R = 4k、編集のセッション P = 3k の恒等式を確かめる（STATE-07）。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from h2_kit import layout
from h2_kit.errors import StageError

ROLLOUTS_PER_K = 4
SESSIONS_PER_K = 3


@dataclass(frozen=True)
class Book:
    """記録した順のラベル。基準の実行はモードで共有するが、各モードの台帳に入れる（harness2 と同じ）。"""

    rollouts: tuple[str, ...]
    sessions: tuple[str, ...]


@dataclass(frozen=True)
class Budget:
    """1つのタスクで使う回数。基準の実行は全モードで1回だけ数える。"""

    rollouts: int
    sessions: int
    side_sessions: int


def build_book(rollouts: Sequence[str], sessions: Sequence[str]) -> Book:
    return Book(tuple(rollouts), tuple(sessions))


def compute_expected_rollouts(k: int) -> int:
    """R = 4k：基準 k、候補 2k、完成品 k。"""
    return ROLLOUTS_PER_K * k


def compute_expected_sessions(k: int) -> int:
    """P = 3k：INV k、DOM k、合成 k（並列は agg1..k、逐次は c1..k）。"""
    return SESSIONS_PER_K * k


def check_identity(book: Book, k: int) -> list[str]:
    """重複したラベルを先に確かめ、その後に件数を確かめる。"""
    problems = [
        f"{kind}のラベル {label} が {count} 回あります"
        for kind, labels in (("実行", book.rollouts), ("セッション", book.sessions))
        for label, count in sorted(Counter(labels).items())
        if count > 1
    ]
    if problems:
        return problems
    if len(book.rollouts) != compute_expected_rollouts(k):
        problems.append(f"実行が {len(book.rollouts)} 回です（R = 4k = {compute_expected_rollouts(k)} のはず）")
    if len(book.sessions) != compute_expected_sessions(k):
        problems.append(f"セッションが {len(book.sessions)} 回です（P = 3k = {compute_expected_sessions(k)} のはず）")
    base = [label for label in book.rollouts if layout.is_base_label(label)]
    if len(base) != k:
        problems.append(f"基準の実行が {len(base)} 回です（k = {k} のはず）")
    return problems


def require_identity(book: Book, k: int) -> Book:
    problems = check_identity(book, k)
    if problems:
        raise StageError("台帳が予算の恒等式に合いません: " + "、".join(problems))
    return book


def compute_budget(k: int, modes: int, selector: bool) -> Budget:
    """plan.md の予算。selector は選択役を起動するか（k が2以上）。"""
    rollouts = k + modes * (compute_expected_rollouts(k) - k)
    sessions = modes * compute_expected_sessions(k)
    side_sessions = modes * (2 if selector else 1)
    return Budget(rollouts, sessions, side_sessions)
