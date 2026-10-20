"""execute のテスト。claude -p の引数（OPS-05 の表）と、実行の記録の保存、続きからの実行を確かめる。"""

from __future__ import annotations

import unittest
from pathlib import Path

from forge_kit import charter, execute, fsops, layout, prepare, workspace
from forge_kit.errors import StageError
from tests import support

FORBIDDEN = ("bypassPermissions", "--dangerously-skip-permissions", "--bare")


class ExecuteTest(unittest.TestCase):
    def test_command(self) -> None:
        model = charter.parse(support.orch_charter(), "charter.json")
        args = execute.command(model.executor, "/dev-orch 依頼", Path("/w/system.md"))
        expected = [
            "claude",
            "-p",
            "/dev-orch 依頼",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--permission-prompts",
            "none",
            "--no-session-persistence",
            "--max-budget-usd",
            "1.0",
            "--append-system-prompt-file",
            "/w/system.md",
            "--allowedTools",
            "Bash(python3 check.py)",
        ]
        self.assertEqual(args, expected)
        self.assertFalse(any(word in arg for arg in args for word in FORBIDDEN))

    def test_model_and_empty_allowed_tools(self) -> None:
        data = support.orch_charter()
        executor = data["executor"]
        assert isinstance(executor, dict)
        executor.update({"model": "sonnet", "allowed_tools": []})
        args = execute.command(charter.parse(data, "charter.json").executor, "p", Path("/s.md"))
        self.assertEqual(args[-2:], ["--model", "sonnet"])
        self.assertNotIn("--allowedTools", args)

    def test_execute(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        slot = layout.make_slot("baseline", 1)
        prepare.prepare(where, slot)
        out = execute.execute(where, slot, support.fake_launcher(exit_code=1))
        self.assertIn("今回 2 件", out)
        self.assertIn("WARN T1-a1 は終了コード 1", out)
        self.assertEqual(workspace.load_execution(where, slot, "T1-a1").exit_code, 1)
        self.assertIn("dev-orch-implementer", fsops.read_text(where.stream_path(slot, "T1-a1")))
        self.assertTrue((where.copy_dir(slot, "T1-a1") / support.IMPL_FILE).is_file())
        self.assertIn("今回 0 件、済み 2 件", execute.execute(where, slot, support.fake_launcher()))

    def test_missing_copy(self) -> None:
        where = support.approved_layout(self, support.orch_charter())
        slot = layout.make_slot("baseline", 1)
        prepare.prepare(where, slot)
        fsops.remove_tree(where.copy_dir(slot, "T1-a2"))
        with self.assertRaises(StageError):
            execute.execute(where, slot, support.fake_launcher())


if __name__ == "__main__":
    unittest.main()
