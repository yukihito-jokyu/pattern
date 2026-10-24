"""`claude -p` の出力（stream-json と json）を読み、軌跡の Markdown と実行の結末を作る。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass

SKILL_TOOL = "Skill"
SANDBOX_MARK = "<作業場所>"


@dataclass(frozen=True)
class Outcome:
    """1回の `claude -p` の結末。finished は result の行があったか。"""

    reply: str
    finished: bool
    is_error: bool
    subtype: str
    num_turns: int
    cost_usd: float
    permission_denials: int
    skills: tuple[str, ...]


def parse_outcome(stream: str) -> Outcome:
    """stream-json の全行から結末を読む。呼ばれたスキルは Skill の tool_use から集める。"""
    skills: list[str] = []
    result: dict[str, object] = {}
    for event in _list_events(stream):
        if event.get("type") == "result":
            result = event
        for item in _list_content(event):
            if item.get("type") == "tool_use" and item.get("name") == SKILL_TOOL:
                value = _build_mapping(item.get("input")).get("skill")
                if isinstance(value, str):
                    skills.append(value)
    return _build_outcome(result, tuple(skills))


def parse_result_json(text: str) -> Outcome:
    """`--output-format json` の1つの JSON から結末を読む。読めなければ終わっていないものとして返す。"""
    whole = _parse_line(text) if text.strip() else None
    if whole is not None and whole.get("type") == "result":
        return _build_outcome(whole, ())
    events = list(_list_events(text))
    result = next((event for event in reversed(events) if event.get("type") == "result"), {})
    return _build_outcome(result, ())


def render_trajectory(stream: str, obs_trunc: int, sandbox: str) -> str:
    """軌跡を `[ACTION]`・`[OBSERVATION]`・`[ERROR]` の行で書く。全イベントを書き、1つの観測だけを obs_trunc で切る。"""
    blocks: list[str] = []
    for line in stream.splitlines():
        if not line.strip():
            continue
        event = _parse_line(line)
        if event is None:
            blocks.append(f"[ERROR] 読めない行: {_build_clipped(line, obs_trunc)}")
            continue
        blocks += list(_render_event(event, obs_trunc))
    text = "\n\n".join(blocks) if blocks else "（軌跡がありません: claude の出力が空でした）"
    return (text.replace(sandbox, SANDBOX_MARK) if sandbox else text) + "\n"


def _render_event(event: dict[str, object], obs_trunc: int) -> Iterator[str]:
    kind = event.get("type")
    if kind == "system" and event.get("subtype") == "init":
        skills = event.get("skills")
        names = ", ".join(str(name) for name in skills) if isinstance(skills, list) else ""
        yield f"[SYSTEM] 開始: model={event.get('model', '')} skills=[{names}]"
    elif kind == "assistant":
        for item in _list_content(event):
            if item.get("type") == "text":
                yield f"[ASSISTANT]\n{item.get('text', '')}"
            elif item.get("type") == "tool_use":
                arguments = json.dumps(item.get("input"), ensure_ascii=False)
                yield f"[ACTION] {item.get('name', '')}\n{_build_clipped(arguments, obs_trunc)}"
    elif kind == "user":
        yield from _render_user(event, obs_trunc)
    elif kind == "result":
        yield (
            f"[RESULT] subtype={event.get('subtype', '')} is_error={event.get('is_error', '')} "
            f"num_turns={event.get('num_turns', '')}\n{event.get('result', '')}"
        )


def _render_user(event: dict[str, object], obs_trunc: int) -> Iterator[str]:
    message = _build_mapping(event.get("message"))
    content = message.get("content")
    if isinstance(content, str):
        yield f"[OBSERVATION]\n{_build_clipped(content, obs_trunc)}"
        return
    for item in _list_content(event):
        if item.get("type") == "tool_result":
            tag = "[ERROR]" if item.get("is_error") is True else "[OBSERVATION]"
            yield f"{tag}\n{_build_clipped(_build_result_text(item.get('content')), obs_trunc)}"
        elif item.get("type") == "text":
            yield f"[OBSERVATION]\n{_build_clipped(str(item.get('text', '')), obs_trunc)}"


def _build_outcome(result: dict[str, object], skills: tuple[str, ...]) -> Outcome:
    denials = result.get("permission_denials")
    cost = result.get("total_cost_usd")
    turns = result.get("num_turns")
    reply = result.get("result")
    return Outcome(
        reply=reply if isinstance(reply, str) else "",
        finished=bool(result),
        is_error=result.get("is_error") is True,
        subtype=str(result.get("subtype", "")),
        num_turns=turns if isinstance(turns, int) else 0,
        cost_usd=float(cost) if isinstance(cost, (int, float)) else 0.0,
        permission_denials=len(denials) if isinstance(denials, list) else 0,
        skills=skills,
    )


def _build_result_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [str(_build_mapping(part).get("text", "")) for part in content]
        return "\n".join(part for part in parts if part)
    return ""


def _build_clipped(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}\n…[描画の側で {omitted} 文字を省いた。この印は実行の失敗ではない]"


def _list_events(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        event = _parse_line(line) if line.strip() else None
        if event is not None:
            yield event


def _list_content(event: dict[str, object]) -> list[dict[str, object]]:
    content = _build_mapping(event.get("message")).get("content")
    if not isinstance(content, list):
        return []
    return [_build_mapping(item) for item in content]


def _parse_line(line: str) -> dict[str, object] | None:
    try:
        data: object = json.loads(line)
    except json.JSONDecodeError:
        return None
    return _build_mapping(data) if isinstance(data, dict) else None


def _build_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}
