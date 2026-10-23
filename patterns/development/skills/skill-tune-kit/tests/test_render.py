"""render のテスト。"""

from __future__ import annotations

import unittest
from fractions import Fraction

from tune_kit import render


class RenderTest(unittest.TestCase):
    def test_rate_is_percent_or_missing(self) -> None:
        self.assertEqual(render.render_rate(Fraction(2, 3)), "66.7%")
        self.assertEqual(render.render_rate(None), render.MISSING)

    def test_table_escapes_pipe_and_newline(self) -> None:
        table = render.render_table(["a", "b"], [["x|y", "1\n2"]])
        self.assertEqual(table.splitlines()[2], "| x\\|y | 1 2 |")

    def test_fence_is_longer_than_backticks_inside(self) -> None:
        self.assertTrue(render.render_fence("```\ncode\n```").startswith("````\n"))

    def test_bullets_show_none_when_empty(self) -> None:
        self.assertEqual(render.render_bullets([]), "- なし")
