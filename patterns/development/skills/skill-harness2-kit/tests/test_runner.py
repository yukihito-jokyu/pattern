"""runner のテスト。claude のコマンド行の閉じ込めのフラグ（OPS-05）。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h2_kit import fsops, layout, runner
from tests import support


def _value_after(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


class RunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_rollout_command_hides_user_settings_and_adds_skill(self) -> None:
        command = runner.build_rollout_command(support.build_model())
        self.assertEqual(_value_after(command, "--setting-sources"), "project")
        self.assertEqual(_value_after(command, "--permission-prompts"), "none")
        for flag in ("--strict-mcp-config", "--no-session-persistence", "-p"):
            self.assertIn(flag, command)
        self.assertIn("Skill", command[command.index("--allowedTools") :])
        self.assertNotIn("--dangerously-skip-permissions", command)

    def test_session_command_is_restricted(self) -> None:
        model = support.build_model(improver={"model": "m", "effort": "high", "timeout_sec": 60, "max_budget_usd": 1})
        command = runner.build_session_command(model, runner.EDIT_TOOLS)
        for flag in ("--restricted", "--disable-slash-commands", "--strict-mcp-config", "--no-session-persistence"):
            self.assertIn(flag, command)
        self.assertEqual(_value_after(command, "--permission-prompts"), "none")
        self.assertEqual(_value_after(command, "--tools"), "Read,Edit,Write,Glob,Grep")
        self.assertEqual((_value_after(command, "--model"), _value_after(command, "--effort")), ("m", "high"))
        self.assertEqual(
            _value_after(runner.build_session_command(model, runner.READ_TOOLS), "--tools"), "Read,Glob,Grep"
        )

    def test_same_session_is_reused(self) -> None:
        log = self.root / "log.jsonl"
        model = support.build_model(log=log)
        session = self.root / "agg1.a1"
        fsops.write_text(session / layout.CONTEXT_DIR / layout.TASK_FILE, "依頼")
        first = runner.run_session(model, session, "合成して", runner.EDIT_TOOLS)
        second = runner.run_session(model, session, "合成して", runner.EDIT_TOOLS)
        self.assertTrue(first.ok)
        self.assertEqual((first.cached, second.cached), (False, True))
        self.assertEqual(len(support.read_log(log)), 1)
        for name in (layout.MISSION_FILE, layout.REPLY_FILE, layout.SESSION_FILE):
            self.assertTrue((session / name).is_file())

    def test_failed_session_is_not_ok(self) -> None:
        model = support.build_model(behaviors=("fail-compose",))
        session = self.root / "agg1.a1"
        fsops.write_text(session / layout.CONTEXT_DIR / layout.TASK_FILE, "依頼")
        reply = runner.run_session(model, session, "合成して", runner.EDIT_TOOLS)
        self.assertFalse(reply.ok)
        self.assertIn("結果がありません", reply.error)
