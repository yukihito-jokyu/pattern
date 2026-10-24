"""スキルの木（SKILL.md、references/、scripts/、assets/）の読み書き、編集面、frontmatter、差分、指紋、多様性。"""

from __future__ import annotations

import difflib
import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from h2_kit import fsops, layout

_PART = r"[A-Za-z0-9][A-Za-z0-9._-]*"
SURFACE = re.compile(
    rf"{re.escape(layout.SKILL_FILE)}"
    rf"|{layout.REFERENCES_DIR}/{_PART}{re.escape(layout.MD_SUFFIX)}"
    rf"|{layout.SCRIPTS_DIR}/{_PART}(?:{'|'.join(re.escape(s) for s in layout.SCRIPT_SUFFIXES)})"
    rf"|{layout.ASSETS_DIR}/{_PART}"
)
FRONTMATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
DESCRIPTION_KEY = "description"
ADDED = "added"
MODIFIED = "modified"
REMOVED = "removed"
CONFIRM_LENGTH = 12


@dataclass(frozen=True)
class SkillTree:
    """スキルの木。files は (相対パス, 中身) をパスの順に並べたもの。"""

    files: tuple[tuple[str, str], ...]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(path for path, _ in self.files)

    def find(self, path: str) -> str | None:
        return next((text for name, text in self.files if name == path), None)


@dataclass(frozen=True)
class Frontmatter:
    """SKILL.md の frontmatter。entries は description 以外の行、body は frontmatter の後の本文。"""

    entries: tuple[str, ...]
    description: str
    body: str


@dataclass(frozen=True)
class Change:
    """木の1つのファイルの変更。kind は added・removed・modified。"""

    kind: str
    path: str


def build_tree(files: Mapping[str, str]) -> SkillTree:
    return SkillTree(tuple(sorted(files.items())))


def build_replaced(tree: SkillTree, path: str, text: str) -> SkillTree:
    """1つのファイルを置き換えた（無ければ足した）新しい木。"""
    files = dict(tree.files)
    files[path] = text
    return build_tree(files)


def is_on_surface(path: str) -> bool:
    return SURFACE.fullmatch(path) is not None


def read_tree(root: Path) -> tuple[SkillTree, list[str]]:
    """木を読む。編集面の外のファイルと UTF-8 で読めないファイルは読まず、2つ目の値に並べる。"""
    files: dict[str, str] = {}
    rejected: list[str] = []
    for relative in fsops.list_files(root):
        text = fsops.read_text_or_none(root / relative) if is_on_surface(relative) else None
        if text is None:
            rejected.append(relative)
        else:
            files[relative] = text
    return build_tree(files), rejected


def write_tree(tree: SkillTree, root: Path) -> None:
    """root を木の中身で置き換える。"""
    fsops.remove_tree(root)
    fsops.write_dir(root)
    for path, text in tree.files:
        fsops.write_text(root / path, text)


def parse_frontmatter(text: str) -> Frontmatter | None:
    """frontmatter を読む。description は `description:` の行と、その後の字下げした行をつないだもの。"""
    found = FRONTMATTER.match(text)
    if found is None:
        return None
    entries: list[str] = []
    description: list[str] = []
    in_description = False
    for line in found.group(1).splitlines():
        key = line.split(":", 1)[0].strip() if ":" in line and not line[:1].isspace() else ""
        if key:
            in_description = key == DESCRIPTION_KEY
        if in_description:
            description.append(line.split(":", 1)[1] if key else line)
        else:
            entries.append(line)
    value = " ".join(part.strip() for part in description).strip().strip("\"'")
    return Frontmatter(tuple(entries), value, text[found.end() :])


def compute_fingerprint(tree: SkillTree) -> str:
    digest = hashlib.sha256()
    for path, text in tree.files:
        digest.update(path.encode("utf-8") + b"\0" + text.encode("utf-8") + b"\0")
    return digest.hexdigest()


def build_confirm_code(fingerprint: str) -> str:
    """adopt の --confirm に渡す確認の符号（指紋の先頭12文字）。"""
    return fingerprint[:CONFIRM_LENGTH]


def compute_changes(before: SkillTree, after: SkillTree) -> list[Change]:
    old = dict(before.files)
    new = dict(after.files)
    changes = [Change(ADDED, path) for path in new if path not in old]
    changes += [Change(REMOVED, path) for path in old if path not in new]
    changes += [Change(MODIFIED, path) for path in new if path in old and old[path] != new[path]]
    return sorted(changes, key=lambda change: change.path)


def compute_diff(before: SkillTree, after: SkillTree) -> str:
    """unified diff。変更が無ければ空文字。"""
    old = dict(before.files)
    new = dict(after.files)
    parts: list[str] = []
    for change in compute_changes(before, after):
        lines = difflib.unified_diff(
            old.get(change.path, "").splitlines(keepends=True),
            new.get(change.path, "").splitlines(keepends=True),
            fromfile="/dev/null" if change.kind == ADDED else f"a/{change.path}",
            tofile="/dev/null" if change.kind == REMOVED else f"b/{change.path}",
        )
        parts.append("".join(line if line.endswith("\n") else line + "\n" for line in lines))
    return "".join(parts)


def compute_diversity(trees: Sequence[SkillTree]) -> float:
    """木どうしの行の Jaccard 係数の平均（harness2 の diversity と同じ）。木が2つ未満なら 1.0。"""
    sets = [
        {f"{path}:{line}" for path, text in tree.files for line in text.splitlines() if line.strip()} for tree in trees
    ]
    sims = [
        len(sets[i] & sets[j]) / len(sets[i] | sets[j]) if sets[i] | sets[j] else 1.0
        for i in range(len(sets))
        for j in range(i + 1, len(sets))
    ]
    return round(sum(sims) / len(sims), 4) if sims else 1.0


def render_inventory(tree: SkillTree) -> str:
    """木のファイルと行数の一覧。"""
    return "\n".join(f"- `{path}`（{len(text.splitlines())} 行）" for path, text in tree.files)
