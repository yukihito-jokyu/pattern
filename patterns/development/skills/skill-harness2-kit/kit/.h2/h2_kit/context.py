"""編集・選択・振り返りのセッションに渡す証拠の木（context/）。証拠はファイルで全部渡す（STATE-03）。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from h2_kit import fsops, guards, layout, render, rollout, skilltree

NO_DECISION = "（この段は notes を返しませんでした）"
SKIPPED_SOURCE = frozenset({layout.CLAUDE_DIR, layout.GIT_DIR})


@dataclass(frozen=True)
class PoolEntry:
    """候補1つ。差分は証拠の木の今のスキル（harness）と比べて作る（harness2 と同じ）。"""

    label: str
    tree: skilltree.SkillTree
    view: rollout.RolloutView | None


@dataclass(frozen=True)
class Evidence:
    """証拠の木に入れるもの。空のものは書かず、道案内にも載せない。"""

    prompt: str
    source: Path
    rollouts: tuple[rollout.RolloutView, ...] = ()
    harness: skilltree.SkillTree | None = None
    base_harness: skilltree.SkillTree | None = None
    pool: tuple[PoolEntry, ...] = ()
    library: Path | None = None
    decisions: tuple[tuple[str, str], ...] = ()
    candidates: tuple[tuple[str, str], ...] = ()
    adoption: Mapping[str, object] | None = None


@dataclass(frozen=True)
class Built:
    """書いた証拠の木。layout は道案内（今回あるパスの一覧）。"""

    root: Path
    layout: str


def write_context(root: Path, evidence: Evidence, leak_globs: Sequence[str]) -> Built:
    """root（`context/`）を作り直して証拠を書き、答えに当たるものが無いことを確かめる。"""
    fsops.remove_tree(root)
    fsops.write_text(root / layout.TASK_FILE, evidence.prompt)
    lines = [f"`{layout.CONTEXT_DIR}/{layout.TASK_FILE}`"]
    lines += _write_source(root, evidence.source, leak_globs)
    lines += _write_named(
        root / layout.DECISIONS_DIR, [(label, notes or NO_DECISION) for label, notes in evidence.decisions]
    )
    lines += _write_named(
        root / layout.ROLLOUTS_DIR, [(view.label, rollout.read_trajectory(view)) for view in evidence.rollouts]
    )
    lines += _write_named(
        root / layout.DELIVERABLES_DIR, [(view.label, rollout.read_deliverable(view)) for view in evidence.rollouts]
    )
    lines += _write_tree(root / layout.HARNESS_DIR, evidence.harness)
    lines += _write_tree(root / layout.BASE_HARNESS_DIR, evidence.base_harness)
    lines += _write_pool(root / layout.POOL_DIR, evidence.pool, evidence.harness)
    lines += _write_library(root / layout.LIBRARY_DIR, evidence.library)
    lines += _write_named(root / layout.CANDIDATES_DIR, list(evidence.candidates))
    if evidence.adoption is not None:
        fsops.write_json(root / layout.ADOPTION_FILE, dict(evidence.adoption))
        lines.append(f"`{layout.CONTEXT_DIR}/{layout.ADOPTION_FILE}`")
    guards.require_clean_directory(root, leak_globs)
    return Built(root, render.render_bullets(lines))


def _write_source(root: Path, source: Path, leak_globs: Sequence[str]) -> list[str]:
    """タスクの材料を写す。leak_globs に当たるファイルと .claude/・.git/ は写さない。"""
    copied = 0
    for relative in fsops.list_files(source):
        if relative.split("/", 1)[0] in SKIPPED_SOURCE or guards.is_leak_path(relative, leak_globs):
            continue
        fsops.copy_file(source / relative, root / layout.SOURCE_DIR / relative)
        copied += 1
    return [f"`{layout.CONTEXT_DIR}/{layout.SOURCE_DIR}/`（{copied} ファイル）"] if copied else []


def _write_named(directory: Path, items: Sequence[tuple[str, str]]) -> list[str]:
    """`<名前>.md` のファイルを並べて書く。"""
    for name, text in items:
        fsops.write_text(directory / f"{name}{layout.MD_SUFFIX}", text)
    if not items:
        return []
    names = ", ".join(f"{name}{layout.MD_SUFFIX}" for name, _ in items)
    return [f"`{layout.CONTEXT_DIR}/{directory.name}/`: {names}"]


def _write_tree(directory: Path, tree: skilltree.SkillTree | None) -> list[str]:
    if tree is None:
        return []
    skilltree.write_tree(tree, directory)
    return [f"`{layout.CONTEXT_DIR}/{directory.name}/`（{len(tree.files)} ファイル）"]


def _write_pool(directory: Path, pool: Sequence[PoolEntry], current: skilltree.SkillTree | None) -> list[str]:
    for entry in pool:
        place = directory / entry.label
        skilltree.write_tree(entry.tree, place / layout.HARNESS_DIR)
        diff = skilltree.compute_diff(current or skilltree.build_tree({}), entry.tree)
        fsops.write_text(place / layout.HARNESS_DIFF_FILE, diff)
        if entry.view is not None:
            fsops.write_text(place / layout.POOL_ROLLOUT_FILE, rollout.read_trajectory(entry.view))
            fsops.write_text(place / layout.PRODUCED_FILE, rollout.read_deliverable(entry.view))
    if not pool:
        return []
    return [f"`{layout.CONTEXT_DIR}/{layout.POOL_DIR}/`: {', '.join(entry.label for entry in pool)}"]


def _write_library(directory: Path, library: Path | None) -> list[str]:
    if library is None or not (library / layout.INDEX_FILE).is_file():
        return []
    fsops.copy_tree(library, directory)
    count = len(fsops.list_dirs(directory))
    return [f"`{layout.CONTEXT_DIR}/{layout.LIBRARY_DIR}/`（{layout.INDEX_FILE} と {count} 件）"]
