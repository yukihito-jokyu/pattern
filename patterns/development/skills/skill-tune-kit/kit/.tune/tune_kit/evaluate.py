"""1つの版をケースで評価する。作業場所を作り（eval-prepare）、機械の検査を回し（eval-collect）、結果を記録する（eval-score）。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from tune_kit import checks, contracts, fsops, layout, plan, proc, prompts, render, workspace
from tune_kit.errors import StageError

COMMAND_TIMEOUT_SEC = 300
NO_EXPECTED = "（この採点では正解を使わない）"


def _check_splits(splits: Sequence[str]) -> None:
    unknown = [name for name in splits if name not in plan.SPLITS]
    if unknown or not splits:
        raise StageError(
            f"--splits は {', '.join(plan.SPLITS)} をカンマ区切りで指定してください（{', '.join(unknown)}）"
        )


def _require_final(where: layout.Layout, approved: workspace.Approved, version: str) -> None:
    """テスト用は、ループが終わった後に元の版と最良の版だけで使う（STATE-03）。"""
    decisions = workspace.load_decisions(where)
    current = workspace.compute_current(decisions)
    finished = bool(
        not where.round_dir(len(decisions) + 1).is_dir()
        and workspace.has_results(where, approved, current, (plan.VAL,))
        and workspace.compute_stop_reason(
            approved.model, decisions, workspace.load_summary(where, approved, current, plan.VAL)
        )
    )
    if not finished:
        raise StageError("テスト用は、ラウンドが終わった後の最後の評価でだけ使います。status を実行してください")
    if version not in (layout.FIRST_VERSION, current):
        raise StageError(f"テスト用で評価できるのは {layout.FIRST_VERSION} と最良の版 {current} だけです")


def _list_runs(
    where: layout.Layout, approved: workspace.Approved, version: str, splits: Sequence[str]
) -> tuple[workspace.RunRef, ...]:
    """評価してよい版と分割なら、要る実行の一覧を返す。"""
    _check_splits(splits)
    if not where.version_dir(version).is_dir():
        raise StageError(f"版 {version} がありません（{where.display(where.version_dir(version))}）")
    if plan.TEST in splits:
        _require_final(where, approved, version)
    return workspace.list_runs(approved, version, splits)


def _build_skill_dir(where: layout.Layout, model: plan.Plan, run_dir: Path) -> Path:
    """実行役が従うスキルの置き場。repo の sandbox でスキルがリポジトリの中にあれば、sandbox の中の写し。"""
    skill_dir = where.skill_dir(model.target.skill_path)
    if model.sandbox == plan.REPO_SANDBOX and skill_dir.is_relative_to(where.root.resolve()):
        return run_dir / layout.SANDBOX_DIR / skill_dir.relative_to(where.root.resolve())
    return run_dir / layout.RUN_SKILL_DIR


def _write_run(where: layout.Layout, approved: workspace.Approved, ref: workspace.RunRef) -> None:
    run_dir = where.run_dir(ref.key)
    fsops.remove_tree(run_dir)
    sandbox = run_dir / layout.SANDBOX_DIR
    if approved.model.sandbox == plan.REPO_SANDBOX:
        fsops.copy_repo(where.root, sandbox)
    else:
        fsops.write_dir(sandbox)
    if where.input_dir(ref.case_id).is_dir():
        fsops.copy_tree_over(where.input_dir(ref.case_id), sandbox)
    skill_dir = _build_skill_dir(where, approved.model, run_dir)
    fsops.copy_tree(where.version_dir(ref.version), skill_dir)
    proc.run_git_baseline(sandbox)
    case = approved.find_case(ref.case_id)
    values = {
        "skill_dir": where.display(skill_dir),
        "skill_md": where.display(skill_dir / layout.SKILL_FILE),
        "sandbox": where.display(sandbox),
        "case_prompt": render.render_fence(case.prompt if case is not None else render.MISSING),
        "response_path": where.display(run_dir / layout.RESPONSE_FILE),
    }
    # プロンプトは最後に書く。プロンプトの有無で「準備済み」を判定するため
    fsops.write_text(run_dir / layout.EXECUTOR_PROMPT_FILE, prompts.render_prompt("executor", values))


def eval_prepare(where: layout.Layout, version: str, splits: Sequence[str]) -> str:
    approved = workspace.load_approved(where)
    refs = _list_runs(where, approved, version, splits)
    targets = [ref for ref in refs if workspace.compute_run_state(where, approved, ref) == workspace.UNPREPARED]
    for ref in targets:
        _write_run(where, approved, ref)
    return f"準備: {len(targets)} 件（{version}、{', '.join(splits)}。作業場所 {where.display(where.work_dir)}/）"


def _read_expected(where: layout.Layout, case: plan.Case, check: plan.Check) -> str | None:
    if check.value:
        return check.value
    if check.expected_file:
        return fsops.read_optional_text(where.expected_dir(case.id) / check.expected_file)
    return case.expected


def _read_target(check: plan.Check, sandbox: Path, response: str) -> str | None:
    if check.target == checks.RESPONSE_TARGET:
        return response
    return fsops.read_optional_text(sandbox / check.target[len(checks.FILE_TARGET_PREFIX) :])


def _evaluate_check(
    where: layout.Layout, case: plan.Case, check: plan.Check, sandbox: Path, response: str
) -> checks.Outcome:
    if check.kind == "exists":
        return checks.evaluate_exists((sandbox / check.target[len(checks.FILE_TARGET_PREFIX) :]).exists())
    if check.kind == "command":
        result = proc.run_command(check.run, sandbox, COMMAND_TIMEOUT_SEC)
        return checks.evaluate_command(result.code, result.tail)
    value = check.pattern if check.kind == "regex" else check.value
    return checks.evaluate_text_check(
        check.kind, _read_target(check, sandbox, response), value, _read_expected(where, case, check)
    )


def _render_expected(where: layout.Layout, case: plan.Case, judged: Sequence[plan.Check]) -> str:
    if not any(check.use_expected for check in judged):
        return NO_EXPECTED
    files = fsops.list_files(where.expected_dir(case.id))
    lines = [render.render_fence(case.expected or render.MISSING)]
    if files:
        lines += [
            "",
            "正解のファイル:",
            render.render_bullets([where.display(where.expected_dir(case.id) / name) for name in files]),
        ]
    return "\n".join(lines)


def _write_grader_prompt(
    where: layout.Layout, case: plan.Case, judged: Sequence[plan.Check], run_dir: Path, changed: Sequence[str]
) -> None:
    rows = [
        [check.id, check.severity, check.criterion, "使う" if check.use_expected else "使わない"] for check in judged
    ]
    changes = [*changed, f"差分: {where.display(run_dir / layout.CHANGES_FILE)}"] if changed else []
    values = {
        "case_prompt": render.render_fence(case.prompt),
        "expected": _render_expected(where, case, judged),
        "criteria": render.render_table(["ID", "重さ", "評価項目", "正解"], rows),
        "response_path": where.display(run_dir / layout.RESPONSE_FILE),
        "sandbox": where.display(run_dir / layout.SANDBOX_DIR),
        "changes": render.render_bullets(changes),
        "grade_path": where.display(run_dir / layout.GRADE_FILE),
        "judge_ids": ", ".join(check.id for check in judged),
    }
    fsops.write_text(run_dir / layout.GRADER_PROMPT_FILE, prompts.render_prompt("grader", values))


def _write_collected(where: layout.Layout, approved: workspace.Approved, ref: workspace.RunRef) -> None:
    case = approved.find_case(ref.case_id)
    if case is None:
        raise StageError(f"ケース {ref.case_id} がありません")
    run_dir = where.run_dir(ref.key)
    sandbox = run_dir / layout.SANDBOX_DIR
    response = fsops.read_text(run_dir / layout.RESPONSE_FILE)
    changed = proc.run_git_changed(sandbox)
    fsops.write_text(run_dir / layout.CHANGES_FILE, proc.run_git_diff(sandbox))
    applied = plan.list_case_checks(approved.model, case)
    outcomes = []
    for check in applied:
        if checks.KINDS[check.kind].judge:
            continue
        outcome = _evaluate_check(where, case, check, sandbox, response)
        outcomes.append(
            {
                "check_id": check.id,
                "kind": check.kind,
                "severity": check.severity,
                "passed": outcome.passed,
                "detail": outcome.detail,
                "by": contracts.MACHINE,
            }
        )
    judged = [check for check in applied if checks.KINDS[check.kind].judge]
    if judged:
        _write_grader_prompt(where, case, judged, run_dir, changed)
    # checks.json は最後に書く。checks.json の有無で「機械の検査が済んだ」を判定するため
    fsops.write_json(run_dir / layout.CHECKS_FILE, {"outcomes": outcomes, "changed": list(changed)})


def eval_collect(where: layout.Layout, version: str, splits: Sequence[str]) -> str:
    approved = workspace.load_approved(where)
    refs = _list_runs(where, approved, version, splits)
    targets = [ref for ref in refs if workspace.compute_run_state(where, approved, ref) == workspace.COLLECTING]
    for ref in targets:
        _write_collected(where, approved, ref)
    waiting = sum(1 for ref in refs if workspace.compute_run_state(where, approved, ref) == workspace.EXECUTING)
    note = f"。出力の無い実行が {waiting} 件あります" if waiting else ""
    return f"機械の検査: {len(targets)} 件（{version}、{', '.join(splits)}）{note}"


def _build_outcomes(
    approved: workspace.Approved, case: plan.Case, collected: contracts.Collected, grades: Sequence[contracts.Grade]
) -> list[dict[str, object]]:
    by_id: dict[str, dict[str, object]] = {
        outcome.check_id: {
            "check_id": outcome.check_id,
            "kind": outcome.kind,
            "severity": outcome.severity,
            "passed": outcome.passed,
            "detail": outcome.detail,
            "by": outcome.by,
        }
        for outcome in collected.outcomes
    }
    applied = plan.list_case_checks(approved.model, case)
    severities = {check.id: check.severity for check in applied}
    for grade in grades:
        by_id[grade.check_id] = {
            "check_id": grade.check_id,
            "kind": "judge",
            "severity": severities[grade.check_id],
            "passed": grade.passed,
            "detail": grade.reason,
            "by": contracts.GRADER,
        }
    return [by_id[check.id] for check in applied if check.id in by_id]


def _write_result(where: layout.Layout, approved: workspace.Approved, ref: workspace.RunRef) -> list[str]:
    """1回の実行の結果を記録する。採点の形に問題があれば grade.json を消し、問題を返す。"""
    run_dir = where.run_dir(ref.key)
    case = approved.find_case(ref.case_id)
    if case is None:
        return [f"ケース {ref.case_id} がありません"]
    judge_ids = workspace.list_judge_ids(approved, ref.case_id)
    problems = workspace.list_grade_problems(where, ref, judge_ids) if judge_ids else []
    if problems:
        fsops.remove_tree(run_dir / layout.GRADE_FILE)
        return [f"{where.display(run_dir / layout.GRADER_PROMPT_FILE)}: {problem}" for problem in problems]
    grades = workspace.load_grades(where, ref, judge_ids) if judge_ids else ()
    result_dir = where.result_dir(ref.version, ref.case_id, ref.run_no)
    result = {
        "version": ref.version,
        "case_id": ref.case_id,
        "run_no": ref.run_no,
        "case_sha": ref.case_sha,
        "outcomes": _build_outcomes(approved, case, workspace.load_collected(where, ref), grades),
        "changed": list(workspace.load_collected(where, ref).changed),
    }
    fsops.copy_file(run_dir / layout.RESPONSE_FILE, result_dir / layout.RESPONSE_FILE)
    fsops.copy_file(run_dir / layout.CHANGES_FILE, result_dir / layout.CHANGES_FILE)
    fsops.write_json(result_dir / layout.RESULT_FILE, result)
    # 作業場所は消す。採点役のプロンプトに正解があり、後の版の実行役に読ませないため
    fsops.remove_tree(run_dir)
    return []


def eval_score(where: layout.Layout, version: str, splits: Sequence[str]) -> str:
    approved = workspace.load_approved(where)
    refs = _list_runs(where, approved, version, splits)
    targets = [ref for ref in refs if workspace.compute_run_state(where, approved, ref) == workspace.SCORING]
    problems: list[str] = []
    for ref in targets:
        problems += _write_result(where, approved, ref)
    if problems:
        lines = "\n".join(f"  - {problem}" for problem in problems)
        raise StageError(
            f"採点の形に問題があった grade.json を消しました。status の指示で採点役をもう一度起動してください:\n{lines}"
        )
    done = sum(1 for ref in refs if workspace.compute_run_state(where, approved, ref) == workspace.DONE)
    return f"記録: {len(targets)} 件（{version}、{', '.join(splits)}。{done} / {len(refs)} 件が記録済み）"
