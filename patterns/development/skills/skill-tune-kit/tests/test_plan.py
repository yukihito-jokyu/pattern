"""plan のテスト。計画とケースの検証を確かめる（PROC-06）。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import plan


class PlanTest(unittest.TestCase):
    def test_skeleton_needs_goal_and_mode(self) -> None:
        model, problems = plan.parse_plan(plan.build_skeleton("sample", support.SKILL_PATH))
        self.assertIsNone(model)
        self.assertTrue(any("goal" in problem for problem in problems))
        self.assertTrue(any("mode" in problem for problem in problems))

    def test_other_schema_version_is_a_problem(self) -> None:
        data = support.build_plan()
        data["schema_version"] = plan.SCHEMA_VERSION + 1
        problems = plan.parse_plan(data)[1]
        self.assertTrue(any("schema_version" in problem for problem in problems))

    def test_check_needs_fields_of_its_kind(self) -> None:
        problems = plan.parse_check({"id": "K1", "kind": "regex", "severity": "must", "value": "x"}, "c")[1]
        self.assertIn("c.pattern が空です（kind regex に必須）", problems)
        self.assertIn("c.value は kind regex では使えません", problems)

    def test_reference_case_needs_expected(self) -> None:
        model, _problems = plan.parse_plan(support.build_plan())
        cases = plan.parse_cases({"cases": [support.build_case("c01", expected=None)]})[0]
        assert model is not None
        self.assertIn("ケース c01: reference モードでは expected（正解）が要ります", plan.check_dataset(model, cases))

    def test_case_data_round_trips(self) -> None:
        source = support.build_case("c01", checks=[support.build_check("K9", "contains", value="x")], note="メモ")
        case = plan.parse_case(source, "c")[0]
        assert case is not None
        self.assertEqual(plan.parse_case(plan.build_case_data(case), "c")[0], case)

    def test_plan_checks_apply_by_group(self) -> None:
        data = support.build_plan(checks=[support.build_check("K1", "equals", groups=["mail"])])
        model = plan.parse_plan(data)[0]
        memo = plan.parse_case(support.build_case("c01", group="memo"), "c")[0]
        assert model is not None and memo is not None
        self.assertEqual(plan.list_case_checks(model, memo), ())
