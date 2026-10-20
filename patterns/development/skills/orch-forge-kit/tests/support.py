"""テストの共通部品。見本のリポジトリを一時ディレクトリに作り、実行役とサブエージェントの代わりに出力を書く。"""

from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path

from forge_kit import (
    bundle,
    charter,
    cli,
    collect,
    contracts,
    execute,
    fsops,
    layout,
    prepare,
    proc,
    score,
    workspace,
)
from forge_kit.layout import Layout, Slot

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample-repo"
STREAMS = FIXTURES / "streams"
TODAY = "2026-10-20"
SKILL = "dev-orch"
NEW_SKILL = "new-orch"
IMPL_FILE = "inventory/remove.py"
IMPL_CODE = (
    '"""在庫を減らす。"""\n\n\ndef remove(stock: dict[str, int], name: str) -> dict[str, int]:\n    return stock\n'
)
TASK_PROMPT = "在庫から数を減らす関数を足して。在庫より多くは減らせないようにして"
ANALYST_LINE = "- 実装役に検査のコマンドを渡さずに任せること"


def make_repo(test: unittest.TestCase) -> Path:
    """見本のリポジトリを一時ディレクトリに写す。claude/ は .claude/ に名前を変える。"""
    base = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, base, ignore_errors=True)
    root = base / "repo"
    shutil.copytree(SAMPLE_REPO, root)
    (root / "claude").rename(root / ".claude")
    test.addCleanup(shutil.rmtree, proc.copies_root(root), ignore_errors=True)
    return root


def make_where(root: Path, target: str) -> Layout:
    return layout.make_layout(root, target, proc.copies_root(root))


def orch_charter(skill_name: str = SKILL) -> dict[str, object]:
    return {
        "schema_version": charter.SCHEMA_VERSION,
        "target": {"id": skill_name, "skill_name": skill_name},
        "purpose": "在庫の機能の追加を、実装役とレビュー役に分けて進め、検査を通して報告するようにしたい",
        "goals": [
            {
                "id": "G1",
                "statement": "依頼を満たし、検査を通す",
                "metrics": ["check_pass", "acceptance", "completion"],
            },
            {"id": "G2", "statement": "実装をサブエージェントに任せる", "metrics": ["delegation", "flow_conformance"]},
            {"id": "G3", "statement": "検査の設定を変えず、決まった形で報告する", "metrics": ["protected_untouched"]},
            {"id": "G4", "statement": "報告の形を守る", "metrics": ["report_format"]},
        ],
        "metrics": [
            {"id": "check_pass", "threshold": 1.0, "priority": "must"},
            {"id": "acceptance", "threshold": 1.0, "priority": "must"},
            {"id": "completion", "threshold": 1.0, "priority": "must"},
            {"id": "delegation", "threshold": 0.8, "priority": "must"},
            {"id": "flow_conformance", "threshold": 1.0, "priority": "should"},
            {"id": "protected_untouched", "threshold": 1.0, "priority": "must"},
            {"id": "report_format", "threshold": 1.0, "priority": "should"},
        ],
        "environment": {
            "check_command": "python3 check.py",
            "check_timeout_sec": 60,
            "protected_paths": ["check.py"],
            "skip_dirs": [],
            "link_dirs": [],
        },
        "executor": {
            "model": "",
            "allowed_tools": ["Bash(python3 check.py)"],
            "max_budget_usd": 1.0,
            "timeout_sec": 600,
            "parallel": 2,
        },
        "tasks": [
            {"id": "T1", "prompt": TASK_PROMPT, "acceptance": ["在庫を減らす関数がある"]},
            {"id": "H1", "prompt": "在庫を空にする関数を足して", "acceptance": ["在庫を空にする関数がある"]},
        ],
        "budget": {"agents": 2, "max_rounds": 2},
        "approval": None,
    }


def approve(where: Layout, data: Mapping[str, object]) -> None:
    approved = dict(data)
    approved["approval"] = {"sha256": charter.digest(approved), "approved_on": TODAY}
    fsops.write_json(where.charter_path, approved)


def approved_layout(test: unittest.TestCase, data: Mapping[str, object]) -> Layout:
    root = make_repo(test)
    target = data["target"]
    assert isinstance(target, dict)
    where = make_where(root, str(target["id"]))
    approve(where, data)
    return where


def run_cli(root: Path, *args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(args), root)
    return code, out.getvalue(), err.getvalue()


def fake_launcher(
    *, stream: str = "delegated", files: Mapping[str, str] | None = None, exit_code: int = 0, timed_out: bool = False
) -> proc.Launcher:
    """claude -p の代わり。コピーにファイルを書き、tests/fixtures/streams/<stream>.jsonl を実行の記録として返す。"""
    written = {IMPL_FILE: IMPL_CODE} if files is None else dict(files)
    text = fsops.read_text(STREAMS / f"{stream}.jsonl")

    def launch(args: Sequence[str], directory: Path, timeout_sec: int) -> proc.Launched:
        assert args[0] == execute.CLAUDE and timeout_sec > 0
        for relative, content in written.items():
            fsops.write_text(directory / relative, content)
        return proc.Launched(exit_code, timed_out, text, "")

    return launch


def act_designer(where: Layout) -> None:
    """設計役の代わりに、実装役とレビュー役の2つの役の design.json を書く。"""
    _data, model = workspace.load_charter(where)
    roles = [
        {
            "role": "implementer",
            "purpose": "変更を加え、検査を通す",
            "tools": ["Read", "Write", "Edit", "Bash"],
            "input": "依頼の文と検査のコマンド",
            "output": "変えたファイルの一覧を返答で返す",
        },
        {
            "role": "reviewer",
            "purpose": "変更が依頼と決まりを満たすかを確かめる",
            "tools": ["Read", "Glob", "Grep"],
            "input": "変えたファイルの一覧",
            "output": "承認か差し戻しを返答で返す",
        },
    ]
    steps = [
        {"id": "S1", "actor": "orchestrator", "action": "依頼を読み、決まらない点を人に確かめる", "parallel": False},
        {"id": "S2", "actor": "implementer", "action": "変更を加え、検査を通す", "parallel": False},
        {"id": "S3", "actor": "reviewer", "action": "変更を確かめる", "parallel": False},
        {"id": "S4", "actor": "orchestrator", "action": "結果をまとめて報告する", "parallel": False},
    ]
    design = {
        "schema_version": 1,
        "skill_name": model.target.skill_name,
        "summary": "機能の追加を、実装役とレビュー役に分けて進め、検査を通してから報告する",
        "roles": roles,
        "steps": steps,
        "checkpoints": [{"step": "S1", "question": "決まらない名前をどうするか", "default": "既存の書き方に合わせる"}],
        "report": ["変えたファイルの一覧", "検査の結果"],
    }
    fsops.write_json(where.design_path, design)


def act_builder(where: Layout) -> None:
    """構築役の代わりに、下書きの骨組みの TODO(forge) の行を、埋めた文に置き換える。"""
    _data, model = workspace.load_charter(where)
    for relative in bundle.files(where.draft_dir, model.target.skill_name):
        path = where.draft_dir / relative
        lines = ["埋めた説明。" if bundle.TODO_MARK in line else line for line in fsops.read_text(path).splitlines()]
        fsops.write_text(path, "\n".join(lines) + "\n")


def grade_all(where: Layout, slot: Slot, *, met: bool) -> None:
    """採点役の代わりに、採点役のプロンプトがある全実行の全項目を met で判定した grade.json を書く。"""
    for run in workspace.load_plan(where, slot).runs:
        if not where.grader_prompt_path(slot, run.run_id).is_file():
            continue
        targets = workspace.load_facts(where, slot, run.run_id).grade_targets
        items = [{"key": target.key, "met": met, "evidence": "テストの判定"} for target in targets]
        fsops.write_json(where.grade_path(slot, run.run_id), {"run_id": run.run_id, "items": items})


def scored_slot(where: Layout, slot: Slot, *, stream: str = "delegated", met: bool = True) -> contracts.Scores:
    """1回の評価を、準備から採点まで済ませる。"""
    prepare.prepare(where, slot)
    execute.execute(where, slot, fake_launcher(stream=stream))
    collect.collect(where, slot, parallel=1)
    grade_all(where, slot, met=met)
    score.score(where, slot)
    return workspace.load_scores(where, slot)


def act_analyst(where: Layout, round_no: int, *, line: str = ANALYST_LINE) -> None:
    """分析役の代わりに、候補のバンドルの SKILL.md の最後に1行足し、proposal.json を書く。"""
    _data, model = workspace.load_charter(where)
    skill_md = bundle.skill_dir(where.proposed_dir(round_no), model.target.skill_name) / layout.SKILL_FILE
    fsops.write_text(skill_md, fsops.read_text(skill_md) + line + "\n")
    change = contracts.Change("P1", "S4", ("delegation",), ("T1-a1: trace.md",), "実装役に渡すものを書いた")
    fsops.write_json(where.proposal_path(round_no), {"changes": [contracts.to_data(change)], "observations": []})


def baseline_scored(test: unittest.TestCase, *, stream: str = "main-edit", met: bool = False) -> Layout:
    """見本の dev-orch の charter で、最初の評価を採点まで済ませる。既定は must に未達がある評価。"""
    where = approved_layout(test, orch_charter())
    scored_slot(where, layout.make_slot("baseline", 1), stream=stream, met=met)
    return where
