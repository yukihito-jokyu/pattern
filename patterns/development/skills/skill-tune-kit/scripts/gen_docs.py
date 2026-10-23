"""検査の種類の一覧（check-kinds.md）を checks.KINDS から作る。--check なら差分があるときに失敗する。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tune_kit import checks, render

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "kit" / "claude" / "skills" / "skill-tune" / "references" / "check-kinds.md"


def render_kinds() -> str:
    rows = []
    for kind in checks.KINDS.values():
        required = ", ".join(f"`{name}`" for name in kind.required) or render.MISSING
        optional = ", ".join(f"`{name}`" for name in kind.optional) or render.MISSING
        rows.append(
            [f"`{kind.name}`", "採点役" if kind.judge else "機械", required, optional, kind.summary, kind.expected]
        )
    examples = [f"- `{kind.name}`: `{kind.example}`" for kind in checks.KINDS.values()]
    return "\n".join(
        [
            "# 検査の種類",
            "",
            "<!-- 生成物。scripts/gen_docs.py が checks.KINDS から作る。手で編集せず make docs で作り直す -->",
            "",
            "検査の `kind` に書ける種類の一覧である。どの種類にも `id`、`kind`、`severity` が要る。",
            "",
            render.render_table(["kind", "判定", "必須の項目", "書いてよい項目", "合格の条件", "正解の使い方"], rows),
            "",
            "## 例",
            "",
            *examples,
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="作り直さず、差分があれば失敗する")
    args = parser.parse_args()
    text = render_kinds()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != text:
            print(f"STR-04 {OUTPUT.relative_to(ROOT)}:1 生成物が checks.KINDS と違います。make docs を実行してください")
            return 1
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"作成: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
