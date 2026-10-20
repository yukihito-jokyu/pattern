"""サブエージェントと実行役へのプロンプトと、下書きの骨組みを、templates/prompts/ のひな形から作る。

文章はひな形だけに書く。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from forge_kit import fsops
from forge_kit.errors import KitError

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "prompts"
PLACEHOLDER = re.compile(r"\$\{?([a-z_]+)\}?")
# ひな形の名前と、ひな形が使う置き換えの名前。ひな形を変えたら、この表とテストを一緒に変える
TEMPLATES: dict[str, tuple[str, frozenset[str]]] = {
    "designer": (
        "designer.md",
        frozenset({"skill_name", "repo", "charter_md", "schema_md", "rules_md", "design", "feedback"}),
    ),
    "draft-skill": (
        "draft-skill.md",
        frozenset({"skill_name", "summary", "roles", "steps", "checkpoints", "report"}),
    ),
    "draft-agent": (
        "draft-agent.md",
        frozenset({"agent_name", "purpose", "tools", "input", "output"}),
    ),
    "builder": (
        "builder.md",
        frozenset({"skill_name", "repo", "charter_md", "design_md", "rules_md", "draft_dir", "feedback"}),
    ),
    "executor": ("executor.md", frozenset({"skill_name", "task_prompt"})),
    "executor-system": ("executor-system.md", frozenset({"skill_name"})),
    "grader": (
        "grader.md",
        frozenset({"run_id", "task_prompt", "skill_md", "trace_md", "result_md", "patch", "items", "grade"}),
    ),
    "analyst": (
        "analyst.md",
        frozenset(
            {
                "skill_name",
                "charter_md",
                "scores_md",
                "rules_md",
                "evidence",
                "history",
                "bundle_dir",
                "proposed_dir",
                "proposal",
                "causes",
            }
        ),
    ),
}


def placeholders(text: str) -> frozenset[str]:
    return frozenset(PLACEHOLDER.findall(text))


def render(name: str, values: Mapping[str, str]) -> str:
    """ひな形の $名前 を values で置き換える。過不足があれば KitError にする（ひな形と表の食い違い）。"""
    if name not in TEMPLATES:
        raise KitError(f"ひな形 {name} は表にありません")
    file_name, expected = TEMPLATES[name]
    if set(values) != expected:
        raise KitError(f"ひな形 {name} の置き換えが表と違います（表: {sorted(expected)}、渡した値: {sorted(values)}）")
    text = fsops.read_text(TEMPLATES_DIR / file_name)
    if placeholders(text) != expected:
        raise KitError(f"ひな形 {file_name} の置き換え {sorted(placeholders(text))} が表 {sorted(expected)} と違います")
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], text)
