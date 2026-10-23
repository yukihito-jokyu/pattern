"""contracts のテスト。サブエージェントが書く JSON の検証を確かめる（ERR-02）。"""

from __future__ import annotations

import unittest
from fractions import Fraction

from tests import support
from tune_kit import contracts, plan


def build_originals() -> dict[str, plan.Case]:
    case = plan.parse_case(support.build_case("c01"), "c")[0]
    assert case is not None
    return {"c01": case}


class ContractsTest(unittest.TestCase):
    def test_grades_need_every_judge_once(self) -> None:
        data = {
            "grades": [
                {"check_id": "Q1", "passed": True, "reason": "根拠"},
                {"check_id": "Q9", "passed": False, "reason": "x"},
            ]
        }
        problems = contracts.parse_grades(data, ["Q1", "Q2"])[1]
        self.assertIn("grade.json に検査 Q2 の判定がありません", problems)
        self.assertIn("grade.json の Q9 は採点する検査ではありません", problems)

    def test_proposal_cases_are_train_only(self) -> None:
        data = {"changes": [{"file": "SKILL.md", "summary": "s", "cause": "c", "cases": ["c03"]}], "notes": ""}
        problems = contracts.parse_proposal(data, ["c01"])[1]
        self.assertIn("proposal.json.changes[0].cases の c03 は学習用のケースではありません", problems)

    def test_audit_fix_follows_cause(self) -> None:
        skill_fix = support.build_finding(1, "c01", "skill", {"case": support.build_case("c01")})
        expected_without_fix = support.build_finding(2, "c01", "expected")
        problems = contracts.parse_audit(
            {"findings": [skill_fix, expected_without_fix]}, build_originals(), [], allow_fix=True
        )[1]
        self.assertTrue(any("findings[0].fix は null" in problem for problem in problems))
        self.assertTrue(any("findings[1].fix がありません" in problem for problem in problems))

    def test_audit_fix_keeps_case_identity(self) -> None:
        moved = support.build_finding(1, "c01", "expected", {"case": support.build_case("c01", group="other")})
        problems = contracts.parse_audit({"findings": [moved]}, build_originals(), [], allow_fix=True)[1]
        self.assertTrue(any("id・group は元のケースと同じ" in problem for problem in problems))

    def test_audit_fix_keeps_original_split(self) -> None:
        echoed = support.build_finding(1, "c01", "expected", {"case": support.build_case("c01", split=plan.TRAIN)})
        audit, problems = contracts.parse_audit({"findings": [echoed]}, build_originals(), [], allow_fix=True)
        self.assertEqual(problems, [])
        self.assertEqual([finding.fix_case.split for finding in audit.findings if finding.fix_case], [""])

    def test_audit_covers_each_failing_case(self) -> None:
        problems = contracts.parse_audit({"findings": []}, build_originals(), [], allow_fix=False)[1]
        self.assertIn("audit.json にケース c01 の指摘がありません（不合格のケースごとに1件以上）", problems)

    def test_decision_round_trips(self) -> None:
        record = contracts.DecisionRecord(
            1, "v0", "v1", True, "理由", Fraction(1, 2), Fraction(1), None, Fraction(2, 3)
        )
        self.assertEqual(contracts.parse_decision(contracts.build_decision_data(record)), (record, []))
