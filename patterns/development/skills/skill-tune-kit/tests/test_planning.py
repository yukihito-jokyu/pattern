"""planning のテスト。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import layout


class PlanningTest(unittest.TestCase):
    def test_init_writes_skeleton(self) -> None:
        root = support.build_repo(self)
        support.run_ok(self, root, "init", "--skill", support.SKILL_PATH)
        data = support.read_json(support.build_where(root).plan_path)
        assert isinstance(data, dict)
        self.assertEqual(data["target"], {"id": support.TARGET, "skill_path": support.SKILL_PATH})
        code, _out, err = support.run_cli(root, "init", "--skill", support.SKILL_PATH)
        self.assertEqual(code, 1)
        self.assertIn("既に計画があります", err)

    def test_init_needs_skill_md(self) -> None:
        code, _out, err = support.run_cli(support.build_repo(self), "init", "--skill", "no/such")
        self.assertEqual(code, 1)
        self.assertIn("SKILL.md がありません", err)

    def test_check_plan_writes_split_and_plan_md(self) -> None:
        root = support.build_repo(self)
        where = support.write_dataset(root, support.build_plan(), support.build_cases(10))
        out = support.run_ok(self, root, "check-plan")
        self.assertIn("train 6 件、val 2 件、test 2 件", out)
        split = support.read_json(where.split_path)
        assert isinstance(split, dict)
        self.assertEqual(split["splits"], support.SPLITS)
        self.assertIn("## サブエージェントの起動回数の見積もり（上限）", where.plan_md_path.read_text(encoding="utf-8"))

    def test_few_cases_are_warned(self) -> None:
        root = support.build_repo(self)
        where = support.write_dataset(root, support.build_plan(), support.build_cases(3))
        support.run_ok(self, root, "check-plan")
        self.assertIn("ケースが 3 件です", where.plan_md_path.read_text(encoding="utf-8"))

    def test_group_missing_from_a_split_is_warned(self) -> None:
        root = support.build_repo(self)
        cases = [*support.build_cases(9), support.build_case("c10", group="rare")]
        where = support.write_dataset(root, support.build_plan(), cases)
        support.run_ok(self, root, "check-plan")
        text = where.plan_md_path.read_text(encoding="utf-8")
        self.assertIn("グループ rare のケースが", text)
        self.assertNotIn("グループ memo のケースが", text)

    def test_approve_needs_fresh_check_plan(self) -> None:
        root = support.build_repo(self)
        where = support.write_dataset(root, support.build_plan(), support.build_cases(10))
        support.run_ok(self, root, "check-plan")
        support.write_dataset(root, support.build_plan(max_rounds=5), support.build_cases(10))
        code, _out, err = support.run_cli(root, "approve")
        self.assertEqual(code, 1)
        self.assertIn("check-plan の後に計画が変わりました", err)
        self.assertFalse(where.version_dir(layout.FIRST_VERSION).exists())

    def test_approve_copies_skill_to_first_version(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        self.assertTrue((where.version_dir(layout.FIRST_VERSION) / "references" / "formats.md").is_file())
