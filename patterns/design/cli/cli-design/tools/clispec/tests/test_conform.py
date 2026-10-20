"""見本の実装に適合テストをかける（TEST-01）。失敗した項目はルールID付きで表示する。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import conform
import model

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ConformTest(unittest.TestCase):
    def assert_conforms(self, name: str, impl: str) -> None:
        spec = model.load(ROOT / "specs" / name / "released" / "1.0.0.json")
        results = conform.run(spec, [sys.executable, str(FIXTURES / impl)])
        self.assertEqual(results[:-1], [], "\n" + "\n".join(results))

    def test_notes(self) -> None:
        self.assert_conforms("notes", "notes_impl.py")

    def test_count_words(self) -> None:
        self.assert_conforms("count-words", "count_words_impl.py")


if __name__ == "__main__":
    unittest.main()
