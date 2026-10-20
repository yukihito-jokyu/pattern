"""charter のテスト。charter-schema.md の例が検査を通り、項目どうしの決まりと承認のハッシュが働くことを確かめる。"""

from __future__ import annotations

import json
import re
import unittest

from forge_kit import charter, fsops
from forge_kit.errors import InvalidFileError
from tests import support

SCHEMA_MD = support.FIXTURES.parent.parent / "kit/claude/skills/forge-goals/references/charter-schema.md"


class CharterTest(unittest.TestCase):
    def test_schema_example(self) -> None:
        blocks = re.findall(r"```json\n(.*?)```", fsops.read_text(SCHEMA_MD), re.S)
        model = charter.parse(json.loads(blocks[0]), "example")
        self.assertEqual(model.target.skill_name, "dev-orch")

    def test_skeleton_needs_human_values(self) -> None:
        with self.assertRaises(InvalidFileError) as caught:
            charter.parse(charter.skeleton("dev-orch", "dev-orch"), "charter.json")
        self.assertIn("goals が空です", caught.exception.message)

    def test_skill_name(self) -> None:
        data = support.orch_charter("forge-x")
        with self.assertRaises(InvalidFileError) as caught:
            charter.parse(data, "charter.json")
        self.assertIn("forge- で始めないでください", caught.exception.message)

    def test_max_budget_usd(self) -> None:
        data = support.orch_charter()
        executor = data["executor"]
        assert isinstance(executor, dict)
        executor["max_budget_usd"] = 0
        with self.assertRaises(InvalidFileError):
            charter.parse(data, "charter.json")

    def test_relations(self) -> None:
        data = support.orch_charter()
        data["tasks"] = [{"id": "H1", "prompt": "在庫を空にして", "acceptance": []}]
        with self.assertRaises(InvalidFileError) as caught:
            charter.parse(data, "charter.json")
        self.assertIn("T<番号>", caught.exception.message)
        self.assertIn("acceptance が1件以上要ります", caught.exception.message)

    def test_grade_items(self) -> None:
        model = charter.parse(support.orch_charter(), "charter.json")
        keys = [key for key, _text in charter.grade_items(model, "T1", ("手順1", "手順2"))]
        self.assertEqual(keys, ["acceptance:1", "step:1", "step:2", "report"])
        self.assertTrue(charter.has_grader_items(model))

    def test_fragments(self) -> None:
        model = charter.parse(support.orch_charter(), "charter.json")
        self.assertEqual(charter.fragments(model, 20), frozenset({support.TASK_PROMPT}))
        self.assertIn("在庫を空にする関数がある", charter.fragments(model, 5))

    def test_approval_state(self) -> None:
        data = support.orch_charter()
        model = charter.parse(data, "charter.json")
        self.assertEqual(charter.approval_state(data, model), "unapproved")
        data["approval"] = {"sha256": charter.digest(data), "approved_on": support.TODAY}
        model = charter.parse(data, "charter.json")
        self.assertEqual(charter.approval_state(data, model), "approved")
        data["purpose"] = "変えた目的"
        self.assertEqual(charter.approval_state(data, charter.parse(data, "charter.json")), "stale")


if __name__ == "__main__":
    unittest.main()
