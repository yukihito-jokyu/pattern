"""Generate deterministic synthetic logs; never read a real agent session."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agent-behavior-html/scripts"))
from event_model import normalize


def demo_events() -> list:
    events = []
    for source in ("claude", "codex"):
        base = {"session_id": "demo-" + source, "turn_id": "turn-auth-fix"}
        failure_event = "PostToolUseFailure" if source == "claude" else "PostToolUse"
        read = {"tool_name": "Read", "tool_input": {"file_path": "src/auth.ts"}}
        edit = {"tool_name": "Edit", "tool_input": {"file_path": "src/auth.ts",
                "old_string": "if (!token) return null", "new_string": "if (!token?.trim()) return null"}}
        check = {"command": "npm test -- auth.test.ts"}
        schedule = [
            (0, "SessionStart", {}), (1, "UserPromptSubmit", {"prompt": "synthetic prompt, not retained"}),
            (2, "ActionIntent", dict(read, purpose="空白だけのトークンが認証を通る原因を確認する",
                                     expected="トークンの空文字判定と分岐条件が分かる")),
            (3, "PreToolUse", dict(read, tool_use_id="read-1")),
            (5, "PostToolUse", dict(read, tool_use_id="read-1", tool_response="synthetic source, not retained")),
            (6, "PreToolUse", {"tool_use_id": "check-1", "tool_name": "Bash",
                               "tool_input": dict(check, description="修正前の認証テストを実行し、問題を再現する")}),
            (9, failure_event, {"tool_use_id": "check-1", "tool_name": "Bash",
                               "error": "auth.test.ts: 空白トークンの拒否テストが失敗",
                               "tool_response": {"exit_code": 1, "stderr": "FAIL auth.test.ts · expected 401, received 200"}}),
            (10, "ActionIntent", dict(edit, purpose="空白トークンも未指定として扱い、認証の抜けを修正する",
                                      expected="空白トークンのリクエストが拒否される")),
            (11, "PreToolUse", dict(edit, tool_use_id="edit-1")),
            (13, "PostToolUse", dict(edit, tool_use_id="edit-1", tool_response={"message": "synthetic edit"})),
            (14, "PreToolUse", {"tool_use_id": "check-2", "tool_name": "Bash",
                                "tool_input": dict(check, description="修正後に同じテストを再実行し、問題の解消を確認する")}),
            (17, "PostToolUse", {"tool_use_id": "check-2", "tool_name": "Bash",
                                 "tool_response": {"exit_code": 0, "stdout": "PASS auth.test.ts · 12 tests passed"}}),
            (18, "PreToolUse", {"tool_use_id": "pending-1", "tool_name": "Bash",
                                "tool_input": {"command": "npm run test:integration"}}),
            (19, "PreToolUse", {"tool_use_id": "read-2", "tool_name": "Read",
                                "tool_input": {"file_path": "docs/auth-notes.md"}}),
            (20, "PostToolUse", {"tool_use_id": "read-2", "tool_name": "Read", "tool_response": "synthetic notes"}),
            (21, "SubagentStart", {"agent_id": "worker-1"}),
            (22, "SubagentStop", {"agent_id": "worker-1"}),
            (23, "PreCompact", {}), (24, "PostCompact", {}), (25, "Stop", {}), (26, "SessionEnd", {}),
        ]
        for index, (seconds, event_name, fields) in enumerate(schedule):
            observed = (datetime(2026, 10, 23, 0, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
            event = normalize(dict(base, hook_event_name=event_name, **fields), source, b"synthetic-demo-key", observed)
            event["event_id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, source + ":" + str(index)))
            events.append(event)
    return events


def main() -> int:
    path = ROOT / "examples/demo.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in demo_events()), encoding="utf-8")
    print("Synthetic logs: " + str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
