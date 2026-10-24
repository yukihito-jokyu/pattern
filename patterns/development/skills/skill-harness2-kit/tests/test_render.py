"""render のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import render


class RenderTest(unittest.TestCase):
    def test_table_escapes_pipes_and_newlines(self) -> None:
        table = render.render_table(["a", "b"], [["x|y", "1\n2"]])
        self.assertEqual(table.splitlines(), ["| a | b |", "|---|---|", "| x\\|y | 1 2 |"])

    def test_fence_is_longer_than_the_longest_fence_inside(self) -> None:
        fenced = render.render_fence("````\nx\n````", "diff")
        self.assertTrue(fenced.startswith("`````diff\n"))
        self.assertTrue(fenced.endswith("\n`````"))

    def test_usd_has_two_decimals(self) -> None:
        self.assertEqual(render.render_usd(1.5), "$1.50")

    def test_sections_skip_empty_parts_and_collapse_blank_runs(self) -> None:
        self.assertEqual(render.render_sections(["# a", "", "b\n\n\n\nc"]), "# a\n\nb\n\nc\n")
