"""shape のテスト。JSON の形の検証の部品が、問題を集めることを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import shape


class ShapeTest(unittest.TestCase):
    def test_collects_problems(self) -> None:
        problems: list[str] = []
        data = shape.as_object({"a": 1, "x": True}, "", problems)
        shape.unknown_keys(data, ("a", "b"), "", problems)
        self.assertEqual(shape.text(data, "a", "", problems), "")
        shape.integer(data, "b", "", problems, bounds=(1, 2))
        self.assertEqual(len(problems), 3)

    def test_texts_and_duplicates(self) -> None:
        problems: list[str] = []
        self.assertEqual(shape.texts({"k": ["a", "b"]}, "k", "", problems), ("a", "b"))
        self.assertEqual(problems, [])
        self.assertEqual(shape.duplicates(["a", "b", "a"]), ["a"])


if __name__ == "__main__":
    unittest.main()
