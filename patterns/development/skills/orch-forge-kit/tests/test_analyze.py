"""analyze のテスト。分析役のプロンプトと候補のバンドルを用意し、分析役の提案を検査することを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import analyze, bundle, contracts, fsops, layout
from forge_kit.errors import InvalidFileError, StageError
from tests import support


class AnalyzeTest(unittest.TestCase):
    def test_analyze(self) -> None:
        where = support.baseline_scored(self)
        out = analyze.analyze(where, 1)
        self.assertIn(f"job {contracts.AGENTS['analyst']} round-1 ", out)
        self.assertTrue(bundle.has_bundle(where.proposed_dir(1), support.SKILL))
        prompt = fsops.read_text(where.analyst_prompt_path(1))
        self.assertIn(str(where.copy_dir(layout.make_slot("baseline", 1), "T1-a1")), prompt)
        self.assertIn("| S4 | 受け渡しが足りない |", prompt)
        with self.assertRaises(StageError):
            analyze.analyze(where, 1)

    def test_analyze_refuses_when_must_met(self) -> None:
        where = support.baseline_scored(self, stream="delegated", met=True)
        with self.assertRaises(StageError):
            analyze.analyze(where, 1)

    def test_propose(self) -> None:
        where = support.baseline_scored(self)
        analyze.analyze(where, 1)
        support.act_analyst(where, 1)
        self.assertIn("変更 1 件、所見 0 件", analyze.propose(where, 1))
        text = fsops.read_text(where.proposal_md_path(1))
        self.assertIn("+" + support.ANALYST_LINE, text)
        self.assertIn("S4 受け渡しが足りない", text)

    def test_propose_rejects_unchanged_bundle(self) -> None:
        where = support.baseline_scored(self)
        analyze.analyze(where, 1)
        support.act_analyst(where, 1, line="")
        skill_md = bundle.skill_dir(where.proposed_dir(1), support.SKILL) / layout.SKILL_FILE
        fsops.write_text(skill_md, fsops.read_text(skill_md).rstrip("\n") + "\n")
        with self.assertRaises(InvalidFileError) as caught:
            analyze.propose(where, 1)
        self.assertIn("候補のバンドルが今のバンドルと同じです", caught.exception.message)

    def test_propose_rejects_copied_task_text(self) -> None:
        where = support.baseline_scored(self)
        analyze.analyze(where, 1)
        support.act_analyst(where, 1, line=f"- 「{support.TASK_PROMPT}」と言われたら inventory に置く")
        with self.assertRaises(InvalidFileError) as caught:
            analyze.propose(where, 1)
        self.assertIn("B12 ", caught.exception.message)


if __name__ == "__main__":
    unittest.main()
