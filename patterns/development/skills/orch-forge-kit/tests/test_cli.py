"""cli のテスト。実行役とサブエージェントの出力を代わりに書きながら、構築と評価の全体の流れを CLI で通す。"""

from __future__ import annotations

import unittest

from forge_kit import bundle, collect, execute, fsops, layout, status
from tests import support


class CliTest(unittest.TestCase):
    def test_error_goes_to_stderr_with_exit_code_one(self) -> None:
        root = support.make_repo(self)
        code, out, err = support.run_cli(root, "charter-check", "--target", support.SKILL)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("エラー: ", err)

    def test_targets(self) -> None:
        root = support.make_repo(self)
        code, out, _err = support.run_cli(root, "targets")
        self.assertEqual(code, 0)
        self.assertIn("| dev-orch |", out)

    def test_build_flow(self) -> None:
        where = support.approved_layout(self, support.orch_charter(support.NEW_SKILL))
        target = ("--target", support.NEW_SKILL)
        self.assert_status(where, "design-new")
        self.cli(where, "design-new", *target)
        self.assert_status(where, "job forge-designer design")
        support.act_designer(where)
        self.cli(where, "design-check", *target)
        self.assert_status(
            where, "直すなら: python3 .forge/forge.py design-new --target new-orch --feedback '<直してほしいこと>'"
        )
        self.cli(where, "design-approve", *target)
        self.assert_status(where, "build --target new-orch")
        self.cli(where, "build", *target)
        self.assert_status(where, "job forge-builder build")
        code, _out, err = support.run_cli(where.root, "bundle-check", *target)
        self.assertEqual(code, 1)
        self.assertIn("構築役に、この問題を直すよう添えて", err)
        support.act_builder(where)
        self.cli(where, "bundle-check", *target)
        self.assert_status(where, "承認なら: python3 .forge/forge.py install --target new-orch")
        self.cli(where, "install", *target)
        self.assertTrue(bundle.has_bundle(where.claude_dir, support.NEW_SKILL))
        self.assert_status(where, "（forge-run）")

    def test_run_flow_from_baseline_to_report(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        target = ("--target", support.SKILL)
        baseline = ("--variant", "baseline", "--round", "1")
        self.assert_status(where, "prepare --target dev-orch --variant baseline --round 1")
        self.cli(where, "prepare", *target, *baseline)
        self.assert_status(where, "execute --target dev-orch --variant baseline --round 1")
        self.evaluate(where, layout.make_slot("baseline", 1), stream="main-edit", met=False)
        self.assert_status(where, "analyze --target dev-orch --round 1")

        self.cli(where, "analyze", *target, "--round", "1")
        self.assert_status(where, "job forge-analyst round-1")
        support.act_analyst(where, 1)
        self.cli(where, "propose", *target, "--round", "1")
        candidate = ("--variant", "candidate", "--round", "1")
        self.assert_status(where, "prepare --target dev-orch --variant candidate --round 1")
        self.cli(where, "prepare", *target, *candidate)
        self.evaluate(where, layout.make_slot("candidate", 1), stream="delegated", met=True)
        self.assert_status(where, "compare --target dev-orch --round 1")
        _code, out, _err = support.run_cli(where.root, "compare", *target, "--round", "1")
        self.assertIn("推奨: 採用", out)
        self.assert_status(where, "採用なら: python3 .forge/forge.py decide --target dev-orch --round 1 --adopt")
        self.cli(where, "decide", *target, "--round", "1", "--adopt")
        skill_md = bundle.skill_dir(where.claude_dir, support.SKILL) / layout.SKILL_FILE
        self.assertIn(support.ANALYST_LINE, fsops.read_text(skill_md))

        self.assert_status(where, "prepare --target dev-orch --variant final")
        self.cli(where, "prepare", *target, "--variant", "final")
        self.evaluate(where, layout.make_slot("final", 0), stream="delegated", met=True)
        self.assert_status(where, "report --target dev-orch")
        self.cli(where, "report", *target)
        self.assertIn("ホールドアウト", fsops.read_text(where.report_path))
        self.assert_status(where, "段階: 完了")

    def evaluate(self, where: layout.Layout, slot: layout.Slot, *, stream: str, met: bool) -> None:
        """execute と collect は実行役の代わりを使って呼び、採点役の代わりに書いてから score を CLI で呼ぶ。"""
        execute.execute(where, slot, support.fake_launcher(stream=stream))
        self.assert_status(where, "collect --target")
        out = collect.collect(where, slot, parallel=1)
        self.assertIn("job forge-grader", out)
        self.assert_status(where, "job forge-grader")
        support.grade_all(where, slot, met=met)
        args = ["--variant", slot.variant] + ([] if slot.variant == "final" else ["--round", str(slot.round_no)])
        self.cli(where, "score", "--target", where.target, *args)

    def cli(self, where: layout.Layout, *args: str) -> str:
        code, out, err = support.run_cli(where.root, *args)
        self.assertEqual(code, 0, err)
        self.assertIn(f"次: {status.CLI} status --target {where.target}", out)
        return out

    def assert_status(self, where: layout.Layout, expected: str) -> None:
        code, out, _err = support.run_cli(where.root, "status", "--target", where.target)
        self.assertEqual(code, 0)
        self.assertIn(expected, out)
        for line in out.splitlines():
            self.assertTrue(line.startswith(status.LINE_KINDS), line)


if __name__ == "__main__":
    unittest.main()
