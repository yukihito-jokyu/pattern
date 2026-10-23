"""errors のテスト。"""

from __future__ import annotations

import unittest

from tune_kit import errors


class ErrorsTest(unittest.TestCase):
    def test_invalid_file_error_lists_all_problems(self) -> None:
        error = errors.InvalidFileError("plan.json", ["goal が空です", "mode が空です"])
        self.assertIn("2 件の問題", error.message)
        self.assertIn("  - mode が空です", error.message)
        self.assertEqual(error.problems, ("goal が空です", "mode が空です"))

    def test_stage_error_is_kit_error(self) -> None:
        self.assertIsInstance(errors.StageError("段階が違います"), errors.KitError)
