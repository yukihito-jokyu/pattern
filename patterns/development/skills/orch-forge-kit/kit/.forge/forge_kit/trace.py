"""実行の記録（claude -p の stream-json）を読み、起動・編集・費用を数え、採点役が読む版を作る。

読むのは文書にある項目だけにする（ADR 0009）。項目の綴りは Claude Code のまま、このモジュールだけで扱う。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from forge_kit import render

LAUNCH_TOOLS = ("Agent", "Task")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
DETAIL_KEYS = ("subagent_type", "file_path", "notebook_path", "command", "pattern", "path", "skill", "url")
DETAIL_CHARS = 120
MAX_EVENTS = 400
MAIN = "メイン"
SUCCESS = "success"


@dataclass(frozen=True)
class Event:
    """1回のツールの使用。actor はメインのセッション（MAIN）か、起動したサブエージェントの名前。"""

    actor: str
    tool: str
    detail: str


@dataclass(frozen=True)
class Launch:
    tool_use_id: str
    agent: str
    description: str


@dataclass(frozen=True)
class Trace:
    events: tuple[Event, ...]
    launches: tuple[Launch, ...]
    edits_main: tuple[str, ...]
    edits_sub: tuple[str, ...]
    max_depth: int
    finished: bool
    subtype: str
    is_error: bool
    cost_usd: float | None
    duration_sec: float | None
    turns: int | None
    denials: tuple[str, ...]
    result_text: str
    malformed_lines: int

    @property
    def completed(self) -> bool:
        return self.finished and self.subtype == SUCCESS and not self.is_error


def _messages(text: str) -> tuple[list[dict[str, Any]], int]:
    found, malformed = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(value, dict):
            found.append(value)
        else:
            malformed += 1
    return found, malformed


def _tool_uses(message: dict[str, Any]) -> list[dict[str, Any]]:
    if message.get("type") != "assistant":
        return []
    body = message.get("message")
    content = body.get("content") if isinstance(body, dict) else None
    if not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, dict) and item.get("type") == "tool_use"]


def _detail(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in DETAIL_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            first = value.strip().splitlines()[0] if value.strip() else ""
            return first[:DETAIL_CHARS]
    return ""


def _launches(messages: Sequence[dict[str, Any]]) -> tuple[Launch, ...]:
    """メインの会話（parent_tool_use_id が null）が Agent ツールで起動したサブエージェント。"""
    found = []
    for message in messages:
        if message.get("parent_tool_use_id") is not None:
            continue
        for use in _tool_uses(message):
            raw = use.get("input")
            tool_input: dict[str, Any] = raw if isinstance(raw, dict) else {}
            if use.get("name") in LAUNCH_TOOLS:
                agent = str(tool_input.get("subagent_type") or "general-purpose")
                found.append(Launch(str(use.get("id", "")), agent, str(tool_input.get("description", ""))))
    return tuple(found)


def _events(messages: Sequence[dict[str, Any]], launches: Sequence[Launch]) -> tuple[Event, ...]:
    names = {launch.tool_use_id: launch.agent for launch in launches}
    found = []
    for message in messages:
        parent = message.get("parent_tool_use_id")
        actor = MAIN if parent is None else names.get(str(parent), str(parent))
        for use in _tool_uses(message):
            found.append(Event(actor, str(use.get("name", "")), _detail(use.get("input"))))
    return tuple(found)


def _edits(events: Sequence[Event]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    main = tuple(event.detail for event in events if event.tool in EDIT_TOOLS and event.actor == MAIN)
    sub = tuple(event.detail for event in events if event.tool in EDIT_TOOLS and event.actor != MAIN)
    return main, sub


def _depth(messages: Sequence[dict[str, Any]]) -> int:
    depths = [
        message.get("spawn_depth")
        for message in messages
        if message.get("type") == "system" and message.get("subtype") == "task_started"
    ]
    return max((depth for depth in depths if isinstance(depth, int)), default=0)


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _denials(result: dict[str, Any]) -> tuple[str, ...]:
    denials = result.get("permission_denials")
    if not isinstance(denials, list):
        return ()
    return tuple(str(item.get("tool_name", "")) for item in denials if isinstance(item, dict))


def parse(text: str) -> Trace:
    """stream-json の全文を読む。JSON として読めない行は数えて飛ばし、result が無ければ未完了とする。"""
    messages, malformed = _messages(text)
    launches = _launches(messages)
    events = _events(messages, launches)
    edits_main, edits_sub = _edits(events)
    result = next((m for m in reversed(messages) if m.get("type") == "result"), None)
    data = result or {}
    duration_ms = _number(data.get("duration_ms"))
    turns = data.get("num_turns")
    return Trace(
        events=events,
        launches=launches,
        edits_main=edits_main,
        edits_sub=edits_sub,
        max_depth=_depth(messages),
        finished=result is not None,
        subtype=str(data.get("subtype", "")),
        is_error=data.get("is_error") is True,
        cost_usd=_number(data.get("total_cost_usd")),
        duration_sec=None if duration_ms is None else round(duration_ms / 1000, 1),
        turns=turns if isinstance(turns, int) and not isinstance(turns, bool) else None,
        denials=_denials(data),
        result_text=str(data.get("result", "")),
        malformed_lines=malformed,
    )


def render_trace(trace: Trace) -> str:
    """採点役と分析役が読む版。概要の表と、ツールの使用を順に並べた一覧。"""
    summary = render.table(
        ["項目", "値"],
        [
            ["完了", "はい" if trace.completed else f"いいえ（{trace.subtype or 'result なし'}）"],
            ["起動したサブエージェント", ", ".join(launch.agent for launch in trace.launches) or "なし"],
            ["メインのセッションの編集", str(len(trace.edits_main))],
            ["サブエージェントの編集", str(len(trace.edits_sub))],
            ["入れ子の深さの最大", str(trace.max_depth)],
            ["拒否された操作", ", ".join(trace.denials) or "なし"],
            ["費用（推定）", render.usd(trace.cost_usd)],
            ["時間（秒）", render.number(trace.duration_sec)],
        ],
    )
    shown = trace.events[:MAX_EVENTS]
    rows = [[str(number), event.actor, event.tool, event.detail] for number, event in enumerate(shown, 1)]
    omitted = len(trace.events) - len(shown)
    parts = ["# 実行の記録の要約", "", "## 概要", "", summary, "", "## ツールの使用（順）", ""]
    parts.append(render.table(["#", "誰が", "ツール", "対象"], rows) if rows else "ツールの使用は無い")
    if omitted:
        parts += ["", f"（以降の {omitted} 件は省いた）"]
    return "\n".join(parts) + "\n"
