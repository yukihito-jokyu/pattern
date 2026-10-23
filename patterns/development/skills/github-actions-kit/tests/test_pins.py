"""pins のテスト。git ls-remote の出力は固定の文字列にする。"""

from __future__ import annotations

import unittest

from gha_kit import pins

LS_REMOTE = "\n".join(
    [
        "1111111111111111111111111111111111111111\trefs/tags/v5",
        "2222222222222222222222222222222222222222\trefs/tags/v5.0.0",
        "3333333333333333333333333333333333333333\trefs/tags/v5.1.0",
        "4444444444444444444444444444444444444444\trefs/tags/v5.1.0^{}",
        "5555555555555555555555555555555555555555\trefs/tags/v6.0.0-beta.1",
    ]
)


def list_tags(repo: str) -> str:
    return LS_REMOTE if repo == "actions/checkout" else ""


class ResolveTest(unittest.TestCase):
    def test_picks_the_newest_stable_tag_and_its_peeled_sha(self) -> None:
        pin = pins.resolve("actions/checkout", list_tags)

        self.assertEqual(pin.uses(), "actions/checkout@4444444444444444444444444444444444444444 # v5.1.0")

    def test_keeps_the_subdirectory_of_the_action(self) -> None:
        pin = pins.resolve("actions/checkout/sub@v5.0.0", list_tags)

        self.assertEqual(pin.uses(), "actions/checkout/sub@2222222222222222222222222222222222222222 # v5.0.0")

    def test_rejects_a_major_only_tag(self) -> None:
        with self.assertRaises(ValueError):
            pins.resolve("actions/checkout@v5", list_tags)


class VerifyTest(unittest.TestCase):
    def test_reports_a_sha_that_does_not_match_the_commented_tag(self) -> None:
        lines = [
            "      - uses: actions/checkout@2222222222222222222222222222222222222222 # v5.0.0",
            "      - uses: actions/checkout@2222222222222222222222222222222222222222 # v5.1.0",
        ]

        mismatches = pins.verify({"ci.yml": lines}, list_tags)

        self.assertEqual([(m.line, m.spec) for m in mismatches], [(2, "actions/checkout")])


if __name__ == "__main__":
    unittest.main()
