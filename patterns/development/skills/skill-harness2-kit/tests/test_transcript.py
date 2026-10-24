"""transcript のテスト。"""

from __future__ import annotations

import json
import unittest

from h2_kit import transcript


def _build_stream(*events: dict[str, object]) -> str:
    return "\n".join(json.dumps(event, ensure_ascii=False) for event in events)


class TranscriptTest(unittest.TestCase):
    def test_outcome_collects_skill_calls_and_result(self) -> None:
        use = {"type": "tool_use", "name": "Skill", "input": {"skill": "sample"}}
        stream = _build_stream(
            {"type": "assistant", "message": {"content": [use]}},
            {"type": "result", "subtype": "success", "result": "済み", "total_cost_usd": 0.5, "num_turns": 4},
        )
        outcome = transcript.parse_outcome(stream)
        self.assertEqual(outcome.skills, ("sample",))
        self.assertTrue(outcome.finished)
        self.assertEqual((outcome.reply, outcome.cost_usd, outcome.num_turns), ("済み", 0.5, 4))

    def test_outcome_without_result_is_not_finished(self) -> None:
        self.assertFalse(transcript.parse_outcome("壊れた行").finished)
        self.assertFalse(transcript.parse_result_json("").finished)

    def test_trajectory_clips_one_observation_and_hides_the_sandbox(self) -> None:
        done = {"type": "tool_result", "content": "/tmp/box/" + "x" * 30, "is_error": False}
        stream = _build_stream({"type": "user", "message": {"content": [done]}}) + "\n{壊れた"
        text = transcript.render_trajectory(stream, 20, "/tmp/box")
        self.assertIn("[OBSERVATION]", text)
        self.assertIn("この印は実行の失敗ではない", text)
        self.assertIn("[ERROR] 読めない行", text)
        self.assertNotIn("/tmp/box", text)
