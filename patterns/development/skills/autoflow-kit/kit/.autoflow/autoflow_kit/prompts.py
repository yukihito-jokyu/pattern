"""サブエージェントへのプロンプトを、templates/prompts/ のひな形から作る。文章はひな形だけに書く（STATE-02）。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from autoflow_kit import fsops
from autoflow_kit.errors import KitError

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "prompts"
PLACEHOLDER = re.compile(r"\$\{([a-z_]+)\}")
# ひな形の名前、ファイル、置き換えの名前。ひな形を変えたら、この表とテストを一緒に変える（PROC-02）
TEMPLATES: dict[str, tuple[str, frozenset[str]]] = {
    "planner": (
        "planner.md",
        frozenset({"task_path", "guide_path", "kinds", "feedback", "output_path", "ref"}),
    ),
    "builder": (
        "builder.md",
        frozenset({"task_path", "plan_md_path", "reason", "tests", "failures", "findings", "answer", "report_path"}),
    ),
    "risk": (
        "risk.md",
        frozenset({"plan_md_path", "diff_path", "rule_tier", "rule_reasons", "tiers", "output_path"}),
    ),
    "finder": (
        "finder.md",
        frozenset(
            {"lens", "plan_md_path", "guide_path", "diff_path", "round_no", "prior_findings", "skip", "output_path"}
        ),
    ),
    "verifier": (
        "verifier.md",
        frozenset({"plan_md_path", "guide_path", "diff_path", "candidates_path", "output_path"}),
    ),
}


def placeholders(text: str) -> frozenset[str]:
    return frozenset(PLACEHOLDER.findall(text))


def fill(name: str, values: Mapping[str, str]) -> str:
    """ひな形の ${名前} を values で置き換える。過不足があれば KitError にする（ひな形と表の食い違い）。"""
    if name not in TEMPLATES:
        raise KitError(f"ひな形 {name} は表にありません")
    file_name, expected = TEMPLATES[name]
    if set(values) != expected:
        raise KitError(f"ひな形 {name} の置き換えが表と違います（表: {sorted(expected)}、渡した値: {sorted(values)}）")
    text = fsops.read_text(TEMPLATES_DIR / file_name)
    if placeholders(text) != expected:
        raise KitError(f"ひな形 {file_name} の置き換え {sorted(placeholders(text))} が表 {sorted(expected)} と違います")
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], text)
