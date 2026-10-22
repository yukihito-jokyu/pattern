#!/usr/bin/env python3
"""autoflow-kit を対象のリポジトリに入れる（補助 CLI、ひな形、スキル、サブエージェント、.gitignore の行）。

対象のリポジトリの .autoflow/profile.json・profile-approval.json・runs/ は変えない。
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

KIT = Path(__file__).resolve().parent / "kit"
GITIGNORE_LINES = ("# autoflow-kit", ".autoflow/runs/", ".claude/settings.local.json", "__pycache__/")
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")


def planned(dest: Path) -> list[tuple[Path, Path]]:
    """(写す元, 写す先) の組。ディレクトリは丸ごと、スキルはディレクトリごと、エージェントはファイルごとに写す。"""
    pairs = [
        (KIT / ".autoflow" / "autoflow.py", dest / ".autoflow" / "autoflow.py"),
        (KIT / ".autoflow" / "autoflow_kit", dest / ".autoflow" / "autoflow_kit"),
        (KIT / ".autoflow" / "templates", dest / ".autoflow" / "templates"),
    ]
    pairs += [(skill, dest / ".claude" / "skills" / skill.name) for skill in sorted((KIT / "claude/skills").iterdir())]
    pairs += [
        (agent, dest / ".claude" / "agents" / agent.name) for agent in sorted((KIT / "claude/agents").glob("*.md"))
    ]
    return pairs


def is_changed(source: Path, target: Path) -> bool:
    """写す先が既にあり、中身が写す元と違うか（上書きで人の変更を消さないため）。"""
    if not target.exists():
        return False
    if source.is_file():
        return not filecmp.cmp(source, target, shallow=False)
    return _is_tree_changed(filecmp.dircmp(source, target, ignore=["__pycache__"]))


def _is_tree_changed(comparison: filecmp.dircmp[str]) -> bool:
    if comparison.left_only or comparison.right_only or comparison.diff_files or comparison.funny_files:
        return True
    return any(_is_tree_changed(sub) for sub in comparison.subdirs.values())


def copy(source: Path, target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=IGNORED)
    else:
        shutil.copy2(source, target)


def missing_gitignore_lines(dest: Path) -> list[str]:
    path = dest / ".gitignore"
    current = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    return [line for line in GITIGNORE_LINES[1:] if line not in current]


def add_gitignore(dest: Path, lines: Sequence[str]) -> None:
    path = dest / ".gitignore"
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    prefix = "" if not current or current.endswith("\n") else "\n"
    path.write_text(current + prefix + "\n".join([GITIGNORE_LINES[0], *lines]) + "\n", encoding="utf-8")


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, help="入れる先のリポジトリのルート")
    parser.add_argument("--force", action="store_true", help="中身の違う既存のファイルを上書きする")
    args = parser.parse_args(argv)
    dest = Path(args.dest).resolve()
    if not dest.is_dir():
        print(f"エラー: {dest} がありません", file=sys.stderr)
        return 1
    pairs = planned(dest)
    conflicts = [target for source, target in pairs if is_changed(source, target)]
    if conflicts and not args.force:
        print(
            "エラー: 次のファイルは既にあり、中身が違います。上書きするなら --force を付けてください", file=sys.stderr
        )
        for target in conflicts:
            print(f"  {target.relative_to(dest)}", file=sys.stderr)
        return 1
    for source, target in pairs:
        copy(source, target)
        print(f"写した: {target.relative_to(dest)}")
    lines = missing_gitignore_lines(dest)
    if lines:
        add_gitignore(dest, lines)
        print(f"足した: .gitignore に {', '.join(lines)}")
    print("次: 対象のリポジトリで Claude Code を開き、/autoflow-setup を実行する")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
