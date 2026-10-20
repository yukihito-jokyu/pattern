"""trace のテスト。記録した stream-json から、起動・編集・完了・費用を読むことを確かめる。"""

from __future__ import annotations

import unittest

from forge_kit import fsops, trace
from tests import support


def load(name: str) -> trace.Trace:
    return trace.parse(fsops.read_text(support.STREAMS / f"{name}.jsonl"))


class TraceTest(unittest.TestCase):
    def test_delegated(self) -> None:
        record = load("delegated")
        self.assertEqual([launch.agent for launch in record.launches], ["dev-orch-implementer", "dev-orch-reviewer"])
        self.assertEqual((record.edits_main, record.edits_sub), ((), (support.IMPL_FILE,)))
        self.assertTrue(record.completed)
        self.assertEqual((record.cost_usd, record.duration_sec), (0.42, 95.0))
        actors = {event.actor for event in record.events}
        self.assertEqual(actors, {trace.MAIN, "dev-orch-implementer", "dev-orch-reviewer"})

    def test_main_edit(self) -> None:
        record = load("main-edit")
        self.assertEqual(record.launches, ())
        self.assertEqual(record.edits_main, (support.IMPL_FILE,))
        self.assertEqual((record.denials, record.malformed_lines), (("Bash",), 1))

    def test_spawn_depth(self) -> None:
        self.assertEqual(load("delegated").max_depth, 1)
        self.assertEqual(load("main-edit").max_depth, 0)

    def test_unfinished(self) -> None:
        record = load("unfinished")
        self.assertFalse(record.finished)
        self.assertFalse(record.completed)
        self.assertIsNone(record.cost_usd)

    def test_render_trace(self) -> None:
        text = trace.render_trace(load("delegated"))
        self.assertIn("dev-orch-implementer, dev-orch-reviewer", text)
        self.assertIn("| 3 | dev-orch-implementer | Bash | python3 check.py |", text)


if __name__ == "__main__":
    unittest.main()
