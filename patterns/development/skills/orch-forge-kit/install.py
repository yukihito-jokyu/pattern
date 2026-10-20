#!/usr/bin/env python3
"""orch-forge-kit を対象のリポジトリに入れる（補助 CLI、スキル、サブエージェント、.gitignore と権限の設定）。"""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

KIT = Path(__file__).resolve().parent / "kit"
GITIGNORE_LINES = ("# orch-forge-kit", ".forge/work/", "__pycache__/")
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")
# スキルの allowed-tools と同じ許可。スキルの許可は呼んだターンだけ効くので、裏の実行の完了を待った後のために残す
CLI_RULE = "Bash(python3 .forge/forge.py *)"


def planned(dest: Path) -> list[tuple[Path, Path]]:
    """(写す元, 写す先) の組。ディレクトリは丸ごと、エージェントはファイルごとに写す。"""
    pairs = [
        (KIT / ".forge" / "forge.py", dest / ".forge" / "forge.py"),
        (KIT / ".forge" / "forge_kit", dest / ".forge" / "forge_kit"),
        (KIT / ".forge" / "templates", dest / ".forge" / "templates"),
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


def has_gitignore_line(dest: Path) -> bool:
    path = dest / ".gitignore"
    return path.is_file() and ".forge/work/" in path.read_text(encoding="utf-8").splitlines()


def add_gitignore(dest: Path) -> None:
    path = dest / ".gitignore"
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    prefix = "" if not current or current.endswith("\n") else "\n"
    path.write_text(current + prefix + "\n".join(GITIGNORE_LINES) + "\n", encoding="utf-8")


def _has_cli_rule(dest: Path) -> bool:
    path = dest / ".claude" / "settings.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    allow = data.get("permissions", {}).get("allow", []) if isinstance(data, dict) else []
    return isinstance(allow, list) and CLI_RULE in allow


def add_cli_rule(dest: Path) -> bool:
    """.claude/settings.json の permissions.allow に CLI_RULE を足す。形が読めないファイルは変えずに False を返す。"""
    path = dest / ".claude" / "settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict) or not isinstance(permissions.get("allow", []), list):
        return False
    data["permissions"] = {**permissions, "allow": [*permissions.get("allow", []), CLI_RULE]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


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
    if not has_gitignore_line(dest):
        add_gitignore(dest)
        print("足した: .gitignore に .forge/work/")
    if not _has_cli_rule(dest):
        if add_cli_rule(dest):
            print(f"足した: .claude/settings.json の permissions.allow に {CLI_RULE}")
        else:
            print(
                f"WARN .claude/settings.json の形が読めないため、permissions.allow に {CLI_RULE} を手で足してください"
            )
    print("次: 対象のリポジトリで Claude Code を開き、/forge-goals を実行する")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
