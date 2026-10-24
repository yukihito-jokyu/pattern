"""前のタスクで選ばれたスキルの木と教訓（ライブラリ）。後のタスクの編集者は前のタスクの分だけを読む。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from h2_kit import contracts, fsops, guards, layout, render, skilltree

CUE_MARK = "- **cue**:"


@dataclass(frozen=True)
class Entry:
    """ライブラリの1件。教訓（experience）がある選択だけを残す（harness2 の has_experience）。"""

    task_id: str
    label: str
    why: str
    edits: str
    experience: contracts.Experience


def write_entry(library_dir: Path, tree: skilltree.SkillTree, entry: Entry) -> Path:
    """選ばれた木と EXPERIENCE.md を書き、INDEX.md をディスクから作り直す。"""
    guards.require_clean_tree(tree, ())
    text = render_experience(entry, tree)
    guards.require_clean_tree(skilltree.build_tree({layout.EXPERIENCE_FILE: text}), ())
    place = library_dir / entry.task_id
    skilltree.write_tree(tree, place / layout.ENTRY_SKILL_DIR)
    fsops.write_text(place / layout.EXPERIENCE_FILE, text)
    write_index(library_dir)
    return place


def copy_earlier(library_dir: Path, earlier: Sequence[str], target: Path) -> Path | None:
    """earlier のタスクの分だけを target に写す。1件も無ければ None（証拠の木に載せない）。"""
    fsops.remove_tree(target)
    names = [name for name in fsops.list_dirs(library_dir) if name in earlier]
    if not names:
        return None
    for name in names:
        fsops.copy_tree(library_dir / name, target / name)
    write_index(target)
    return target


def write_index(library_dir: Path) -> Path:
    """INDEX.md をディスクにある項目から作り直す。"""
    rows = [
        "# ライブラリ",
        "前の依頼のうち、スキルが選ばれ、移せる教訓が書かれたものを1件ずつ置いている。"
        "各件はスキルの木の全体と、選ばれた理由と教訓を持つ。この一覧を読み、関係がありそうな件を開く。",
    ]
    for name in fsops.list_dirs(library_dir):
        tree, _ = skilltree.read_tree(library_dir / name / layout.ENTRY_SKILL_DIR)
        cue = _find_cue(fsops.read_text_or_none(library_dir / name / layout.EXPERIENCE_FILE) or "")
        lines = [
            f"スキル: `{name}/{layout.ENTRY_SKILL_DIR}/`（{render_census(tree)}）",
            f"理由と教訓: `{name}/{layout.EXPERIENCE_FILE}`",
        ]
        rows += [f"## `{name}/`", render.render_bullets([*lines, f"cue: {cue}"] if cue else lines)]
    path = library_dir / layout.INDEX_FILE
    fsops.write_text(path, render.render_sections(rows))
    return path


def render_experience(entry: Entry, tree: skilltree.SkillTree) -> str:
    lesson = entry.experience
    parts = [
        f"# {entry.task_id}",
        render.render_bullets([f"選ばれた候補: `{entry.label}`", f"部品: {render_census(tree)}"]),
        "## 選ばれた理由",
        entry.why or "（理由はありません）",
        "## 各編集がしたこと",
        entry.edits or "（編集の行はありません）",
        "## 移せる教訓",
        "\n".join(
            [
                f"{CUE_MARK} {lesson.cue}",
                f"- **lesson**: {lesson.lesson}",
                f"- **evidence**: {lesson.evidence}",
                f"- **confidence**: {lesson.confidence or '（書かれていません）'}",
            ]
        ),
    ]
    return render.render_sections(parts)


def render_census(tree: skilltree.SkillTree) -> str:
    """木の部品の1行の数え上げ。"""
    skill = tree.find(layout.SKILL_FILE) or ""
    counts = [
        f"{layout.SKILL_FILE} {len(skill.splitlines())} 行",
        f"{layout.REFERENCES_DIR} {_compute_count(tree, layout.REFERENCES_DIR)}",
        f"{layout.SCRIPTS_DIR} {_compute_count(tree, layout.SCRIPTS_DIR)}",
        f"{layout.ASSETS_DIR} {_compute_count(tree, layout.ASSETS_DIR)}",
    ]
    return "、".join(counts)


def _compute_count(tree: skilltree.SkillTree, directory: str) -> int:
    return sum(1 for path in tree.paths if path.startswith(f"{directory}/"))


def _find_cue(text: str) -> str:
    return next((line[len(CUE_MARK) :].strip() for line in text.splitlines() if line.startswith(CUE_MARK)), "")
