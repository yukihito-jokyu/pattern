"""decide のテスト。"""

from __future__ import annotations

import unittest

from tests import support
from tune_kit import layout, workspace


class DecideTest(unittest.TestCase):
    def test_adopts_when_val_improves(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_until_learn(self, root)
        out = support.run_round(self, root, 1)
        self.assertIn("採用: 今の版は v1 になりました", out)
        decision = workspace.load_decisions(where)[0]
        self.assertEqual((decision.val_before, decision.val_after), (0.5, 1))
        compare = (where.round_dir(1) / layout.COMPARE_MD_FILE).read_text(encoding="utf-8")
        self.assertIn("| 検証用の合格率 | 50.0% | 100.0% |", compare)

    def test_no_change_is_rejected_without_evaluation(self) -> None:
        root = support.build_approved_repo(self)
        where = support.build_where(root)
        support.run_until_learn(self, root)
        support.write_proposal(where, 1, [], notes="直す点が見つからなかった")
        support.run_ok(self, root, "learn-check", "--round", "1")
        out = support.run_ok(self, root, "decide", "--round", "1")
        self.assertIn("不採用: 今の版は v0 のままです（学習役が変更を提案しなかった）", out)

    def test_decide_needs_the_current_round(self) -> None:
        root = support.build_approved_repo(self)
        code, _out, err = support.run_cli(root, "decide", "--round", "2")
        self.assertEqual(code, 1)
        self.assertIn("2 回目のラウンドは今のラウンドではありません", err)
