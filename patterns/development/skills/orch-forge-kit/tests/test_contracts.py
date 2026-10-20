"""contracts のテスト。サブエージェントが書く JSON の検証と、補助 CLI が書く JSON の読み戻しを確かめる。"""

from __future__ import annotations

import json
import unittest

from forge_kit import contracts
from forge_kit.errors import InvalidFileError


class ContractsTest(unittest.TestCase):
    def test_parse_grade(self) -> None:
        data = {"run_id": "T1-a1", "items": [{"key": "report", "met": True, "evidence": "返答の順"}]}
        grade = contracts.parse_grade(data, "grade.json", run_id="T1-a1", keys=("report",))
        self.assertTrue(grade.items[0].met)
        with self.assertRaises(InvalidFileError) as caught:
            contracts.parse_grade(data, "grade.json", run_id="T1-a1", keys=("acceptance:1", "report"))
        self.assertIn("items の key は次の順で全部書いてください", caught.exception.message)

    def test_parse_proposal(self) -> None:
        change = {"id": "P1", "cause": "S6", "metrics": ["delegation"], "evidence": ["x"], "summary": "y"}
        with self.assertRaises(InvalidFileError):
            contracts.parse_proposal({"changes": [change], "observations": []}, "p", metric_ids=("delegation",))
        change["cause"] = "S2"
        proposal = contracts.parse_proposal({"changes": [change], "observations": []}, "p", metric_ids=("delegation",))
        self.assertEqual(proposal.changes[0].cause, "S2")
        with self.assertRaises(InvalidFileError):
            contracts.parse_proposal({"changes": [change], "observations": []}, "p", metric_ids=("acceptance",))

    def test_parse_plan(self) -> None:
        run = contracts.Run("T1-a1", "T1", 1)
        plan = contracts.Plan("round-1-baseline", "baseline", 1, "0" * 64, "dev-orch", "/b", (run,))
        data = json.loads(json.dumps(contracts.to_data(plan)))
        self.assertEqual(contracts.parse_plan(data, "plan.json"), plan)

    def test_causes_split(self) -> None:
        self.assertEqual(set(contracts.CAUSES), {*contracts.BUNDLE_CAUSES, *contracts.OBSERVATION_CAUSES})


if __name__ == "__main__":
    unittest.main()
