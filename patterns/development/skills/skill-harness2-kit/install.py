"""配布物（kit/）を利用者のリポジトリに入れる。`.h2/targets/`（利用者の対象と記録）には触れない。

使い方: python3 install.py <利用者のリポジトリ> [--force]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

KIT = Path(__file__).resolve().parent / "kit"
# 配布物の置き場と、利用者のリポジトリでの置き場。--force のときは右の置き場を消してから写す
PLACES = (
    (Path(".h2") / "h2.py", Path(".h2") / "h2.py"),
    (Path(".h2") / ".gitignore", Path(".h2") / ".gitignore"),
    (Path(".h2") / "h2_kit", Path(".h2") / "h2_kit"),
    (Path(".h2") / "templates", Path(".h2") / "templates"),
    (Path("claude") / "skills" / "skill-harness2", Path(".claude") / "skills" / "skill-harness2"),
)
IGNORED = frozenset({"__pycache__", ".DS_Store"})


def list_files(root: Path) -> list[Path]:
    """root の下のファイル（root がファイルならそれ自体）を、root からの相対パスで並べる。"""
    if root.is_file():
        return [Path()]
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not IGNORED & set(path.relative_to(root).parts) and path.suffix != ".pyc"
    )


def list_conflicts(repo: Path) -> list[Path]:
    """中身の違う既存のファイル。"""
    conflicts = []
    for source, target in PLACES:
        for relative in list_files(KIT / source):
            installed = repo / target / relative
            if installed.is_file() and installed.read_bytes() != (KIT / source / relative).read_bytes():
                conflicts.append(installed)
    return conflicts


def copy_kit(repo: Path, force: bool) -> int:
    """置き場ごとに写し、写したファイルの数を返す。"""
    count = 0
    for source, target in PLACES:
        if force and (repo / target).is_dir():
            shutil.rmtree(repo / target)
        for relative in list_files(KIT / source):
            installed = repo / target / relative
            installed.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KIT / source / relative, installed)
            count += 1
    return count


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="skill-harness2 を利用者のリポジトリに入れる")
    parser.add_argument("repo", help="利用者のリポジトリのルート")
    parser.add_argument("--force", action="store_true", help="中身の違う既存のファイルを置き換える")
    args = parser.parse_args(list(argv))
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"エラー: {repo} はディレクトリではありません", file=sys.stderr)
        return 1
    conflicts = list_conflicts(repo)
    if conflicts and not args.force:
        shown = "\n".join(f"- {path}" for path in conflicts)
        print(
            f"エラー: 中身の違うファイルがあります。置き換えるなら --force を付けてください\n{shown}", file=sys.stderr
        )
        return 1
    count = copy_kit(repo, args.force)
    print(f"{repo} に {count} ファイルを入れました（.h2/targets/ には触れていません）")
    print("次: Claude Code で /skill-harness2 <対象の名前> を実行する")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
