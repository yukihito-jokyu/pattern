"""github-actions-kit を配布先のリポジトリに入れる・上げる。標準ライブラリだけを使う。

使い方:
  python3 install.py <配布先のリポジトリ> [--dry-run]

写すもの（ADR 0003）:
  .gha/                              検査の CLI と設定。zizmor.yml と actionlint.yaml は既にあれば残す
  .github/actions/run-report/        処理時間の報告と合否の composite アクション
  .claude/skills/gha-workflow/       実装用スキル（作成・保守的更新・破壊的更新）
  .claude/skills/gha-review/         レビュー用スキル
  .github/dependabot.yml             外部アクションの更新の設定（PROC-03）。既にあれば残す

ディレクトリごと置き換えるもの（gha_kit、run-report、スキル）は、写す前に配布先の同じディレクトリを消す。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
REPLACED_DIRS = (
    ".gha/gha_kit",
    ".github/actions/run-report",
    ".claude/skills/gha-workflow",
    ".claude/skills/gha-review",
)
REPLACED_FILES = (".gha/gha.py", ".gha/gha.py.lock", ".gha/yamllint.yml")
# dependabot.yml を写すのは、run-report があるだけで PROC-03 が dependabot.yml を求め、導入した直後の check が落ちるため
KEPT_FILES = (".gha/zizmor.yml", ".gha/actionlint.yaml", ".github/dependabot.yml")
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")
NEXT_STEPS = """\
次にすること:
  1. uv を入れる（https://docs.astral.sh/uv/）
  2. uv run --locked --script .gha/gha.py check を回し、既存のワークフローの指摘を見る（空のリポジトリなら0件）
  3. ci.yml に report ジョブを置き、ブランチ保護の必須チェックを report にする（references/rules.md の OPS-01）
"""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="書かずに、何をするかだけを出す")
    args = parser.parse_args(argv)
    target = args.target.resolve()
    if not target.is_dir():
        print(f"エラー: {target} はディレクトリではない", file=sys.stderr)
        return 2
    if target == KIT:
        print("エラー: キット自身には入れない", file=sys.stderr)
        return 2
    for line in install(target, dry_run=args.dry_run):
        print(line)
    print(NEXT_STEPS, end="")
    return 0


def install(target: Path, dry_run: bool = False) -> list[str]:
    """写した内容を1行ずつ返す。dry_run なら書かない。"""
    log = []
    for rel in REPLACED_DIRS:
        log.append(f"置き換え {rel}/")
        if not dry_run:
            shutil.rmtree(target / rel, ignore_errors=True)
            shutil.copytree(KIT / rel, target / rel, ignore=IGNORED)
    for rel in REPLACED_FILES:
        log.append(f"置き換え {rel}")
        if not dry_run:
            _copy(KIT / rel, target / rel)
    for rel in KEPT_FILES:
        if (target / rel).exists():
            log.append(f"残した   {rel}（配布先の設定）")
            continue
        log.append(f"作った   {rel}")
        if not dry_run:
            _copy(KIT / rel, target / rel)
    return log


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
