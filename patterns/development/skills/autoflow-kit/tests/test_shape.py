"""shape のテスト。"""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from autoflow_kit import shape


@dataclass(frozen=True)
class Pair:
    left: str
    right: tuple[str, ...]


class ShapeTest(unittest.TestCase):
    def test_text_checks_pattern(self) -> None:
        problems: list[str] = []
        self.assertEqual(shape.text({"id": "c1"}, "id", "plan", problems, pattern=r"C[0-9]+"), "c1")
        self.assertIn("plan.id の形が違います", problems[0])

    def test_filled_rejects_blank(self) -> None:
        problems: list[str] = []
        shape.filled({"goal": "  "}, "goal", "", problems)
        self.assertEqual(problems, ["goal が空です"])

    def test_integer_rejects_bool_and_bounds(self) -> None:
        problems: list[str] = []
        shape.integer({"n": True}, "n", "", problems, bounds=(1, 3))
        shape.integer({"n": 4}, "n", "", problems, bounds=(1, 3))
        self.assertEqual(len(problems), 2)

    def test_choice_lists_options(self) -> None:
        problems: list[str] = []
        shape.choice({"tier": "huge"}, "tier", ("low", "high"), "", problems)
        self.assertIn("low, high", problems[0])

    def test_texts_rejects_blank_item(self) -> None:
        problems: list[str] = []
        self.assertEqual(shape.texts({"scope": ["a", " "]}, "scope", "", problems), ("a", " "))
        self.assertEqual(problems, ["scope[1] が空です"])

    def test_objects_gives_paths(self) -> None:
        problems: list[str] = []
        found = shape.objects({"items": [{"a": 1}, 2]}, "items", "root", problems)
        self.assertEqual([path for path, _item in found], ["root.items[0]", "root.items[1]"])
        self.assertEqual(problems, ["root.items[1] はオブジェクトにしてください"])

    def test_unknown_keys(self) -> None:
        problems: list[str] = []
        shape.unknown_keys({"a": 1, "b": 2}, ("a",), "", problems)
        self.assertEqual(problems, ["全体 に知らないキーがあります: b"])

    def test_duplicates_once_each(self) -> None:
        self.assertEqual(shape.duplicates(["a", "b", "a", "a", "b"]), ["a", "b"])

    def test_to_data_uses_field_names(self) -> None:
        self.assertEqual(shape.to_data(Pair("x", ("y",))), {"left": "x", "right": ["y"]})
