"""status のテスト。出力の全行が決まった書き出しで始まることを確かめる（OPS-01）。"""

from __future__ import annotations

import unittest

from autoflow_kit import contracts, deciding, handoff, planning, policy, reviewing, status, verifying
from autoflow_kit.layout import Layout
from tests import support

NOW = support.NOW


class StatusTest(unittest.TestCase):
    def lines(self, where: Layout, run_id: str = "") -> list[str]:
        text = status.status(where, run_id)
        for line in text.splitlines():
            self.assertTrue(line.startswith(status.LINE_KINDS), f"決まった書き出しで始まらない行: {line}")
        return text.splitlines()

    def test_verify_and_plan(self) -> None:
        where, run_id = support.started(self)
        lines = self.lines(where)
        self.assertEqual(lines[0], f"対象: {run_id}（掛け算を足す）ブランチ autoflow/{run_id}")
        self.assertEqual(lines[-1], f"次: python3 .autoflow/autoflow.py verify --run {run_id}")
        verifying.verify(where, run_id, NOW)
        self.assertEqual(self.lines(where, run_id)[-1], f"次: python3 .autoflow/autoflow.py plan-new --run {run_id}")
        planning.plan_new(where, run_id, NOW)
        lines = self.lines(where, run_id)
        prompt = where.relative(where.plan_prompt_path(run_id, 1))
        self.assertEqual(
            lines[2:],
            [
                status.LAUNCH,
                f"job autoflow-planner planner-1 {prompt}",
                f"その後: python3 .autoflow/autoflow.py plan-check --run {run_id}",
            ],
        )

    def test_review_jobs(self) -> None:
        where, run_id = support.risked(self)
        reviewing.review_new(where, run_id, NOW)
        jobs = [line for line in self.lines(where, run_id) if line.startswith("job ")]
        lenses = policy.depth_of(policy.MEDIUM).lenses
        self.assertEqual([line.split()[2] for line in jobs], [f"{lens}-r1" for lens in lenses])
        support.act_finders(where, run_id, {"correctness": [support.finding()]})
        reviewing.review_collect(where, run_id, NOW)
        jobs = [line for line in self.lines(where, run_id) if line.startswith("job ")]
        self.assertEqual(
            [line.split()[1:3] for line in jobs],
            [[contracts.AGENTS["verifier"], f"verifier-{k}-r1"] for k in (1, 2, 3)],
        )

    def test_gate_lines(self) -> None:
        where, run_id = support.handed_off(self)
        lines = self.lines(where, run_id)
        self.assertTrue(lines[2].startswith(f"人: {where.relative(where.handoff_path(run_id, 1))} を人に見せ"))
        choices = [line for line in lines if line.startswith("選択:")]
        self.assertEqual(len(choices), len(policy.gate_of(policy.H3).options))
        self.assertIn("--gate H3 --choice approve --answer '<人の回答の原文>'", choices[0])

    def test_end_lines(self) -> None:
        where, run_id = support.handed_off(self)
        deciding.decide(where, run_id, policy.H3, policy.APPROVE, "承認します", NOW)
        handoff.commit(where, run_id, NOW)
        self.assertTrue(self.lines(where, run_id)[-1].startswith("終了: 作業ブランチ"))

    def test_stopped(self) -> None:
        where, run_id = support.planned(self, support.feature_plan(dependencies_to_add=["numpy"]))
        deciding.decide(where, run_id, policy.H1, policy.ABORT, "やめます", NOW)
        self.assertTrue(self.lines(where, run_id)[-1].startswith("終了: 止めた（人が止めた）"))
