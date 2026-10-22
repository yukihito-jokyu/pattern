"""render のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import render


class RenderTest(unittest.TestCase):
    def test_number_and_percent_show_missing(self) -> None:
        self.assertEqual(render.number(None), render.MISSING)
        self.assertEqual(render.number(1.25, 1), "1.2")
        self.assertEqual(render.percent(1, 0), render.MISSING)
        self.assertEqual(render.percent(1, 3), "33%")

    def test_table_escapes_cells(self) -> None:
        text = render.table(["a", "b"], [["x|y", "1\n2"], ["", "z"]])
        self.assertEqual(text.splitlines(), ["| a | b |", "|---|---|", "| x\\|y | 1 2 |", f"| {render.MISSING} | z |"])

    def test_bullets_empty(self) -> None:
        self.assertEqual(render.bullets([]), "- なし")
        self.assertEqual(render.bullets(["a", "b"]), "- a\n- b")

    def test_fence_grows_marker(self) -> None:
        self.assertEqual(render.fence("x"), "```text\nx\n```")
        self.assertTrue(render.fence("```\ncode\n```").startswith("````text"))

    def test_job_line(self) -> None:
        self.assertEqual(render.job("autoflow-builder", "builder-1", "p.md"), "job autoflow-builder builder-1 p.md")
