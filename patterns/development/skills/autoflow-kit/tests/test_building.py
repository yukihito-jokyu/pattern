"""building のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import building, fsops, policy, trail, verifying
from autoflow_kit.errors import InvalidFileError, StageError
from tests import support

NOW = support.NOW
BROKEN = {"calc.py": "def multiply(a: int, b: int) -> int:\n    return a + b\n"}


class BuildingTest(unittest.TestCase):
    def test_build_new_prompt(self) -> None:
        where, run_id = support.planned(self)
        building.build_new(where, run_id, NOW)
        prompt = fsops.read_text(where.build_prompt_path(run_id, 1))
        self.assertIn(trail.FIRST, prompt)
        self.assertIn(where.relative(where.report_path(run_id, 1)), prompt)
        self.assertIn("`tests/**`", prompt)

    def test_check_needs_prompt(self) -> None:
        where, run_id = support.planned(self)
        with self.assertRaisesRegex(StageError, "build-new"):
            building.build_check(where, run_id, NOW)

    def test_failures_go_to_next_prompt(self) -> None:
        where, run_id = support.planned(self)
        support.build(where, run_id, BROKEN)
        verifying.verify(where, run_id, NOW)
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.reason), (trail.BUILD, trail.FAILED))
        building.build_new(where, run_id, NOW)
        prompt = fsops.read_text(where.build_prompt_path(run_id, 2))
        self.assertIn("unit: 終了コード 1", prompt)

    def test_findings_must_be_answered(self) -> None:
        where, run_id = support.risked(self)
        support.review_round(where, run_id, {"correctness": [support.finding()]})
        building.build_new(where, run_id, NOW)
        self.assertIn("R1-1 [Important]", fsops.read_text(where.build_prompt_path(run_id, 2)))
        support.act_builder(where, run_id)
        with self.assertRaisesRegex(InvalidFileError, "R1-1 への回答"):
            building.build_check(where, run_id, NOW)
        answer = {"finding_id": "R1-1", "status": "fixed", "reason": "", "locations": ["calc.py:14"]}
        support.act_builder(where, run_id, resolutions=[answer])
        building.build_check(where, run_id, NOW)
        self.assertEqual(support.events(where, run_id)[-1].kind, trail.BUILT)

    def test_repro_build_only_touches_tests(self) -> None:
        where, run_id = support.planned(self, support.fix_plan())
        building.build_new(where, run_id, NOW)
        support.act_builder(where, run_id, {"calc.py": "x = 1\n"})
        with self.assertRaisesRegex(InvalidFileError, "paths.tests のパスだけ"):
            building.build_check(where, run_id, NOW)

    def test_blockers_escalate(self) -> None:
        where, run_id = support.planned(self)
        support.build(where, run_id, {}, blockers=["検査に要る鍵が無い"])
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.gate), (trail.DECIDE, policy.H2))
        self.assertIn("検査に要る鍵が無い", fsops.read_text(where.gate_path(run_id, policy.H2, 1)))
