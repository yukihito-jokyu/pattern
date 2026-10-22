"""profile のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import profile, shape
from tests import support


def default_data() -> dict[str, object]:
    return shape.to_data(profile.make_profile((support.UNIT,), ("REVIEW.md",)))


class ProfileTest(unittest.TestCase):
    def test_default_parses(self) -> None:
        problems: list[str] = []
        settings = profile.parse(default_data(), problems)
        self.assertEqual(problems, [])
        self.assertEqual(settings.verify.commands, (support.UNIT,))
        self.assertEqual(settings.review.guide_files, ("REVIEW.md",))
        self.assertIn(".claude/**", settings.risk.always_human)

    def test_old_schema_version(self) -> None:
        data = default_data()
        data["schema_version"] = 0
        problems: list[str] = []
        profile.parse(data, problems)
        self.assertTrue(any("setup-new --force" in problem for problem in problems))

    def test_commands_required_and_unique(self) -> None:
        data = default_data()
        data["verify"] = {"commands": []}
        problems: list[str] = []
        profile.parse(data, problems)
        self.assertTrue(any("verify.commands が空です" in problem for problem in problems))
        command = {"id": "unit", "run": "make test", "timeout_sec": 10}
        data["verify"] = {"commands": [command, command]}
        problems = []
        profile.parse(data, problems)
        self.assertTrue(any("重なっています" in problem for problem in problems))

    def test_command_shape(self) -> None:
        data = default_data()
        data["verify"] = {"commands": [{"id": "Unit Test", "run": " ", "timeout_sec": 0}]}
        problems: list[str] = []
        profile.parse(data, problems)
        self.assertEqual(len(problems), 3)

    def test_limits_order(self) -> None:
        data = default_data()
        limits = dict(shape.to_data(profile.DEFAULT_LIMITS))
        limits["large_diff_lines"] = 2000
        data["limits"] = limits
        problems: list[str] = []
        profile.parse(data, problems)
        self.assertEqual(problems, ["limits.large_diff_lines は limits.huge_diff_lines 以下にする"])

    def test_unknown_key(self) -> None:
        data = default_data()
        data["extra"] = 1
        problems: list[str] = []
        profile.parse(data, problems)
        self.assertEqual(problems, ["全体 に知らないキーがあります: extra"])

    def test_approval(self) -> None:
        problems: list[str] = []
        approval = {"sha256": profile.digest("x"), "who": "", "answer": "承認", "at": support.NOW}
        self.assertEqual(profile.parse_approval(approval, problems).answer, "承認")
        self.assertEqual(problems, [])
        profile.parse_approval({**approval, "sha256": "abc", "answer": ""}, problems)
        self.assertEqual(len(problems), 2)

    def test_fields_cover_profile(self) -> None:
        keys = {field.key.split(".")[0].split("[")[0] for field in profile.FIELDS}
        self.assertEqual(keys, set(default_data()))
