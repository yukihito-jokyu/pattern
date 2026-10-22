"""配布するスキルの参照ファイルのうち、コードから作る文書（関所の表、プロファイルの項目）を生成する。

--check は、生成し直した結果と今のファイルが違えば失敗する（STR-04）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autoflow_kit import policy, profile, render, shape

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "kit" / "claude" / "skills"
GATES_MD = SKILLS / "autoflow" / "references" / "gates.md"
SCHEMA_MD = SKILLS / "autoflow-setup" / "references" / "profile-schema.md"
HEADER = "<!-- 生成物。scripts/gen_docs.py が {source}から作る。手で編集しない（make docs で作り直す） -->"


def _gates_table() -> list[str]:
    lines = []
    for gate in policy.GATES:
        rows = [[f"`{option.name}`", option.label, option.then] for option in gate.options]
        lines += [
            f"### {gate.id} {gate.label}",
            "",
            f"- いつ: {gate.when}",
            f"- 人に見せるもの: {gate.show}",
            "",
            render.table(["選択", "意味", "その後"], rows),
            "",
        ]
    return lines


def render_gates() -> str:
    rules = [[f"`{rule.id}`", rule.text] for rule in policy.H1_RULES]
    stuck = [[f"`{rule.id}`", rule.text] for rule in policy.H2_RULES]
    tiers = [[f"`{tier.name}`", tier.depth, tier.human] for tier in policy.TIERS]
    depths = [
        [depth.name, ", ".join(depth.lenses), render.number(depth.verifiers), render.number(depth.threshold)]
        for depth in policy.DEPTHS
    ]
    lenses = [[f"`{lens.name}`", lens.label] for lens in policy.LENSES]
    kinds = [[f"`{kind.name}`", kind.label, "要る" if kind.repro else "—", kind.checks] for kind in policy.KINDS]
    review = policy.REVIEW
    parts = [
        HEADER.format(source="policy.py の表"),
        "",
        "# 関所",
        "",
        "人の関所（H0〜H3）では人が決め、それ以外の場面では AI が人に聞かずに進む。"
        "機械の関所（段の順序、証拠、レビューの票、リスクの段、承認の結び付け）は補助 CLI が判定する。",
        "",
        "## 人の関所",
        "",
        *_gates_table(),
        "## H1 を起こす条件（どれか1つに当たれば聞く）",
        "",
        render.table(["id", "条件"], rules),
        "",
        "## H2 を起こす条件（どれか1つに当たれば聞く）",
        "",
        render.table(["id", "条件"], stuck),
        "",
        "## リスクの段",
        "",
        "段は差分のパスと行数から規則で決め、リスク判定役の段とは大きい方を採る（判定役は段を下げられない）。",
        "",
        render.table(["段", "レビューの深さ", "H3 で人がすること"], tiers),
        "",
        "## レビューの深さ",
        "",
        "探索役は観点ごとに1人、検証役は人数ぶん起動する。指摘は、本物の票が閾値以上のときだけ残る。",
        "",
        render.table(["深さ", "観点", "検証役", "閾値"], depths),
        "",
        render.table(["観点", "見ること"], lenses),
        "",
        f"- 指摘の種類: {', '.join(review.categories)}（文体・整形・掃除だけの指摘は受け付けない）",
        f"- 重大度: {', '.join(review.tags)}。報告に進めないのは {', '.join(review.blocking)} が残るとき",
        f"- {review.diff_only_from_round} ラウンド目からは、前のラウンドからの差分だけを見せる",
        "- 退けた指摘を、同じ場所と題名で出し直さない",
        "",
        "## 依頼の種類",
        "",
        render.table(["種類", "意味", "再現のテスト", "確かめること"], kinds),
        "",
    ]
    return "\n".join(parts)


def render_schema() -> str:
    defaults = shape.to_data(profile.make_profile((), ()))
    rows = [[f"`{field.key}`", field.kind, field.meaning] for field in profile.FIELDS]
    example = json.dumps(defaults, ensure_ascii=False, indent=2)
    parts = [
        HEADER.format(source="profile.py の FIELDS と既定値"),
        "",
        "# プロファイルの項目",
        "",
        f"`.autoflow/profile.json` の項目である。形の版は `schema_version` で、今は {profile.SCHEMA_VERSION} である。"
        "glob の `*` は `/` もまたぎ、`**/` で始まる glob はルートの直下のファイルにも当たる。",
        "",
        render.table(["項目", "型", "意味"], rows),
        "",
        "## 既定値",
        "",
        "setup-new は、検出した検査コマンドとレビューの指示のファイルを、次の既定値に足す。",
        "",
        render.fence(example),
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="生成物が最新かだけを確かめる")
    args = parser.parse_args()
    stale = []
    for path, text in ((GATES_MD, render_gates()), (SCHEMA_MD, render_schema())):
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if args.check:
            if current != text:
                stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"生成: {path.relative_to(ROOT)}")
    for path in stale:
        print(f"{path.relative_to(ROOT)} が古い。make docs で作り直す", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
