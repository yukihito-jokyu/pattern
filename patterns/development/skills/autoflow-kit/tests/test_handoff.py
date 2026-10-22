"""handoff のテスト。"""

from __future__ import annotations

import dataclasses
import unittest

from autoflow_kit import deciding, fsops, handoff, policy, profile, trail, verifying
from autoflow_kit.errors import StageError
from tests import support

NOW = support.NOW


class HandoffTest(unittest.TestCase):
    def test_report_sections(self) -> None:
        where, run_id = support.handed_off(self)
        text = fsops.read_text(where.handoff_path(run_id, 1))
        for heading in (
            "## H3 で人がすること",
            "## 証拠（補助 CLI が実行した検査）",
            "## 検査が見ていないこと",
            "## 戻し方",
        ):
            self.assertIn(heading, text)
        self.assertIn("受け入れ条件 C2（review）", text)
        self.assertIn("リモートには送らない", text)
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.gate), (trail.DECIDE, policy.H3))

    def test_commit_after_approval(self) -> None:
        where, run_id = support.handed_off(self)
        deciding.decide(where, run_id, policy.H3, policy.APPROVE, "承認します", NOW)
        handoff.commit(where, run_id, NOW)
        self.assertEqual(support.git(where.root, "log", "-1", "--format=%s").strip(), "PROJ-1 掛け算の関数を足す")
        self.assertEqual(support.git(where.root, "status", "--porcelain").strip(), "")
        self.assertEqual(support.next_step(where, run_id).step, trail.DONE)

    def test_commit_requires_same_tree(self) -> None:
        where, run_id = support.handed_off(self)
        deciding.decide(where, run_id, policy.H3, policy.APPROVE, "承認します", NOW)
        support.write_files(where, {"README.md": "承認の後に変えた\n"})
        with self.assertRaisesRegex(StageError, "commit の番ではなく verify の番"):
            handoff.commit(where, run_id, NOW)

    def test_changes_go_back_to_build(self) -> None:
        where, run_id = support.handed_off(self)
        deciding.decide(where, run_id, policy.H3, policy.CHANGES, "README にも書いて", NOW)
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.reason), (trail.BUILD, trail.HUMAN))
        support.build(where, run_id, {"README.md": "# sample\n\nmultiply もある。\n"})
        self.assertIn("README にも書いて", fsops.read_text(where.build_prompt_path(run_id, 2)))
        verifying.verify(where, run_id, NOW)
        self.assertEqual(support.next_step(where, run_id).step, trail.REVIEW)

    def test_trailers(self) -> None:
        trailer = "Co-Authored-By: bot <bot@example.com>"
        settings = dataclasses.replace(profile.make_profile((support.UNIT,), ()), commit=profile.Commit((trailer,)))
        where, run_id = support.planned(self, settings=settings)
        support.build(where, run_id)
        verifying.verify(where, run_id, NOW)
        support.risk(where, run_id)
        support.review_round(where, run_id)
        handoff.handoff(where, run_id, NOW)
        message = support.events(where, run_id)[-1].text
        self.assertEqual(message, f"PROJ-1 掛け算の関数を足す\n\n{trailer}\n")
