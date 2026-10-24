"""候補のスキルの木を実行の前に検証する。壊れた候補に予算を使わない（STATE-06）。"""

from __future__ import annotations

import re

from h2_kit import guards, layout, skilltree

MAX_SKILL_LINES = 500
MAX_DESCRIPTION = 1024
INJECTION = "!`"
_PART = r"[A-Za-z0-9][A-Za-z0-9._-]*"
NAMED_PATH = re.compile(
    rf"(?:(?<=\}}/)|(?<![\w./-]))(?:{layout.REFERENCES_DIR}|{layout.SCRIPTS_DIR}|{layout.ASSETS_DIR})/{_PART}"
)
HEADING = re.compile(r"^#+\s+(.+?)\s*$", re.M)


def check_tree(tree: skilltree.SkillTree, base: skilltree.SkillTree, rejected: list[str]) -> list[str]:
    """候補の問題の一覧。元の木に既にある問題は数えない（候補が持ち込んだ問題だけを差し戻す）。"""
    known = set(_list_problems(base, base))
    found = [f"{path} は編集面の外にあるので捨てられます" for path in rejected]
    found += [problem for problem in _list_problems(tree, base) if problem not in known]
    return found


def build_autolinked(tree: skilltree.SkillTree) -> tuple[skilltree.SkillTree, list[str]]:
    """SKILL.md で名指しされていない references/ のファイルに、読む場面の行を足す（harness2 の autotrigger）。

    足すと SKILL.md が上限の行数を超える場合は足さない。
    """
    skill = tree.find(layout.SKILL_FILE)
    if skill is None:
        return tree, []
    linked: list[str] = []
    for path, text in tree.files:
        if not path.startswith(f"{layout.REFERENCES_DIR}/") or path in skill:
            continue
        line = f"- {_find_topic(text, path)}を確かめるときは `{path}` を読む。"
        if len((skill.rstrip() + "\n" + line).splitlines()) > MAX_SKILL_LINES:
            continue
        skill = skill.rstrip() + "\n" + line + "\n"
        linked.append(path)
    return (skilltree.build_replaced(tree, layout.SKILL_FILE, skill), linked) if linked else (tree, [])


def _list_problems(tree: skilltree.SkillTree, base: skilltree.SkillTree) -> list[str]:
    skill = tree.find(layout.SKILL_FILE)
    if skill is None:
        return [f"{layout.SKILL_FILE} がありません。消さずに編集してください"]
    problems = _check_frontmatter(skill, base.find(layout.SKILL_FILE) or "")
    if len(skill.splitlines()) > MAX_SKILL_LINES:
        problems.append(
            f"{layout.SKILL_FILE} が {MAX_SKILL_LINES} 行を超えています。詳細は references/ に移してください"
        )
    problems += [
        f"{path} が {layout.SKILL_FILE} で名指しされていません。読む場面を書いた行を足してください"
        for path in tree.paths
        if path.startswith(f"{layout.REFERENCES_DIR}/") and path not in skill
    ]
    problems += _check_named_paths(tree)
    if _compute_injections(tree) > _compute_injections(base):
        problems.append(
            f"動的な挿入（{INJECTION}…`）が増えています。読み込みの前にコマンドが動くので足さないでください"
        )
    problems += _check_scripts(tree)
    problems += guards.check_tree_markers(tree)
    return problems


def _check_frontmatter(skill: str, base_skill: str) -> list[str]:
    found = skilltree.parse_frontmatter(skill)
    if found is None:
        return [f"{layout.SKILL_FILE} の先頭に frontmatter（--- で囲んだ行）がありません"]
    problems: list[str] = []
    before = skilltree.parse_frontmatter(base_skill)
    if before is not None and found.entries != before.entries:
        problems.append(f"{layout.SKILL_FILE} の frontmatter の description 以外の行を変えないでください")
    if not found.description:
        problems.append(f"{layout.SKILL_FILE} の description が空です")
    if len(found.description) > MAX_DESCRIPTION:
        problems.append(f"{layout.SKILL_FILE} の description が {MAX_DESCRIPTION} 字を超えています")
    if "<" in found.description or ">" in found.description:
        problems.append(f"{layout.SKILL_FILE} の description に < か > があります")
    return problems


def _check_named_paths(tree: skilltree.SkillTree) -> list[str]:
    """本文と参照ファイルで名指ししたパスが木にあるか。文末の句点はパスに含めない。"""
    problems: list[str] = []
    for path, text in tree.files:
        if path != layout.SKILL_FILE and not path.startswith(f"{layout.REFERENCES_DIR}/"):
            continue
        for named in sorted({match.rstrip(".") for match in NAMED_PATH.findall(text)}):
            if named not in tree.paths:
                problems.append(
                    f"{path} が名指しした {named} が木にありません。同じ提案で足すか、名指しを消してください"
                )
    return problems


def _check_scripts(tree: skilltree.SkillTree) -> list[str]:
    problems: list[str] = []
    for path, text in tree.files:
        if not path.endswith(layout.PY_SUFFIX):
            continue
        try:
            compile(text, path, "exec")
        except (SyntaxError, ValueError) as exc:
            problems.append(f"{path} が Python としてコンパイルできません: {exc}")
    return problems


def _compute_injections(tree: skilltree.SkillTree) -> int:
    return sum(text.count(INJECTION) for _, text in tree.files)


def _find_topic(text: str, path: str) -> str:
    found = HEADING.search(text)
    return found.group(1) if found else path.rsplit("/", 1)[-1]
