"""答えを方法に入れない遮断。測定の語、採点の印、leak_globs のパスを拒む（STATE-04）。"""

from __future__ import annotations

import fnmatch
from collections.abc import Sequence
from pathlib import Path

from h2_kit import fsops, skilltree
from h2_kit.errors import LeakError

# harness2 の BenchPrompts が拒む語に、日本語の同じ意味の語を足した
MEASUREMENT_WORDS = (
    "benchmark",
    "evaluation",
    "grader",
    "rubric",
    "score",
    "採点",
    "正解",
    "スコア",
    "ルーブリック",
    "評価基準",
    "ベンチマーク",
)
# harness2 の GRADER_VERDICT_MARKERS に、judge が書く記録の印を足した
GRADER_MARKERS = (
    "deterministic_eval_summary",
    "deterministic_eval_result",
    "judge_scope_and_deterministic_status",
    "Judge findings on the rendered result",
    '"passed_count"',
    '"pass_rate"',
    '"test_pass_rate"',
    '"h2_judged"',
)
SHOWN_LIMIT = 8


def check_measurement_words(field: str, text: str) -> list[str]:
    """方法に渡す文が測定の語を含めば問題にする。仕事を書き、測り方を書かない。"""
    lowered = text.lower()
    return [
        f"{field} に測定の語 {word!r} があります。測り方ではなく、実務家に要る仕事を書いてください"
        for word in MEASUREMENT_WORDS
        if word in lowered
    ]


def check_text_markers(name: str, text: str) -> list[str]:
    """ファイルの名前と中身にある採点の印。"""
    problems = [f"{name} の名前に採点の印 {marker!r} があります" for marker in GRADER_MARKERS if marker in name]
    problems += [f"{name} に採点の印 {marker!r} があります" for marker in GRADER_MARKERS if marker in text]
    return problems


def check_tree_markers(tree: skilltree.SkillTree) -> list[str]:
    return [problem for path, text in tree.files for problem in check_text_markers(path, text)]


def check_directory(root: Path, patterns: Sequence[str]) -> list[str]:
    """ディレクトリの下の、leak_globs に当たるパスと採点の印。テキストでないファイルは名前だけを見る。"""
    problems: list[str] = []
    for relative in fsops.list_files(root):
        if is_leak_path(relative, patterns):
            problems.append(f"{relative} は leak_globs に当たります")
            continue
        problems += check_text_markers(relative, fsops.read_text_or_none(root / relative) or "")
    return problems


def is_leak_path(relative: str, patterns: Sequence[str]) -> bool:
    """harness2 と同じく、パス全体か、どこかのディレクトリの下のパスとして照合する。"""
    for pattern in patterns:
        normalized = pattern.replace("\\", "/").lstrip("./")
        if fnmatch.fnmatch(relative, normalized) or fnmatch.fnmatch(relative, f"*/{normalized}"):
            return True
    return False


def require_clean_directory(root: Path, patterns: Sequence[str]) -> Path:
    """証拠の木に答えが入っていれば LeakError を投げる。広げて黙らせず、入った経路を直す。"""
    problems = check_directory(root, patterns)
    if problems:
        raise LeakError(_render_leak(f"{root} に答えに当たるものがあります", problems))
    return root


def require_clean_tree(tree: skilltree.SkillTree, patterns: Sequence[str]) -> skilltree.SkillTree:
    problems = check_tree_markers(tree)
    problems += [f"{path} は leak_globs に当たります" for path in tree.paths if is_leak_path(path, patterns)]
    if problems:
        raise LeakError(_render_leak("スキルの木に答えに当たるものがあります", problems))
    return tree


def _render_leak(head: str, problems: Sequence[str]) -> str:
    shown = "、".join(problems[:SHOWN_LIMIT])
    more = f"（ほか {len(problems) - SHOWN_LIMIT} 件）" if len(problems) > SHOWN_LIMIT else ""
    return f"{head}: {shown}{more}"
