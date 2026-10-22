"""reviewing のテスト。"""

from __future__ import annotations

import unittest

from autoflow_kit import fsops, policy, reviewing, trail, verifying, workspace
from autoflow_kit.errors import StageError
from tests import support

NOW = support.NOW


class ReviewingTest(unittest.TestCase):
    def test_review_new_one_prompt_per_lens(self) -> None:
        where, run_id = support.risked(self)
        reviewing.review_new(where, run_id, NOW)
        for lens in policy.depth_of(policy.MEDIUM).lenses:
            prompt = fsops.read_text(where.finder_prompt_path(run_id, 1, lens))
            self.assertIn(where.relative(where.findings_path(run_id, 1, lens)), prompt)
        self.assertIn("+def multiply", fsops.read_text(where.review_diff_path(run_id, 1)))

    def test_collect_merges_and_skips(self) -> None:
        where, run_id = support.risked(self)
        reviewing.review_new(where, run_id, NOW)
        found = {
            "correctness": [support.finding(), support.finding(file="dist/app.min.js", line=1)],
            "security": [support.finding(title="同じ場所の別の見方")],
        }
        support.act_finders(where, run_id, found)
        reviewing.review_collect(where, run_id, NOW)
        candidates = workspace.load_candidates(where, run_id, 1)
        self.assertEqual([(item.id, item.lenses) for item in candidates], [("R1-1", ("correctness", "security"))])
        self.assertTrue(where.verifier_prompt_path(run_id, 1, 3).is_file())

    def test_votes_decide_what_stays(self) -> None:
        where, run_id = support.risked(self)
        found = {"correctness": [support.finding(), support.finding(line=5, title="別の指摘")]}
        ballots = [
            {"R1-1": ("real", policy.NIT), "R1-2": ("real", policy.IMPORTANT)},
            {"R1-1": ("real", policy.IMPORTANT), "R1-2": ("not_real", policy.IMPORTANT)},
            {"R1-1": ("not_real", policy.NIT), "R1-2": ("not_real", policy.IMPORTANT)},
        ]
        support.review_round(where, run_id, found, ballots)
        result = workspace.load_result(where, run_id, 1)
        self.assertEqual(
            [(item.id, item.tag, item.real_votes) for item in result.kept], [("R1-1", policy.IMPORTANT, 2)]
        )
        self.assertEqual(result.dropped, ("R1-2",))
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.reason), (trail.BUILD, trail.FINDINGS))

    def test_no_candidates_skips_verifiers(self) -> None:
        where, run_id = support.risked(self)
        reviewing.review_new(where, run_id, NOW)
        support.act_finders(where, run_id)
        reviewing.review_collect(where, run_id, NOW)
        self.assertFalse(where.verifier_prompt_path(run_id, 1, 1).exists())
        reviewing.review_tally(where, run_id, NOW)
        self.assertEqual(support.next_step(where, run_id).step, trail.HANDOFF)

    def test_tree_changed_during_review(self) -> None:
        where, run_id = support.risked(self)
        reviewing.review_new(where, run_id, NOW)
        support.act_finders(where, run_id)
        support.write_files(where, {"calc.py": "x = 1\n"})
        with self.assertRaisesRegex(StageError, "作業ツリーが変わりました"):
            reviewing.review_collect(where, run_id, NOW)

    def test_second_round_sees_only_new_diff_and_drops_declined(self) -> None:
        where, run_id = support.risked(self)
        support.review_round(where, run_id, {"correctness": [support.finding()]})
        declined = {"finding_id": "R1-1", "status": "declined", "reason": "負の数は仕様の外", "locations": []}
        files = {"README.md": "# sample\n\n掛け算もある。\n"}
        support.build(where, run_id, files, resolutions=[declined])
        verifying.verify(where, run_id, NOW)
        self.assertEqual(support.next_step(where, run_id).step, trail.REVIEW)
        reviewing.review_new(where, run_id, NOW)
        diff = fsops.read_text(where.review_diff_path(run_id, 2))
        self.assertIn("README.md", diff)
        self.assertNotIn("def multiply", diff)
        self.assertIn("負の数は仕様の外", fsops.read_text(where.finder_prompt_path(run_id, 2, "correctness")))
        support.act_finders(where, run_id, {"correctness": [support.finding()]})
        reviewing.review_collect(where, run_id, NOW)
        self.assertEqual(workspace.load_candidates(where, run_id, 2), ())

    def test_review_rounds_escalate(self) -> None:
        where, run_id = support.risked(self)
        for round_no in range(1, 4):
            support.review_round(where, run_id, {"correctness": [support.finding(line=round_no)]})
            if round_no < 3:
                answer = {"finding_id": f"R{round_no}-1", "status": "fixed", "reason": "", "locations": []}
                support.build(where, run_id, {"README.md": f"{round_no}\n"}, resolutions=[answer])
                verifying.verify(where, run_id, NOW)
        current = support.next_step(where, run_id)
        self.assertEqual((current.step, current.gate), (trail.DECIDE, policy.H2))
