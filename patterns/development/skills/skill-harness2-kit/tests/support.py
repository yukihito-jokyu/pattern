"""テストの部品。一時ディレクトリに、リポジトリ・スキル・プロファイル・タスクを作り、偽の claude を使う（TEST-02）。"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path

from h2_kit import cli, layout, planning, profile, skilltree, workspace

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_CLAUDE = FIXTURES / "fake_claude.py"
TEMPLATES = ROOT / "kit" / layout.H2_DIR / layout.TEMPLATES_DIR
SKILL_PATH = ".claude/skills/sample"
TARGET = "sample"
TASK_ID = "t1"
TODAY = "2026-10-23"
DELIVER_MARK = "答えを answer.md に書く"


def build_repo(test: unittest.TestCase) -> Path:
    """一時ディレクトリにリポジトリを作り、見本のスキルとひな形を置く。テストの後に消す。"""
    temporary = tempfile.TemporaryDirectory()
    test.addCleanup(temporary.cleanup)
    root = Path(temporary.name).resolve()
    shutil.copytree(FIXTURES / "skills" / "sample", root / SKILL_PATH)
    shutil.copytree(TEMPLATES, root / layout.H2_DIR / layout.TEMPLATES_DIR)
    return root


def build_where(root: Path) -> layout.Layout:
    return layout.Layout(root, TARGET)


def build_profile(**fields: object) -> dict[str, object]:
    """偽の claude を使うプロファイル。behaviors は fake_claude.py の振る舞いの名前、log は呼び出しの記録の置き場。"""
    data = profile.build_default_profile(SKILL_PATH)
    data.update(
        {
            "work": "議事録の日付をそろえて渡す",
            "domain_word": "議事録の整形",
            "deliverable_word": "整えた議事録",
            "k": 1,
            "width": 1,
            "claude": _build_command(fields.get("behaviors", ()), fields.get("log")),
        }
    )
    data.update({key: value for key, value in fields.items() if key not in ("behaviors", "log")})
    return data


def _build_command(behaviors: object, log: object) -> list[str]:
    names = [str(name) for name in behaviors] if isinstance(behaviors, (list, tuple)) else []
    command = [sys.executable, str(FAKE_CLAUDE), "behavior=" + ",".join(names)]
    return [*command, f"log={log}"] if log is not None else command


def build_model(**fields: object) -> profile.Profile:
    found, problems = profile.parse_profile(build_profile(**fields))
    if found is None:
        raise AssertionError(problems)
    return found


def write_profile(where: layout.Layout, **fields: object) -> dict[str, object]:
    data = build_profile(**fields)
    where.profile_path.parent.mkdir(parents=True, exist_ok=True)
    where.profile_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def write_task(where: layout.Layout, task_id: str = TASK_ID, files: dict[str, str] | None = None) -> workspace.Task:
    """タスクを書く。files は workspace/ に置く材料。"""
    prompt = f"{task_id} の議事録の日付をそろえてください"
    where.task_file(task_id).parent.mkdir(parents=True, exist_ok=True)
    where.task_file(task_id).write_text(prompt, encoding="utf-8")
    for name, text in (files or {"memo.md": "2026/1/5 に打ち合わせ\n"}).items():
        path = where.task_workspace(task_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return workspace.Task(task_id, prompt, where.task_dir(task_id))


def write_checks(where: layout.Layout, task_id: str, checks: list[dict[str, object]]) -> None:
    where.checks_path(task_id).write_text(json.dumps({"checks": checks}, ensure_ascii=False), encoding="utf-8")


def build_approved(test: unittest.TestCase, task_ids: Sequence[str] = (TASK_ID,), **fields: object) -> layout.Layout:
    """プロファイルとタスクを書き、check と approve まで済ませた対象。"""
    where = build_where(build_repo(test))
    write_profile(where, **fields)
    for task_id in task_ids:
        write_task(where, task_id)
    planning.check(where)
    planning.approve(where, TODAY)
    return where


def read_skill(where: layout.Layout) -> skilltree.SkillTree:
    tree, _ = skilltree.read_tree(where.skill_dir(SKILL_PATH))
    return tree


def read_log(log: Path) -> list[dict[str, object]]:
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def run_cli(root: Path, *argv: str) -> tuple[int, str, str]:
    """cli.main を動かし、終了コード・標準出力・標準エラーを返す。"""
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv), root)
    return code, out.getvalue(), err.getvalue()
