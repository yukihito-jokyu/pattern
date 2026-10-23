"""rulemap（外部ツールの規則名 → ルールID）のテスト。"""

from __future__ import annotations

import unittest

from gha_kit import rulemap


class RuleForTest(unittest.TestCase):
    def test_maps_a_known_tool_rule(self) -> None:
        self.assertEqual(rulemap.rule_for("zizmor", "unpinned-uses", ""), "DEP-06")

    def test_maps_an_untrusted_expression_to_the_injection_rule(self) -> None:
        message = '"github.event.pull_request.title" is potentially untrusted'

        self.assertEqual(rulemap.rule_for("actionlint", "expression", message), "ERR-02")

    def test_falls_back_to_the_default_rule_of_the_tool(self) -> None:
        self.assertEqual(rulemap.rule_for("actionlint", "syntax-check", ""), "TEST-01")


if __name__ == "__main__":
    unittest.main()
