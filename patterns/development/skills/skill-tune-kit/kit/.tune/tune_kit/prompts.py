"""サブエージェントへのプロンプトを、templates/prompts/ のひな形から作る。プロンプトの文はひな形だけに書く。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from tune_kit import fsops, layout
from tune_kit.errors import KitError

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / layout.TEMPLATES_DIR / layout.PROMPTS_DIR
PLACEHOLDER = re.compile(r"\$\{([a-z_]+)\}")
# ひな形の名前と、ひな形が使う置き換えの名前。ひな形を変えたら、この表とテストを一緒に変える（STATE-02）
TEMPLATES: dict[str, frozenset[str]] = {
    "executor": frozenset({"skill_dir", "skill_md", "sandbox", "case_prompt", "response_path"}),
    "grader": frozenset(
        {"case_prompt", "expected", "criteria", "response_path", "sandbox", "changes", "grade_path", "judge_ids"}
    ),
    "learner": frozenset(
        {
            "goal",
            "checks",
            "current_dir",
            "candidate_dir",
            "evidence_path",
            "proposal_path",
            "history",
            "problems",
            "line_limit",
            "train_ids",
        }
    ),
    "auditor": frozenset({"goal", "mode", "scope", "evidence_path", "audit_path", "check_ids", "case_ids", "problems"}),
}


def build_template_path(name: str) -> Path:
    return TEMPLATES_DIR / f"{name}{layout.TEMPLATE_SUFFIX}"


def list_placeholders(text: str) -> frozenset[str]:
    return frozenset(PLACEHOLDER.findall(text))


def render_prompt(name: str, values: Mapping[str, str]) -> str:
    """ひな形の ${名前} を値で置き換える。値の名前がひな形の表と食い違えばエラーにする。"""
    expected = TEMPLATES.get(name)
    if expected is None:
        raise KitError(f"プロンプトのひな形 {name} は prompts.TEMPLATES にありません")
    if set(values) != expected:
        missing = sorted(expected - set(values))
        extra = sorted(set(values) - expected)
        raise KitError(f"ひな形 {name} の置き換えの名前が合いません（足りない: {missing}、余分: {extra}）")
    template = fsops.read_text(build_template_path(name))
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], template)
