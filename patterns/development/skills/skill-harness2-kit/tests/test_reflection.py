"""reflection のテスト。"""

from __future__ import annotations

import unittest
from collections.abc import Sequence

from h2_kit import context, fsops, layout, reflection, skilltree
from tests import support


class ReflectionTest(unittest.TestCase):
    def run_with(self, behaviors: Sequence[str] = ()) -> tuple[reflection.Reflected, reflection.Request]:
        where = support.build_where(support.build_repo(self))
        base = support.read_skill(where)
        chosen = context.PoolEntry("agg1", skilltree.build_replaced(base, "references/x.md", "# x\n"), None)
        request = reflection.Request(
            model=support.build_model(behaviors=behaviors),
            prompt="依頼",
            source_dir=where.repo / "material",
            place=where.repo / "reflection",
            templates=where.templates_dir,
            views=(),
            chosen=chosen,
            base_tree=base,
            candidates=(chosen,),
            decisions=(("agg1", "kept -> x -> 1/1"),),
        )
        return reflection.run_reflection(request, "A", "理由", (("A", "agg1"),)), request

    def test_lesson_and_edits_are_kept(self) -> None:
        found, request = self.run_with()
        assert found.experience is not None
        self.assertEqual(found.experience.cue, "成果物の書き忘れ")
        self.assertIn("verdict: helped", fsops.read_text(request.place / layout.EDITS_FILE))
        adoption = fsops.read_json(request.place / layout.CONTEXT_DIR / layout.ADOPTION_FILE)
        self.assertEqual(
            adoption, {"chosen_label": "agg1", "chosen_id": "A", "candidate_ids": {"A": "agg1"}, "reason": "理由"}
        )
        self.assertTrue((request.place / layout.CONTEXT_DIR / layout.BASE_HARNESS_DIR / "SKILL.md").is_file())

    def test_no_entry_is_declined(self) -> None:
        found, _ = self.run_with(("no-entry",))
        self.assertTrue(found.declined)
        self.assertIsNone(found.experience)

    def test_failed_session_writes_no_lesson(self) -> None:
        found, _ = self.run_with(("fail-reflect",))
        self.assertIsNone(found.experience)
        self.assertTrue(found.error)
