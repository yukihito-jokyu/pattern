"""作業ツリーの tree id と、tree どうしの差分（ファイル、行数、差分の文）を求める。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autoflow_kit import proc


@dataclass(frozen=True)
class Stat:
    path: str
    added: int
    deleted: int


def snapshot(root: Path) -> str:
    """未追跡ファイルを含む今の版を、利用者の index を変えずに記録する。"""
    return proc.git_snapshot(root)


def branch(root: Path) -> str:
    return proc.git_branch(root)


def changed_files(root: Path, base: str, tree: str) -> tuple[str, ...]:
    return proc.git_diff_names(root, base, tree)


def stats(root: Path, base: str, tree: str) -> tuple[Stat, ...]:
    return tuple(Stat(path, added, deleted) for path, added, deleted in proc.git_numstat(root, base, tree))


def line_count(found: tuple[Stat, ...]) -> int:
    return sum(stat.added + stat.deleted for stat in found)


def diff_text(root: Path, base: str, tree: str) -> str:
    return proc.git_diff(root, base, tree)
