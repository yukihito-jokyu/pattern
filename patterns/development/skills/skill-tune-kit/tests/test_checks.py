"""checks のテスト。検査の種類ごとに test_kind_<種類> を置く（TEST-03）。"""

from __future__ import annotations

import unittest

from tune_kit import checks


class ChecksTest(unittest.TestCase):
    def test_kind_contains(self) -> None:
        self.assertTrue(checks.evaluate_text_check("contains", "日付は ２０２６-01-05 です", "2026-01-05", None).passed)
        self.assertFalse(checks.evaluate_text_check("contains", "日付なし", "2026-01-05", None).passed)

    def test_kind_not_contains(self) -> None:
        self.assertTrue(checks.evaluate_text_check("not_contains", "完了", "TODO", None).passed)
        self.assertFalse(checks.evaluate_text_check("not_contains", "TODO: 残り", "TODO", None).passed)

    def test_kind_regex(self) -> None:
        self.assertTrue(checks.evaluate_text_check("regex", "前置き\n## 概要\n", "^## 概要$", None).passed)
        self.assertFalse(checks.is_valid_pattern("("))

    def test_kind_equals(self) -> None:
        self.assertTrue(checks.evaluate_text_check("equals", "a  \r\nb\n\n", "", "a\nb").passed)
        self.assertFalse(checks.evaluate_text_check("equals", "a", "", "b").passed)
        self.assertFalse(checks.evaluate_text_check("equals", None, "", "a").passed)

    def test_kind_json_equals(self) -> None:
        self.assertTrue(checks.evaluate_text_check("json_equals", '{"b": 1, "a": [2]}', "", '{"a":[2],"b":1}').passed)
        self.assertFalse(checks.evaluate_text_check("json_equals", "{broken", "", "{}").passed)

    def test_kind_exists(self) -> None:
        self.assertTrue(checks.evaluate_exists(True).passed)
        self.assertFalse(checks.evaluate_exists(False).passed)

    def test_kind_command(self) -> None:
        self.assertTrue(checks.evaluate_command(0, "").passed)
        self.assertIn("終了コード 2", checks.evaluate_command(2, "失敗").detail)

    def test_kind_judge(self) -> None:
        kind = checks.KINDS["judge"]
        self.assertTrue(kind.judge)
        self.assertEqual(kind.required, ("criterion",))
        self.assertFalse(any(other.judge for name, other in checks.KINDS.items() if name != "judge"))
