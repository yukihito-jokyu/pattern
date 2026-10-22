"""contracts のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import contracts, policy, shape
from tests import support

KINDS = tuple(kind.name for kind in policy.KINDS)


class ContractsTest(unittest.TestCase):
    def test_plan_parses(self) -> None:
        problems: list[str] = []
        plan = contracts.parse_plan(support.feature_plan(), KINDS, problems)
        self.assertEqual(problems, [])
        self.assertEqual([item.id for item in plan.criteria], ["C1", "C2"])

    def test_plan_problems(self) -> None:
        criteria = [
            {"id": "C1", "text": "動く", "check": "command", "run": ""},
            {"id": "C1", "text": "読める", "check": "review", "run": "make"},
        ]
        plan = support.feature_plan(criteria=criteria, scope=[], commit_subject="一行目\n二行目")
        problems: list[str] = []
        contracts.parse_plan(plan, KINDS, problems)
        expected = [
            "commit_subject は1行にする",
            "scope が空です。1つ以上書く",
            "criteria[0].run が空です。check が command なら、確かめるコマンドを書く",
            "criteria[1].run は check が command のときだけ書く",
            "criteria の id 'C1' が重なっています",
        ]
        self.assertEqual(problems, expected)

    def test_report_declined_needs_reason(self) -> None:
        report = {
            "summary": "直した",
            "explanation": "説明",
            "resolutions": [{"finding_id": "R1-1", "status": "declined", "reason": " ", "locations": []}],
            "blockers": [],
        }
        problems: list[str] = []
        contracts.parse_report(report, problems)
        self.assertEqual(problems, ["resolutions[0].reason が空です。退けるなら理由を書く"])

    def test_findings_category(self) -> None:
        problems: list[str] = []
        contracts.parse_findings({"findings": [support.finding(category="style")]}, policy.REVIEW.categories, problems)
        self.assertEqual(len(problems), 1)
        self.assertIn("bug, security, criteria, fit", problems[0])

    def test_votes_one_per_candidate(self) -> None:
        vote = {"id": "R1-1", "verdict": "real", "tag": "important", "reason": "確かめた"}
        problems: list[str] = []
        contracts.parse_votes(
            {"votes": [vote, vote, {**vote, "id": "R1-9"}]}, ("R1-1", "R1-2"), policy.REVIEW.tags, problems
        )
        self.assertEqual(
            problems,
            [
                "候補 R1-2 への票がありません",
                "候補に無い id R1-9 への票があります",
                "候補 R1-1 への票が2つ以上あります",
            ],
        )

    def test_judgment_needs_reasons(self) -> None:
        problems: list[str] = []
        judgment = {"tier": "low", "human_required": False, "reasons": [], "attention_files": []}
        contracts.parse_judgment(judgment, ("low", "medium", "high"), problems)
        self.assertEqual(problems, ["reasons が空です。段を選んだ理由を1つ以上書く"])

    def test_round_trip(self) -> None:
        finding = contracts.parse_findings({"findings": [support.finding()]}, policy.REVIEW.categories, [])[0]
        result = contracts.ReviewResult(
            1, "t", "b", "quick", (contracts.Kept("R1-1", "nit", 2, 2, ("intent",), finding),), ()
        )
        problems: list[str] = []
        self.assertEqual(contracts.parse_result(shape.to_data(result), policy.REVIEW.categories, problems), result)
        evidence = contracts.Evidence(
            1, "t", "check", True, (contracts.CheckResult("unit", "make", 0, False, "1.log"),)
        )
        self.assertEqual(contracts.parse_evidence(shape.to_data(evidence), problems), evidence)
        self.assertEqual(problems, [])
