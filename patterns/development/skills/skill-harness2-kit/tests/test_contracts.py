"""contracts のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import contracts


class ContractsTest(unittest.TestCase):
    def test_notes_reads_the_last_block(self) -> None:
        text = "<notes>\n古い\n</notes>\n本文\n<notes>\n新しい\n</notes>"
        self.assertEqual(contracts.parse_notes(text), "新しい")

    def test_notes_without_tags_is_the_whole_reply(self) -> None:
        self.assertEqual(contracts.parse_notes("  KEEP_BASE  "), "KEEP_BASE")
        self.assertTrue(contracts.is_keep_base("KEEP_BASE: 分かれ目が無い"))

    def test_decisions_read_each_line(self) -> None:
        notes = "kept -> inv1 の確かめ -> base 2/2 で答えが無い\ndropped -> dom1 の例 -> 1/2 だけ"
        found = contracts.parse_decisions(notes)
        self.assertEqual([item.kind for item in found], ["kept", "dropped"])
        self.assertEqual(found[0].evidence, "base 2/2 で答えが無い")

    def test_choice_reads_id_and_why(self) -> None:
        text = "<why>\n" + "\n".join(f"理由{i}" for i in range(8)) + "\n</why>\n```choice\nB\n```"
        choice, problem = contracts.parse_choice(text, ["A", "B"])
        self.assertEqual(problem, "")
        assert choice is not None
        self.assertEqual(choice.chosen_id, "B")
        self.assertEqual(len(choice.why.splitlines()), contracts.WHY_MAX_LINES)

    def test_choice_rejects_unknown_id_and_missing_fence(self) -> None:
        self.assertIsNone(contracts.parse_choice("```choice\nZ\n```", ["A"])[0])
        self.assertIsNone(contracts.parse_choice("A", ["A"])[0])

    def test_reflection_reads_experience(self) -> None:
        text = "<edits>\nverdict: helped\n</edits>\n<experience>\ncue: c\nlesson: l\nevidence: e\n</experience>"
        found = contracts.parse_reflection(text)
        assert found.experience is not None
        self.assertEqual(found.experience.lesson, "l")
        self.assertEqual(contracts.list_verdicts(found.edits), ["helped"])

    def test_reflection_without_lesson_fields_has_no_experience(self) -> None:
        self.assertIsNone(contracts.parse_reflection("<experience>\ncue: c\n</experience>").experience)
        self.assertTrue(contracts.parse_reflection("<edits>\nx\n</edits>\nNO_ENTRY").declined)
