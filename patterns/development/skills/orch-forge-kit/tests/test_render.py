"""render のテスト。表・数・箇条書き・job の行の書き方を確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import render


class RenderTest(unittest.TestCase):
    def test_table_escapes_pipes_and_newlines(self) -> None:
        text = render.table(["a", "b"], [["x|y", "1\n2"]])
        self.assertEqual(text, "| a | b |\n|---|---|\n| x\\|y | 1 2 |")

    def test_number_and_usd(self) -> None:
        self.assertEqual(render.number(0.5), "0.500")
        self.assertEqual(render.number(None), render.MISSING)
        self.assertEqual(render.usd(1.234), "$1.23")

    def test_bullets_and_mark(self) -> None:
        self.assertEqual(render.bullets([]), "- なし")
        self.assertEqual(render.bullets(["a", "b"]), "- a\n- b")
        self.assertEqual(render.mark(True), "達成")

    def test_job(self) -> None:
        self.assertEqual(render.job("forge-grader", "T1-a1", "/p.md"), "job forge-grader T1-a1 /p.md")


if __name__ == "__main__":
    unittest.main()
