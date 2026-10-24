"""rollout のテスト。"""

from __future__ import annotations

import unittest
from pathlib import Path

from h2_kit import layout, profile, rollout, sandbox, skilltree, transcript
from tests import support


def _build_outcome(reply: str, skills: tuple[str, ...] = ()) -> transcript.Outcome:
    return transcript.Outcome(reply, True, False, "success", 1, 0.0, 0, skills)


class RolloutTest(unittest.TestCase):
    def test_run_writes_the_record_last_and_reuses_it(self) -> None:
        where = support.build_where(support.build_repo(self))
        log = where.repo / "log.jsonl"
        task = support.write_task(where)
        job = rollout.Job(
            "base1", where.repo / "r" / "base1", support.read_skill(where), task, support.build_model(log=log)
        )
        view = rollout.run_rollout(job)
        again = rollout.run_rollout(job)
        self.assertEqual(len(support.read_log(log)), 1)
        self.assertEqual(view.record, again.record)
        self.assertTrue(view.record.skill_invoked)
        self.assertTrue(view.record.ok)
        for name in (layout.STREAM_FILE, layout.TRAJECTORY_FILE, layout.DELIVERABLE_FILE, layout.REPLY_FILE):
            self.assertTrue((job.directory / name).is_file(), name)
        self.assertTrue((job.directory / layout.OUTPUT_DIR / "memo.md").is_file())
        self.assertIn("[ACTION] Skill", rollout.read_trajectory(view))

    def test_slash_prompt_counts_as_invoked(self) -> None:
        self.assertTrue(rollout.is_skill_invoked("/sample 整えて", "sample", _build_outcome("x")))
        self.assertTrue(rollout.is_skill_invoked("整えて", "sample", _build_outcome("x", ("sample",))))
        self.assertFalse(rollout.is_skill_invoked("sample を使って", "sample", _build_outcome("x")))

    def test_delivered_depends_on_the_kind(self) -> None:
        wrote = [sandbox.FileChange(skilltree.ADDED, "a.md", "a", True)]
        replied = _build_outcome("済み")
        self.assertTrue(rollout.is_delivered(profile.FILES_DELIVERABLE, _build_outcome(""), wrote))
        self.assertFalse(rollout.is_delivered(profile.FILES_DELIVERABLE, replied, []))
        self.assertTrue(rollout.is_delivered(profile.REPLY_DELIVERABLE, replied, []))
        self.assertFalse(rollout.is_delivered(profile.ANY_DELIVERABLE, _build_outcome(""), []))

    def test_deliverable_shows_reply_and_files(self) -> None:
        changes = [sandbox.FileChange(skilltree.ADDED, "a.md", "本文\n", True)]
        text = rollout.render_deliverable("済み", changes)
        self.assertIn("# 最後の返答\n\n済み", text)
        self.assertIn("## added: `a.md`", text)
        self.assertEqual(rollout.build_skill_name(support.build_model()), Path(support.SKILL_PATH).name)
