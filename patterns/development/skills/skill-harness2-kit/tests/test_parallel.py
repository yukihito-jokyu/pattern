"""parallel のテスト。"""

from __future__ import annotations

import threading
import unittest
from functools import partial

from h2_kit import parallel


def _wait_then_return(gate: threading.Event, value: int) -> int:
    gate.wait(5)
    return value


class ParallelTest(unittest.TestCase):
    def test_results_follow_the_input_order(self) -> None:
        gate = threading.Event()
        jobs = [partial(_wait_then_return, gate, value) for value in range(4)]
        gate.set()
        self.assertEqual(parallel.run_ordered(jobs, 3), [0, 1, 2, 3])

    def test_width_one_runs_in_order(self) -> None:
        seen: list[int] = []
        jobs = [partial(seen.append, value) for value in range(3)]
        parallel.run_ordered(jobs, 1)
        self.assertEqual(seen, [0, 1, 2])
