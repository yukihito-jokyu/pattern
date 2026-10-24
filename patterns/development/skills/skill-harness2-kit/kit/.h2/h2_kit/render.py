"""Markdown の部品（表、箇条書き、金額、囲み）。人に見せる文字列の形をここで揃える（OPS-03）。"""

from __future__ import annotations

import re
from collections.abc import Sequence

BLANK_RUNS = re.compile(r"\n{3,}")
FENCE_RUN = re.compile(r"`{3,}")


def render_cell(text: str) -> str:
    """表のセル。`|` と改行で表が崩れないようにする。"""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = [
        "| " + " | ".join(render_cell(h) for h in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines += ["| " + " | ".join(render_cell(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def render_bullets(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_usd(value: float) -> str:
    return f"${value:.2f}"


def render_fence(text: str, info: str = "") -> str:
    """囲み。中にある最も長い ``` より1つ長い囲みにする。"""
    longest = max((len(match) for match in FENCE_RUN.findall(text)), default=2)
    fence = "`" * (longest + 1)
    body = text if text.endswith("\n") else text + "\n"
    return f"{fence}{info}\n{body}{fence}"


def render_sections(parts: Sequence[str]) -> str:
    """空でない部分を空行で区切ってつなぎ、3行以上の空行を詰める。"""
    joined = "\n\n".join(part.strip() for part in parts if part.strip())
    return BLANK_RUNS.sub("\n\n", joined).strip() + "\n"
