"""並行の実行。スレッドで動かし、結果は入力の順で返す。並行に触れるのはこのモジュールだけ（ASYNC-01）。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")


def run_ordered(jobs: Sequence[Callable[[], T]], width: int) -> list[T]:
    """jobs を最大 width 個ずつ並行に動かし、結果を jobs の順で返す。width が1以下なら順に動かす。"""
    if width <= 1 or len(jobs) <= 1:
        return [job() for job in jobs]
    with ThreadPoolExecutor(max_workers=min(width, len(jobs))) as pool:
        futures = [pool.submit(job) for job in jobs]
        return [future.result() for future in futures]
