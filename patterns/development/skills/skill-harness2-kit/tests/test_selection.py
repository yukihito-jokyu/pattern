"""selection のテスト。匿名の ID と盲検（STATE-05）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from h2_kit import fsops, layout, rollout, selection, workspace
from tests import support


def _build_view(root: Path, label: str, delivered: bool = True) -> rollout.RolloutView:
    directory = root / label
    fsops.write_text(directory / layout.DELIVERABLE_FILE, "# 最後の返答\n\n整えた議事録\n")
    record = workspace.RunRecord(label, "f", True, delivered, True, 0.0, 1, "success", 0, 1)
    return rollout.RolloutView(label, directory, record)


class SelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = support.build_repo(self)

    def build_request(self, **fields: object) -> selection.Request:
        model = support.build_model(**{"k": 2, **fields})
        templates = self.root / layout.H2_DIR / layout.TEMPLATES_DIR / layout.PROMPTS_DIR
        source = self.root / "material"
        return selection.Request(model, "依頼", source, self.root / "selection", templates, "t1", layout.PARALLEL)

    def test_ids_are_reproducible(self) -> None:
        labels = ["agg2", "agg1", "agg3"]
        ids = selection.compute_anonymous_ids(labels, "t1", 3, "parallel")
        self.assertEqual(ids, selection.compute_anonymous_ids(list(reversed(labels)), "t1", 3, "parallel"))
        self.assertEqual(sorted(ids), ["A", "B", "C"])
        self.assertEqual(sorted(ids.values()), sorted(labels))

    def test_ids_count_like_spreadsheet_columns(self) -> None:
        self.assertEqual([selection.build_anonymous_id(i) for i in (0, 25, 26, 27)], ["A", "Z", "AA", "AB"])

    def test_candidates_carry_no_labels_or_trees(self) -> None:
        pool = selection.build_pool([_build_view(self.root, "agg1"), _build_view(self.root, "agg2")])
        found = selection.run_selection(self.build_request(), pool)
        files = fsops.list_files(self.root / "selection" / layout.CONTEXT_DIR)
        self.assertEqual(sorted(files), ["candidates/A.md", "candidates/B.md", "task.md"])
        self.assertFalse(found.fallback)
        self.assertEqual(dict(found.id_map)[found.chosen_id], found.chosen_label)

    def test_unknown_choice_falls_back_to_the_first_label(self) -> None:
        pool = selection.build_pool([_build_view(self.root, "agg2"), _build_view(self.root, "agg1")])
        found = selection.run_selection(self.build_request(behaviors=("select-bad",)), pool)
        self.assertTrue(found.fallback)
        self.assertEqual(found.chosen_label, "agg1")

    def test_k1_does_not_start_a_selector(self) -> None:
        log = self.root / "log.jsonl"
        request = self.build_request(log=log, k=1)
        found = selection.run_selection(request, selection.build_pool([_build_view(self.root, "agg1")]))
        self.assertEqual((found.chosen_label, found.chosen_id), ("agg1", "A"))
        self.assertEqual(support.read_log(log), [])

    def test_finals_without_deliverable_are_dropped(self) -> None:
        pool = selection.build_pool([_build_view(self.root, "agg1", delivered=False)])
        self.assertEqual(pool.dropped, ("agg1",))
        self.assertEqual(selection.run_selection(self.build_request(), pool).chosen_label, "")
