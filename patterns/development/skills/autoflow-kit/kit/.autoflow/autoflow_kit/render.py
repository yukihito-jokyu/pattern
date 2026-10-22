"""Markdown の部品（表、数、箇条書き、コードの囲み、job の行）を、副作用の無い関数で作る。"""

from __future__ import annotations

from collections.abc import Sequence

MISSING = "—"
FENCE = "```"


def number(value: float | None, digits: int = 0) -> str:
    return MISSING if value is None else f"{value:.{digits}f}"


def percent(part: int, whole: int) -> str:
    return MISSING if whole == 0 else f"{part * 100 / whole:.0f}%"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip() or MISSING


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def bullets(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- なし"


def fence(text: str) -> str:
    """コードの囲み。中身に ``` があれば、より長い囲みにする。"""
    marker = FENCE
    while marker in text:
        marker += "`"
    return f"{marker}text\n{text.rstrip()}\n{marker}"


def job(agent: str, label: str, prompt_path: str) -> str:
    """サブエージェントの起動の指示の1行。スキルはこの行から Agent ツールの呼び出しを作る。"""
    return " ".join(["job", agent, label, prompt_path])
