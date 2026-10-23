"""テストの部品。一時ディレクトリに、リポジトリ・計画・ケース・サブエージェントの出力を作る（TEST-02）。"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from collections.abc import Callable, Sequence
from pathlib import Path

from tune_kit import cli, contracts, fsops, layout, plan, workspace

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SKILL_PATH = ".claude/skills/sample"
TARGET = "sample"
ANSWER = "2026-01-05 に打ち合わせ"
WRONG = "2026/1/5 に打ち合わせ"
# 既定の10件（c01〜c10）の分割。種が同じなら常にこの分割になる（test_splitting が確かめる）
SPLITS = {
    "c01": "train",
    "c02": "train",
    "c03": "val",
    "c04": "test",
    "c05": "train",
    "c06": "train",
    "c07": "train",
    "c08": "val",
    "c09": "train",
    "c10": "test",
}
# 元の版 v0 が間違えるケース（学習用・検証用・テスト用から1件ずつ）
WRONG_IDS = ("c01", "c03", "c04")
LINE = "4. 年・月・日を2桁にそろえる"


def build_repo(test: unittest.TestCase) -> Path:
    """一時ディレクトリにリポジトリを作り、見本のスキルを置く。テストの後に消す。"""
    temporary = tempfile.TemporaryDirectory()
    test.addCleanup(temporary.cleanup)
    root = Path(temporary.name).resolve()
    shutil.copytree(FIXTURES / "sample-skill", root / SKILL_PATH)
    return root


def build_where(root: Path) -> layout.Layout:
    return layout.build_layout(root, TARGET)


def build_check(check_id: str, kind: str, severity: str = plan.MUST, **fields: object) -> dict[str, object]:
    return {"id": check_id, "kind": kind, "severity": severity, **fields}


def build_prompt(case_id: str) -> str:
    return f"{case_id} の議事録にある日付を、すべて ISO 8601 の形にそろえてください"


def build_case(case_id: str, group: str = "memo", expected: str | None = ANSWER, **fields: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": case_id,
        "group": group,
        "prompt": build_prompt(case_id),
        "expected": expected,
    }
    data.update(fields)
    return data


def build_plan(
    mode: str = plan.REFERENCE, checks: Sequence[dict[str, object]] = (), **budget: int
) -> dict[str, object]:
    data = plan.build_skeleton(TARGET, SKILL_PATH)
    data["goal"] = "日付を ISO 8601 にそろえる"
    data["mode"] = mode
    data["checks"] = list(checks) or [build_check("K1", "equals")]
    data["budget"] = {"runs_per_case": 1, "max_rounds": 3, "patience": 2, "parallel": 4, **budget}
    return data


def build_cases(count: int) -> list[dict[str, object]]:
    return [build_case(f"c{index:02d}") for index in range(1, count + 1)]


def write_dataset(root: Path, plan_data: dict[str, object], cases: Sequence[dict[str, object]]) -> layout.Layout:
    where = build_where(root)
    fsops.write_json(where.plan_path, plan_data)
    fsops.write_json(where.cases_path, {"cases": list(cases)})
    fsops.write_dir(where.files_dir)
    return where


def run_cli(root: Path, *args: str) -> tuple[int, str, str]:
    """補助 CLI を動かし、終了コード、標準出力、標準エラーを返す。"""
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main([*args, "--target", TARGET], root)
    return code, out.getvalue(), err.getvalue()


def run_ok(test: unittest.TestCase, root: Path, *args: str) -> str:
    code, out, err = run_cli(root, *args)
    test.assertEqual(code, 0, f"{args} が失敗した: {err}")
    return out


def run_approve(test: unittest.TestCase, root: Path) -> workspace.Approved:
    run_ok(test, root, "check-plan")
    run_ok(test, root, "approve")
    return workspace.load_approved(build_where(root))


def build_answer(case_id: str, version: str) -> str:
    """既定の返答。v0 は WRONG_IDS を間違え、v1 以降は全部正しく答える。"""
    return WRONG if version == layout.FIRST_VERSION and case_id in WRONG_IDS else ANSWER


def write_responses(
    where: layout.Layout, version: str, splits: Sequence[str], answer: Callable[[str, str], str]
) -> int:
    """出力の無い実行に、実行役の代わりに返答を書く。書いた件数を返す。"""
    approved = workspace.load_approved(where)
    written = 0
    for ref in workspace.list_runs(approved, version, splits):
        if workspace.compute_run_state(where, approved, ref) == workspace.EXECUTING:
            fsops.write_text(where.run_dir(ref.key) / layout.RESPONSE_FILE, answer(ref.case_id, version))
            written += 1
    return written


def write_grades(where: layout.Layout, version: str, splits: Sequence[str], passed: bool) -> int:
    """採点の無い実行に、採点役の代わりに grade.json を書く。"""
    approved = workspace.load_approved(where)
    written = 0
    for ref in workspace.list_runs(approved, version, splits):
        if workspace.compute_run_state(where, approved, ref) == workspace.GRADING:
            grades = [
                {"check_id": i, "passed": passed, "reason": "テスト"}
                for i in workspace.list_judge_ids(approved, ref.case_id)
            ]
            fsops.write_json(where.run_dir(ref.key) / layout.GRADE_FILE, {"grades": grades})
            written += 1
    return written


def run_eval(
    test: unittest.TestCase,
    root: Path,
    version: str,
    splits: Sequence[str],
    answer: Callable[[str, str], str] = build_answer,
    passed: bool = True,
) -> None:
    """1つの版の評価を、サブエージェントの出力を書きながら最後まで進める。"""
    where = build_where(root)
    args = ("--version", version, "--splits", ",".join(splits))
    run_ok(test, root, "eval-prepare", *args)
    write_responses(where, version, splits, answer)
    run_ok(test, root, "eval-collect", *args)
    write_grades(where, version, splits, passed)
    run_ok(test, root, "eval-score", *args)


def write_proposal(where: layout.Layout, number: int, changes: Sequence[dict[str, object]], notes: str = "") -> None:
    fsops.write_json(where.round_dir(number) / layout.PROPOSAL_FILE, {"changes": list(changes), "notes": notes})


def write_skill_line(where: layout.Layout, version: str, line: str) -> None:
    """版の SKILL.md の末尾に1行足す（学習役の直しの代わり）。"""
    path = where.version_dir(version) / layout.SKILL_FILE
    fsops.write_text(path, fsops.read_text(path) + line + "\n")


def write_audit(where: layout.Layout, number: int | None, findings: Sequence[dict[str, object]]) -> None:
    fsops.write_json(where.audit_dir(number) / layout.AUDIT_FILE, {"findings": list(findings)})


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def list_status(root: Path) -> list[str]:
    code, out, err = run_cli(root, "status")
    if code != 0:
        raise AssertionError(err)
    return out.strip().splitlines()


def find_line(lines: Sequence[str], prefix: str) -> str:
    return next((line for line in lines if line.startswith(prefix)), "")


def build_approved_repo(test: unittest.TestCase, plan_data: dict[str, object] | None = None) -> Path:
    """既定の10件の計画を承認したリポジトリ。"""
    root = build_repo(test)
    write_dataset(root, plan_data or build_plan(), build_cases(10))
    run_approve(test, root)
    return root


def build_finding(number: int, case_id: str, cause: str = "skill", fix: object = None) -> dict[str, object]:
    return {"id": f"F{number}", "case_id": case_id, "cause": cause, "summary": "要約", "evidence": "根拠", "fix": fix}


def run_until_learn(test: unittest.TestCase, root: Path, number: int = 1) -> None:
    """今の版の評価から、ラウンドの監査と直しの見送りを経て、学習の準備まで進める。"""
    where = build_where(root)
    if number == 1:
        run_eval(test, root, layout.FIRST_VERSION, (plan.TRAIN, plan.VAL))
    run_ok(test, root, "audit", "--round", str(number))
    if not (where.round_dir(number) / layout.AUDIT_MD_FILE).is_file():
        approved = workspace.load_approved(where)
        current = workspace.compute_current(workspace.load_decisions(where))
        failing = workspace.list_failing_cases(where, approved, current, (plan.TRAIN, plan.VAL))
        write_audit(where, number, [build_finding(index, case_id) for index, case_id in enumerate(failing, 1)])
        run_ok(test, root, "audit-check", "--round", str(number))
    run_ok(test, root, "data-fix", "--round", str(number), "--none")
    run_ok(test, root, "learn", "--round", str(number))


def run_round(test: unittest.TestCase, root: Path, number: int, line: str = LINE) -> str:
    """学習役の代わりに候補へ1行足し、提案の検査、候補の評価、採否まで進める。decide の出力を返す。"""
    where = build_where(root)
    version = layout.build_version(number)
    write_skill_line(where, version, line)
    write_proposal(where, number, [{"file": "SKILL.md", "summary": "手順を足した", "cause": "桁", "cases": ["c01"]}])
    run_ok(test, root, "learn-check", "--round", str(number))
    run_eval(test, root, version, (plan.TRAIN, plan.VAL))
    return run_ok(test, root, "decide", "--round", str(number))


def run_final(test: unittest.TestCase, root: Path, best: str) -> None:
    """元の版と最良の版のテスト用の評価と、最後の監査まで進める。"""
    where = build_where(root)
    run_eval(test, root, layout.FIRST_VERSION, (plan.TEST,))
    if best != layout.FIRST_VERSION:
        run_eval(test, root, best, (plan.TEST,))
    run_ok(test, root, "audit", "--final")
    if not (where.final_dir / layout.AUDIT_MD_FILE).is_file():
        approved = workspace.load_approved(where)
        failing = workspace.list_failing_cases(where, approved, best, (plan.TEST,))
        write_audit(where, None, [build_finding(index, case_id) for index, case_id in enumerate(failing, 1)])
        run_ok(test, root, "audit-check", "--final")


def run_to_report(test: unittest.TestCase, root: Path) -> None:
    """1ラウンドで v1 を採用し、最後の評価を経て報告まで進める。"""
    run_until_learn(test, root)
    run_round(test, root, 1)
    run_final(test, root, "v1")
    run_ok(test, root, "report")


def build_decisions(adopted: Sequence[bool]) -> tuple[contracts.DecisionRecord, ...]:
    """ラウンドごとの採否から決定の並びを作る。"""
    decisions = []
    current = layout.FIRST_VERSION
    for number, flag in enumerate(adopted, 1):
        candidate = layout.build_version(number)
        decisions.append(contracts.DecisionRecord(number, current, candidate, flag, "理由", None, None, None, None))
        current = candidate if flag else current
    return tuple(decisions)
