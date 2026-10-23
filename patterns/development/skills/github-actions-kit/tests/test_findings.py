"""findings（指摘の型と出力の形）のテスト。"""

from __future__ import annotations

import unittest

from gha_kit.findings import Finding, counts


class FindingTest(unittest.TestCase):
    def test_renders_rule_path_line_and_message(self) -> None:
        finding = Finding(".github/workflows/ci.yml", 12, "DEP-06", "SHA で固定する")

        self.assertEqual(finding.render(), "DEP-06 .github/workflows/ci.yml:12 SHA で固定する")

    def test_counts_findings_per_path_and_rule(self) -> None:
        findings = [
            Finding("a.yml", 1, "NAM-06", "x"),
            Finding("a.yml", 9, "NAM-06", "y"),
            Finding("b.yml", 1, "NAM-06", "z"),
        ]

        self.assertEqual(counts(findings), {("a.yml", "NAM-06"): 2, ("b.yml", "NAM-06"): 1})


if __name__ == "__main__":
    unittest.main()
