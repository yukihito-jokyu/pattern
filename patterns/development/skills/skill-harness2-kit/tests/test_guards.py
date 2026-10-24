"""guards のテスト。答えを方法に入れない遮断（STATE-04）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h2_kit import fsops, guards, skilltree
from h2_kit.errors import LeakError


class GuardsTest(unittest.TestCase):
    def test_measurement_words_are_rejected_in_both_languages(self) -> None:
        for text in ("Maximize the SCORE", "採点の基準に合わせる", "正解と同じにする", "rubric を満たす"):
            with self.subTest(text=text):
                self.assertTrue(guards.check_measurement_words("work", text))
        self.assertEqual(guards.check_measurement_words("work", "議事録の日付をそろえる"), [])

    def test_grader_markers_in_names_and_text(self) -> None:
        self.assertTrue(guards.check_text_markers("out.json", '{"pass_rate": 1}'))
        self.assertTrue(guards.check_text_markers("judged.json", '{"h2_judged": true}'))
        self.assertEqual(guards.check_text_markers("a.md", "pass rate の話"), [])

    def test_leak_paths_match_anywhere_below(self) -> None:
        self.assertTrue(guards.is_leak_path("answers/key.md", ["answers/*"]))
        self.assertTrue(guards.is_leak_path("deep/answers/key.md", ["answers/*"]))
        self.assertTrue(guards.is_leak_path("expected.md", ["./expected.md"]))
        self.assertFalse(guards.is_leak_path("memo.md", ["answers/*"]))

    def test_dirty_tree_and_directory_raise(self) -> None:
        tree = skilltree.build_tree({"SKILL.md": "deterministic_eval_summary を見る"})
        with self.assertRaises(LeakError):
            guards.require_clean_tree(tree, ())
        with tempfile.TemporaryDirectory() as name:
            fsops.write_text(Path(name) / "answers" / "a.md", "答え")
            with self.assertRaises(LeakError):
                guards.require_clean_directory(Path(name), ["answers/*"])
