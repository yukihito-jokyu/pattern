"""ひな形（templates/prompts/<名前>.md）からプロンプトを作る。プロンプトの文はひな形だけに置く（STATE-02）。

`${名前}` は値で置き換え、`${block_<名前>}` は `_<名前>.md`（`_` は `-` に読み替える）を同じ値で描いて置き換える。
`<!-- -->` のコメントは、ひな形の出典を書くためのもので、プロンプトには入れない。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from h2_kit import fsops, layout
from h2_kit.errors import KitError

PLACEHOLDER = re.compile(r"\$\{([a-z][a-z0-9_]*)\}")
COMMENT = re.compile(r"[ \t]*<!--.*?-->[ \t]*\n?", re.S)
BLANK_RUNS = re.compile(r"\n{3,}")
BLOCK_PREFIX = "block_"
PART_PREFIX = "_"

# ひな形ごとの置き換えの名前（`${block_*}` を除く）。tests/test_prompts.py がファイルと突き合わせる
TEMPLATES: dict[str, tuple[str, ...]] = {
    "mission": ("job", "layout"),
    "propose-inv": ("work", "deliverable_word", "levers", "yardstick"),
    "propose-dom": ("work", "deliverable_word", "domain_word", "levers", "yardstick"),
    "compose": ("work", "k", "candidate_count", "parallel_composers", "yardstick"),
    "compose-round": ("work", "t", "k", "first_round", "round_job"),
    "select": ("n", "work", "deliverable_word", "selection_lead", "selection_checks", "ids"),
    "reflect": ("work", "chosen", "why", "layout"),
    "_answer-free": (),
    "_answer-free-select": (),
    "_evidence-boundary": (),
    "_evidence-boundary-select": (),
    "_generalize": ("domain_word",),
    "_how-to-read": (),
    "_how-to-decide": ("candidate_of", "round"),
    "_keep-base": (),
    "_layout-legend": (),
    "_notes-format": ("k", "example_failed"),
    "_pool-finals": (),
    "_surface": (),
    "_candidate-of": ("index", "k"),
    "_round": ("t",),
    "_yardstick": ("text",),
    "_parallel-composers": ("k",),
    "_first-round": (),
    "_compose-final": (),
    "_compose-checkpoint": ("t",),
    "_selection-lead": ("text",),
    "_selection-checks": ("text",),
    "_rejected": ("problems",),
}


def read_template(templates_dir: Path, name: str) -> str:
    """ひな形の本文（コメントを除いたもの）。"""
    if name not in TEMPLATES:
        raise KitError(f"ひな形 {name} は prompts.TEMPLATES にありません")
    return COMMENT.sub("", fsops.read_text(templates_dir / f"{name}{layout.MD_SUFFIX}"))


def list_placeholders(text: str) -> list[str]:
    """本文の置き換えの名前を、出てくる順に重ならずに並べる。"""
    return list(dict.fromkeys(PLACEHOLDER.findall(text)))


def build_block_name(placeholder: str) -> str:
    """`block_answer_free` → `_answer-free`。"""
    return PART_PREFIX + placeholder[len(BLOCK_PREFIX) :].replace("_", "-")


def render_prompt(templates_dir: Path, name: str, values: Mapping[str, str]) -> str:
    """ひな形を値で描く。表の名前の値が欠けていれば KitError を投げる。空の値の段落は詰める。"""
    text = read_template(templates_dir, name)
    missing = [key for key in TEMPLATES[name] if key not in values]
    if missing:
        raise KitError(f"ひな形 {name} の値 {', '.join(missing)} がありません")

    def _fill(match: re.Match[str]) -> str:
        key = match.group(1)
        if key.startswith(BLOCK_PREFIX):
            return render_prompt(templates_dir, build_block_name(key), values).strip()
        if key not in TEMPLATES[name]:
            raise KitError(f"ひな形 {name} の {key} は prompts.TEMPLATES に登録されていません")
        return values[key].strip()

    return BLANK_RUNS.sub("\n\n", PLACEHOLDER.sub(_fill, text)).strip() + "\n"


def render_part(templates_dir: Path, name: str, values: Mapping[str, str], when: bool) -> str:
    """条件つきの部品。when が偽なら空文字（ひな形の段落ごと消える）。"""
    return render_prompt(templates_dir, name, values) if when else ""
