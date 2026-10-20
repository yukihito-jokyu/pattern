"""Markdown の部品（表、数値、費用、箇条書き、job の行）を、副作用の無い関数で作る。"""

from __future__ import annotations

from collections.abc import Sequence

MISSING = "—"


def number(value: float | None) -> str:
    return MISSING if value is None else f"{value:.3f}"


def usd(value: float | None) -> str:
    return MISSING if value is None else f"${value:.2f}"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip() or MISSING


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def bullets(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- なし"


def mark(flag: bool) -> str:
    return "達成" if flag else "未達"


def job(agent: str, label: str, prompt_path: str) -> str:
    """サブエージェントの起動の指示の1行。スキルはこの行から Agent ツールの呼び出しを作る。"""
    return " ".join(["job", agent, label, prompt_path])
