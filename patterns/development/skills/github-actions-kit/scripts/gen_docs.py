"""配布するスキルの references/ を正本から作る（KIT-06）。標準ライブラリだけを使う。

- references/rules.md: docs/design/rules.md の「用語」以降から KIT 節を除いたもの
- references/examples/: .github/ の参照実装（ワークフロー、composite アクション、dependabot.yml）の写し

`--check` を付けると書き換えずに、生成物が正本と食い違っていれば終了コード 1 を返す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "design" / "rules.md"
REFERENCES = ROOT / ".claude" / "skills" / "gha-workflow" / "references"
EXAMPLES = REFERENCES / "examples"
FIRST_SECTION = "## 用語"
DROPPED_SECTIONS = ("## KIT ",)
PREAMBLE = """\
<!-- 生成物。github-actions-kit の docs/design/rules.md から scripts/gen_docs.py が作る。手で編集しない -->
# GitHub Actions のワークフローのルール

GitHub Actions のワークフロー、composite アクション、`dependabot.yml` を書く・直すときのルールである。\
実装用スキル（`../SKILL.md`）、レビュー用スキル、検査の指摘は、ここのルールIDを参照する。

- 検査の指摘は `<ルールID> <パス>:<行> <説明>` の形で出る。外部ツールの指摘は、説明の先頭に `[ツール:規則名]` が付く
- **強制**の先頭のキーワードは、そのルールを守らせる仕組みである。`lint` と `structure` は \
`uv run --locked --script .gha/gha.py check` が落とし、`review` はレビュー用スキルが確かめ、`doc` は手順として守る
- **出典**と**強制**の欄のパス（`research.md`、`rules_*.py` など）は github-actions-kit のリポジトリのものである
- 「見本」と書いたファイルは `examples/` にある（`examples/workflows/ci.yml` など）

"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="書き換えずに食い違いだけを報告する")
    args = parser.parse_args()
    expected = build()
    actual = {path: path.read_text(encoding="utf-8") for path in _generated_files()}
    stale = sorted(
        {path for path in expected if actual.get(path) != expected[path]} | (actual.keys() - expected.keys())
    )
    if args.check:
        for path in stale:
            print(f"KIT-06 {path.relative_to(ROOT).as_posix()}:1 生成物が正本と食い違う。make docs を回す")
        print(f"docs-check: 食い違い {len(stale)} 件")
        return 1 if stale else 0
    for path in actual.keys() - expected.keys():
        path.unlink()
    for path, text in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"docs: {len(expected)} ファイルを書いた（書き換え {len(stale)} 件）")
    return 0


def build() -> dict[Path, str]:
    files = {REFERENCES / "rules.md": render_rules(SOURCE.read_text(encoding="utf-8"))}
    github = ROOT / ".github"
    sources = [
        *sorted((github / "workflows").glob("*.yml")),
        *sorted((github / "actions").glob("*/action.yml")),
        github / "dependabot.yml",
    ]
    for source in sources:
        files[EXAMPLES / source.relative_to(github)] = source.read_text(encoding="utf-8")
    return files


def render_rules(text: str) -> str:
    """「用語」より前（読み方と書式）と KIT 節を除き、追加した軸の表から KIT の行を除く。"""
    body = text[text.index(FIRST_SECTION) :]
    kept: list[str] = []
    dropping = False
    for line in body.splitlines():
        if line.startswith("## "):
            dropping = line.startswith(DROPPED_SECTIONS)
        if not dropping and not line.endswith("| KIT |"):
            kept.append(line)
    return PREAMBLE + "\n".join(kept).rstrip() + "\n"


def _generated_files() -> list[Path]:
    files = [REFERENCES / "rules.md"] if (REFERENCES / "rules.md").is_file() else []
    return files + sorted(path for path in EXAMPLES.rglob("*") if path.is_file())


if __name__ == "__main__":
    sys.exit(main())
