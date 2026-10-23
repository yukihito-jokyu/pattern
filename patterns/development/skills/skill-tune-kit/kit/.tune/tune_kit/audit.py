"""失敗を監査役に点検させ（audit）、指摘を検査し（audit-check）、人が選んだデータの直しを適用する（data-fix）。"""

from __future__ import annotations

import difflib
import json
from collections.abc import Sequence
from dataclasses import replace

from tune_kit import contracts, evidence, fsops, layout, plan, prompts, render, workspace
from tune_kit.errors import StageError


def _require_scope(
    where: layout.Layout, approved: workspace.Approved, number: int | None
) -> tuple[str, tuple[str, ...]]:
    """監査する版と分割。ラウンドの監査は今の版の学習用・検証用、最後の監査は最良の版のテスト用。"""
    decisions = workspace.load_decisions(where)
    current = workspace.compute_current(decisions)
    if number is None:
        tested = all(
            workspace.has_results(where, approved, version, (plan.TEST,)) for version in (layout.FIRST_VERSION, current)
        )
        if where.round_dir(len(decisions) + 1).is_dir() or not tested:
            raise StageError(
                "最後の監査は、元の版と最良の版のテスト用の評価が終わってから行います。status を実行してください"
            )
        return current, (plan.TEST,)
    if len(decisions) != number - 1:
        raise StageError(
            f"{number} 回目のラウンドは今のラウンドではありません（決定済み {len(decisions)} 回）。"
            "status を実行してください"
        )
    if not workspace.has_results(where, approved, current, (plan.TRAIN, plan.VAL)):
        raise StageError(f"今の版 {current} の学習用・検証用の評価が終わっていません。status を実行してください")
    if workspace.compute_stop_reason(
        approved.model, decisions, workspace.load_summary(where, approved, current, plan.VAL)
    ):
        raise StageError("ラウンドは終わっています。status を実行してください")
    return current, (plan.TRAIN, plan.VAL)


def _render_evidence(where: layout.Layout, approved: workspace.Approved, version: str, splits: Sequence[str]) -> str:
    failures = workspace.list_failures(where, approved, version, splits)
    checks = [plan.build_check_data(check) for check in approved.model.checks]
    lines = [f"# 監査の証拠（版 {version}、{', '.join(splits)} の不合格のケース）", ""]
    lines += [f"版のスキル: {where.display(where.version_dir(version))}", ""]
    lines += ["計画の検査（直すときの元の形）:", "", render.render_fence("\n".join(_render_json(checks)), "json"), ""]
    for case in approved.cases:
        if case.id in failures:
            lines.append(evidence.render_case(where, approved.model, case, approved.splits[case.id], failures[case.id]))
            source = "\n".join(_render_json(plan.build_case_data(case)))
            lines += ["ケースの JSON（直すときの元の形）:", "", render.render_fence(source, "json"), ""]
    return "\n".join(lines) + "\n"


def _write_prompt(
    where: layout.Layout, approved: workspace.Approved, number: int | None, version: str, problems: Sequence[str]
) -> None:
    directory = where.audit_dir(number)
    splits = (plan.TEST,) if number is None else (plan.TRAIN, plan.VAL)
    failing = workspace.list_failing_cases(where, approved, version, splits)
    scope = f"版 {version}（{where.display(where.version_dir(version))}）の {', '.join(splits)} で不合格だったケース"
    values = {
        "goal": approved.model.goal,
        "mode": approved.model.mode,
        "scope": scope,
        "evidence_path": where.display(directory / layout.AUDIT_EVIDENCE_FILE),
        "audit_path": where.display(directory / layout.AUDIT_FILE),
        "check_ids": ", ".join(check.id for check in approved.model.checks) or render.MISSING,
        "case_ids": ", ".join(failing),
        "problems": render.render_bullets(list(problems)),
    }
    fsops.write_text(directory / layout.AUDIT_PROMPT_FILE, prompts.render_prompt("auditor", values))


def _build_label(number: int | None, version: str) -> str:
    if number is None:
        return f"最後の監査（最良の版 {version} のテスト用。報告のみ）"
    return f"{number} 回目のラウンドの監査（今の版 {version} の学習用・検証用）"


def audit(where: layout.Layout, number: int | None) -> str:
    approved = workspace.load_approved(where)
    version, splits = _require_scope(where, approved, number)
    directory = where.audit_dir(number)
    if (directory / layout.AUDIT_PROMPT_FILE).is_file() or (directory / layout.AUDIT_FILE).is_file():
        raise StageError("監査は準備済みです。status を実行してください")
    failing = workspace.list_failing_cases(where, approved, version, splits)
    if not failing:
        fsops.write_json(directory / layout.AUDIT_FILE, {"findings": []})
        fsops.write_text(
            directory / layout.AUDIT_MD_FILE,
            f"# {_build_label(number, version)}\n\n不合格のケースが無いので、監査を省いた。\n",
        )
        return f"不合格のケースが無いので、監査を省きました（{where.display(directory / layout.AUDIT_MD_FILE)}）"
    fsops.write_text(directory / layout.AUDIT_EVIDENCE_FILE, _render_evidence(where, approved, version, splits))
    _write_prompt(where, approved, number, version, [])
    return f"監査の準備: 不合格のケース {len(failing)} 件（{', '.join(failing)}）"


def _render_json(data: object) -> list[str]:
    return json.dumps(data, ensure_ascii=False, indent=2).splitlines()


def _render_fix(approved: workspace.Approved, finding: contracts.Finding) -> list[str]:
    if finding.fix_case is not None:
        original = approved.find_case(finding.case_id)
        before = _render_json(plan.build_case_data(original)) if original is not None else []
        after = _render_json(plan.build_case_data(finding.fix_case))
        title = f"ケース {finding.case_id} を直す（このケースの結果が古くなり、今の版で評価し直す）"
    elif finding.fix_check is not None:
        check_id = finding.fix_check.id
        original_check = next((check for check in approved.model.checks if check.id == check_id), None)
        before = _render_json(plan.build_check_data(original_check)) if original_check is not None else []
        after = _render_json(plan.build_check_data(finding.fix_check))
        title = f"計画の検査 {check_id} を直す（この検査を当てる全ケースの結果が古くなる。テスト用の採点にも及ぶ）"
    else:
        return []
    diff = "\n".join(difflib.unified_diff(before, after, "直す前", "直した後", lineterm=""))
    return [f"## {finding.id} の直し", "", title, "", render.render_fence(diff, "diff"), ""]


def _render_audit(
    where: layout.Layout, approved: workspace.Approved, number: int | None, version: str, found: contracts.Audit
) -> str:
    rows = [
        [
            f.id,
            f.case_id,
            approved.splits.get(f.case_id, render.MISSING),
            f.cause,
            f.summary,
            f.evidence,
            "あり" if f.fixable else "なし",
        ]
        for f in found.findings
    ]
    lines = [
        f"# {_build_label(number, version)}",
        "",
        f"証拠: {where.display(where.audit_dir(number) / layout.AUDIT_EVIDENCE_FILE)}",
        "",
    ]
    lines += [
        render.render_table(["ID", "ケース", "分割", "原因", "要約", "根拠", "直し"], rows) if rows else "指摘なし",
        "",
    ]
    for finding in found.findings:
        lines += _render_fix(approved, finding)
    return "\n".join(lines)


def audit_check(where: layout.Layout, number: int | None) -> str:
    approved = workspace.load_approved(where)
    version, splits = _require_scope(where, approved, number)
    directory = where.audit_dir(number)
    if not (directory / layout.AUDIT_FILE).is_file():
        raise StageError(
            f"{where.display(directory / layout.AUDIT_FILE)} がありません。status の指示で監査役を起動してください"
        )
    originals = workspace.list_failing_cases(where, approved, version, splits)
    problems = workspace.list_audit_problems(where, number, approved, originals)
    if problems:
        fsops.remove_tree(directory / layout.AUDIT_FILE)
        _write_prompt(where, approved, number, version, problems)
        lines = "\n".join(f"  - {problem}" for problem in problems)
        raise StageError(
            f"監査に {len(problems)} 件の問題がありました。プロンプトに問題を書き足したので、"
            f"status の指示で監査役をもう一度起動してください:\n{lines}"
        )
    found = workspace.load_audit(where, number, approved, originals)
    fsops.write_text(directory / layout.AUDIT_MD_FILE, _render_audit(where, approved, number, version, found))
    fixable = sum(1 for finding in found.findings if finding.fixable)
    written = where.display(directory / layout.AUDIT_MD_FILE)
    return f"監査に問題はありません（指摘 {len(found.findings)} 件、直しの提案 {fixable} 件）。{written} を書きました"


def _build_fixed(
    model: plan.Plan, cases: Sequence[plan.Case], chosen: Sequence[contracts.Finding]
) -> tuple[plan.Plan, tuple[plan.Case, ...]]:
    case_fixes = {f.case_id: f.fix_case for f in chosen if f.fix_case is not None}
    check_fixes = {f.fix_check.id: f.fix_check for f in chosen if f.fix_check is not None}
    fixed_cases = tuple(case_fixes.get(case.id) or case for case in cases)
    fixed_checks = tuple(check_fixes.get(check.id, check) for check in model.checks)
    return replace(model, checks=fixed_checks), fixed_cases


def _check_fixed(
    where: layout.Layout, model: plan.Plan, cases: Sequence[plan.Case], splits: dict[str, str]
) -> list[str]:
    problems = plan.check_dataset(model, cases) + workspace.check_files(where, model, cases)
    after = workspace.compute_splits(model, cases)
    problems += [
        f"直すとケース {case_id} の分割が変わります" for case_id, split in splits.items() if after.get(case_id) != split
    ]
    return problems


def _write_approval(
    where: layout.Layout, approved: workspace.Approved, chosen: Sequence[contracts.Finding], number: int, today: str
) -> bool:
    """直した後の計画とケースで承認を記録し直す。テスト用のケースが変わったかを返す。"""
    dataset = workspace.load_dataset(where)
    splits = workspace.compute_splits(dataset.model, dataset.cases)
    case_shas = {case.id: workspace.compute_case_sha(where, dataset.model, case) for case in dataset.cases}
    test_sha = workspace.compute_test_sha(case_shas, splits)
    test_changed = test_sha != approved.approval.test_sha
    detail = f"r{number}: " + "、".join(f"{f.id}（{f.case_id}、{f.cause}）" for f in chosen)
    entry = contracts.HistoryEntry(on=today, kind=contracts.DATA_FIX_KIND, detail=detail, test_changed=test_changed)
    approval = replace(
        approved.approval,
        plan_sha=workspace.compute_plan_sha(where),
        dataset_sha=workspace.compute_dataset_sha(where),
        test_sha=test_sha,
        history=(*approved.approval.history, entry),
    )
    fsops.write_json(where.approval_path, contracts.build_approval_data(approval))
    return test_changed


def data_fix(where: layout.Layout, number: int, chosen_ids: Sequence[str], today: str) -> str:
    approved = workspace.load_approved(where)
    version, splits = _require_scope(where, approved, number)
    directory = where.round_dir(number)
    if not (directory / layout.AUDIT_MD_FILE).is_file() or workspace.load_fixes(where, number) is not None:
        raise StageError(
            f"{number} 回目のラウンドは、データの直しを決める段階ではありません。status を実行してください"
        )
    found = workspace.load_audit(
        where, number, approved, workspace.list_failing_cases(where, approved, version, splits)
    )
    fixable = {finding.id: finding for finding in found.findings if finding.fixable}
    unknown = [finding_id for finding_id in chosen_ids if finding_id not in fixable]
    if unknown:
        raise StageError(
            f"{', '.join(unknown)} は直しの提案ではありません（直しの提案: {', '.join(fixable) or 'なし'}）"
        )
    chosen = [fixable[finding_id] for finding_id in fixable if finding_id in chosen_ids]
    note = ""
    if chosen:
        model, cases = _build_fixed(approved.model, approved.cases, chosen)
        problems = _check_fixed(where, model, cases, approved.splits)
        if problems:
            lines = "\n".join(f"  - {problem}" for problem in problems)
            raise StageError(
                f"直しを適用すると計画に問題が出るため、適用しませんでした。適用する指摘を選び直してください:\n{lines}"
            )
        fsops.write_json(where.plan_path, plan.build_plan_data(model))
        fsops.write_json(where.cases_path, {"cases": [plan.build_case_data(case) for case in cases]})
        if _write_approval(where, approved, chosen, number, today):
            note = "。テスト用のケースの採点が変わったので、報告に記録します"
    rejected = [finding_id for finding_id in fixable if finding_id not in chosen_ids]
    # fixes.json は最後に書く。fixes.json の有無で「直しを決めた」を判定するため
    fsops.write_json(
        directory / layout.FIXES_FILE,
        contracts.build_fixes_data(contracts.Fixes(tuple(f.id for f in chosen), tuple(rejected))),
    )
    return f"データの直し: 適用 {len(chosen)} 件、見送り {len(rejected)} 件{note}"
