"""git のある版（コミット、ブランチ）のファイルを読む。"""

from __future__ import annotations

from pathlib import Path

from gha_kit import proc
from gha_kit.errors import UsageError

TEXT_SUFFIXES = (".yml", ".yaml", ".sh", ".py", ".json")


def show(root: Path, ref: str, rel: str) -> str | None:
    """版 ref の rel の中身。その版に無ければ None。"""
    result = proc.run(["git", "show", f"{ref}:{rel}"], root)
    return result.stdout if result.code == 0 else None


def tracked(root: Path, ref: str, base: str) -> list[str]:
    """版 ref の base の下にある、テキストとして読むファイルの一覧。"""
    result = proc.run(["git", "ls-tree", "-r", "--name-only", ref, "--", base], root)
    if result.code != 0:
        raise UsageError(f"git の版 {ref} を読めない: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.endswith(TEXT_SUFFIXES)]
