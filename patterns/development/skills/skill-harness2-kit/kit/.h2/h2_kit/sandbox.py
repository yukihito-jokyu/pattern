"""実行の作業場所（sandbox）。タスクの材料と候補のスキルを入れ、実行の後に材料からの変化を読む。"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from h2_kit import fsops, layout, skilltree

SANDBOX_PREFIX = "h2-rollout-"
SKIPPED = frozenset({layout.CLAUDE_DIR, layout.GIT_DIR})


@dataclass(frozen=True)
class FileChange:
    """作業場所の1つのファイルの変化。kind は skilltree の ADDED・MODIFIED・REMOVED。

    body は、足したテキストのファイルなら全文、変えたテキストのファイルなら unified diff、それ以外は空。
    """

    kind: str
    path: str
    body: str
    is_text: bool


def write_sandbox(source: Path, tree: skilltree.SkillTree, skill_name: str) -> Path:
    """OS の一時ディレクトリに作業場所を作る。材料の .claude/ と .git/ は写さない。"""
    place = fsops.write_temp_dir(SANDBOX_PREFIX)
    if source.is_dir():
        fsops.copy_tree(source, place, skip=SKIPPED)
    skilltree.write_tree(tree, place / layout.CLAUDE_DIR / layout.SKILLS_DIR / skill_name)
    return place


def read_changes(source: Path, place: Path) -> list[FileChange]:
    """材料（source）と実行の後の作業場所（place）を比べる。.claude/ と .git/ は比べない。"""
    before = set(_list_work_files(source))
    after = set(_list_work_files(place))
    changes: list[FileChange] = []
    for path in sorted(before | after):
        old = source / path if path in before else None
        new = place / path if path in after else None
        if old is not None and new is not None and old.read_bytes() == new.read_bytes():
            continue
        changes.append(_build_change(path, old, new))
    return changes


def copy_output(place: Path, output: Path) -> None:
    fsops.copy_tree(place, output, skip=SKIPPED)


def remove_sandbox(place: Path) -> None:
    fsops.remove_tree(place)


def _list_work_files(root: Path) -> list[str]:
    return [path for path in fsops.list_files(root) if path.split("/", 1)[0] not in SKIPPED]


def _build_change(path: str, old: Path | None, new: Path | None) -> FileChange:
    old_text = fsops.read_text_or_none(old) if old is not None else ""
    new_text = fsops.read_text_or_none(new) if new is not None else ""
    if old is None:
        return FileChange(skilltree.ADDED, path, new_text or "", new_text is not None)
    if new is None:
        return FileChange(skilltree.REMOVED, path, "", old_text is not None)
    if old_text is None or new_text is None:
        return FileChange(skilltree.MODIFIED, path, "", is_text=False)
    lines = difflib.unified_diff(
        old_text.splitlines(keepends=True), new_text.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}"
    )
    return FileChange(
        skilltree.MODIFIED, path, "".join(line if line.endswith("\n") else line + "\n" for line in lines), True
    )
