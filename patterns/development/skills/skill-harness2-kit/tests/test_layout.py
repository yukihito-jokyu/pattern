"""layout のテスト。"""

from __future__ import annotations

import unittest
from pathlib import Path

from h2_kit import layout
from h2_kit.errors import InvalidFileError


class LayoutTest(unittest.TestCase):
    def test_labels_and_session_names(self) -> None:
        self.assertEqual(layout.build_label(layout.AGG, 2), "agg2")
        self.assertEqual(layout.build_session_name("inv1", 2), "inv1.a2")
        self.assertTrue(layout.is_base_label("base1"))
        self.assertFalse(layout.is_base_label("agg1"))

    def test_names_are_lowercase_words(self) -> None:
        self.assertEqual(layout.require_name("対象", "minutes-1"), "minutes-1")
        for name in ("Minutes", "../x", ""):
            with self.subTest(name=name), self.assertRaises(InvalidFileError):
                layout.require_name("対象", name)

    def test_paths_of_a_task(self) -> None:
        where = layout.Layout(Path("/repo"), "t")
        place = where.task_place(3, "a")
        self.assertEqual(
            place.rollout_dir("parallel", "agg1"), Path("/repo/.h2/targets/t/runs/r3/a/parallel/rollouts/agg1")
        )
        self.assertEqual(where.checks_path("a"), Path("/repo/.h2/targets/t/tasks/a/checks.json"))
