"""Markdown の部品（表、率、箇条書き、コードの囲み）を、副作用の無い関数で作る。"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

MISSING = "—"


def render_rate(value: Fraction | None) -> str:
    """率を百分率で書く。値が無ければ MISSING。"""
    if value is None:
        return MISSING
    return f"{float(value) * 100:.1f}%"


def render_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip() or MISSING


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(render_cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def render_bullets(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- なし"


def render_fence(text: str, language: str = "") -> str:
    """中身に含まれるより長いバッククォートで囲む。"""
    longest = 0
    run = 0
    for char in text:
        run = run + 1 if char == "`" else 0
        longest = max(longest, run)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{text.rstrip()}\n{fence}"


def render_job(agent: str, label: str, prompt_path: str) -> str:
    """サブエージェントの起動の指示の1行。スキルはこの行から Agent ツールの呼び出しを作る。"""
    return f"job {agent} {label} {prompt_path}"
