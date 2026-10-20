"""配布するスキルの参照ファイルのうち、コードから作る文書（指標の一覧、バンドルの決まり）を生成する。

--check は、生成し直した結果と今のファイルが違えば失敗する。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from forge_kit import bundle, catalog, render

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "kit" / "claude" / "skills"
CATALOG_MD = SKILLS / "forge-goals" / "references" / "metric-catalog.md"
RULES_MD = SKILLS / "forge-build" / "references" / "bundle-rules.md"
HEADER = "<!-- 生成物。scripts/gen_docs.py が {source} から作る。手で編集しない（make docs で作り直す） -->"


def render_catalog() -> str:
    amounts = "、".join(f"`{metric.id}`" for metric in catalog.METRICS if metric.max_value is None)
    parts = [
        HEADER.format(source="catalog.py"),
        "",
        "# 指標の一覧",
        "",
        "charter の `metrics` に書ける指標である。`machine` は補助 CLI が実行の記録と差分から機械で数え、"
        "`grader` は採点役が判定する。",
        f"値は 0〜1 の割合（量の指標 {amounts} を除く）で、課題ごとに求めてから平均する。",
        "",
    ]
    for metric in catalog.METRICS:
        direction = "高いほど良い" if metric.direction == "higher" else "低いほど良い"
        recommended = "（推奨）" if metric.recommended else ""
        parts += [
            f"## `{metric.id}` {metric.name}{recommended}",
            "",
            render.table(
                ["項目", "内容"],
                [
                    ["分かること", metric.tells],
                    ["求め方", metric.computes],
                    ["測り方", metric.method],
                    ["向き", direction],
                    ["既定の閾値", render.number(metric.default_threshold)],
                    ["前提", metric.requires or render.MISSING],
                ],
            ),
            "",
        ]
    parts += [
        "## 独自の指標（`custom_<番号>`）",
        "",
        "一覧に無い観点は `custom_1` のような id にし、`criterion` に、"
        "採点役が「満たした / 満たしていない」で判定できる1文を書く。",
        "値は、満たした実行の割合になる。向きは高いほど良い。",
        "",
    ]
    return "\n".join(parts)


def render_rules() -> str:
    parts = [
        HEADER.format(source="bundle.py の RULES"),
        "",
        "# バンドルの決まり",
        "",
        "バンドルとは、対象のスキル（`skills/<スキル名>/`）と、そのサブエージェント（`agents/<スキル名>-<役>.md`）の組である。"
        "下書き・候補・リポジトリの `.claude/` のバンドルは、全部の決まりを満たす。"
        "補助 CLI の `bundle-check`、`prepare`、`propose` がこの決まりで検査し、満たさないと先へ進まない。",
        "",
        render.table(["id", "決まり"], [[rule.id, rule.text] for rule in bundle.RULES]),
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="生成物が最新かだけを確かめる")
    args = parser.parse_args()
    stale = []
    for path, text in ((CATALOG_MD, render_catalog()), (RULES_MD, render_rules())):
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if args.check:
            if current != text:
                stale.append(path)
            continue
        path.write_text(text, encoding="utf-8")
        print(f"生成: {path.relative_to(ROOT)}")
    for path in stale:
        print(f"{path.relative_to(ROOT)} が古い。make docs で作り直す", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
