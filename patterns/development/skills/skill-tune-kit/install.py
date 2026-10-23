"""skill-tune-kit の配布物（kit/）を利用者のリポジトリに入れる。既にあるファイルは --force が無ければ上書きしない。"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent / "kit"
# 配布物の置き場と、利用者のリポジトリでの置き場
DESTINATIONS = ((".tune", ".tune"), ("claude", ".claude"))
SKIP = ("__pycache__", ".mypy_cache", ".ruff_cache", ".DS_Store")
IGNORE_LINE = ".tune/work/"
GITIGNORE = ".gitignore"


def list_sources() -> list[tuple[Path, Path]]:
    """写すファイルと、写し先のリポジトリのルートからの相対パス。"""
    pairs: list[tuple[Path, Path]] = []
    for source_name, destination_name in DESTINATIONS:
        base = KIT / source_name
        for path in sorted(base.rglob("*")):
            if path.is_file() and not any(part in SKIP for part in path.relative_to(base).parts):
                pairs.append((path, Path(destination_name) / path.relative_to(base)))
    return pairs


def write_gitignore(dest: Path) -> bool:
    """作業場所を .gitignore に足す。足したら True。"""
    path = dest / GITIGNORE
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if IGNORE_LINE in text.splitlines():
        return False
    separator = "" if not text or text.endswith("\n") else "\n"
    path.write_text(f"{text}{separator}{IGNORE_LINE}\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dest", help="入れる先のリポジトリのルート")
    parser.add_argument("--force", action="store_true", help="既にあるファイルを上書きする")
    args = parser.parse_args()
    dest = Path(args.dest).resolve()
    if not dest.is_dir():
        print(f"エラー: {dest} はディレクトリではありません", file=sys.stderr)
        return 1
    pairs = list_sources()
    conflicts = [relative for _source, relative in pairs if (dest / relative).exists()]
    if conflicts and not args.force:
        lines = "\n".join(f"  - {relative}" for relative in conflicts)
        print(f"エラー: 既にあるファイルがあります。上書きするなら --force を付けてください:\n{lines}", file=sys.stderr)
        return 1
    for source, relative in pairs:
        (dest / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest / relative)
    added = write_gitignore(dest)
    print(f"入れました: {len(pairs)} ファイル（{dest}）")
    if added:
        print(f"{GITIGNORE} に {IGNORE_LINE} を足しました")
    print("使い方: Claude Code で /skill-tune <target-id> <対象スキルのディレクトリ> を実行する")
    return 0


if __name__ == "__main__":
    sys.exit(main())
