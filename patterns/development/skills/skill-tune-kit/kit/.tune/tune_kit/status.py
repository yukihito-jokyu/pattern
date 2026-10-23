"""作業場所のファイルから今の段階を求め、次に実行するコマンドか、起動するサブエージェントを示す。ファイルは書かない。"""

from __future__ import annotations

from collections.abc import Sequence

from tune_kit import contracts, layout, plan, render, workspace

# status の行の書き出し。スキルはこの書き出しで行を読み分けるので、足すときは SKILL.md の表も変える（OPS-01、PROC-02）
LINE_KINDS = (
    "対象:",
    "ラウンド:",
    "段階:",
    "問題:",
    "次:",
    "job ",
    "その後:",
    "承認なら:",
    "適用するなら:",
    "適用しないなら:",
)
APPLY_PLACEHOLDER = " --apply '<適用する指摘の ID をカンマ区切り>'"
LAUNCH = "次: 下の job をすべて Agent ツールで1つのメッセージにまとめて起動し、全員の完了を待つ"


def _build_command(where: layout.Layout, name: str, extra: str = "") -> str:
    return f"{layout.CLI} {name} --target {where.target}{extra}"


def _build_after(where: layout.Layout) -> str:
    return f"その後: {_build_command(where, 'status')}"


def _build_eval_args(version: str, splits: Sequence[str]) -> str:
    return f" --version {version} --splits {','.join(splits)}"


def _build_eval_steps(
    where: layout.Layout, approved: workspace.Approved, version: str, splits: Sequence[str], label: str
) -> list[str]:
    """1つの版の評価の次の手。評価が終わっていれば空。"""
    refs = workspace.list_runs(approved, version, splits)
    states = [(ref, workspace.compute_run_state(where, approved, ref)) for ref in refs]
    pending = [ref for ref, state in states if state != workspace.DONE]
    if not pending:
        return []
    args = _build_eval_args(version, splits)
    progress = f"（残り {len(pending)} / {len(refs)} 件）"
    if any(state == workspace.UNPREPARED for _ref, state in states):
        return [f"段階: {label}の準備{progress}", f"次: {_build_command(where, 'eval-prepare', args)}"]
    limit = approved.model.budget.parallel
    executing = [ref for ref, state in states if state == workspace.EXECUTING]
    if executing:
        jobs = [
            render.render_job(
                contracts.AGENTS["executor"],
                f"run-{ref.key[:8]}",
                _build_prompt(where, ref, layout.EXECUTOR_PROMPT_FILE),
            )
            for ref in executing[:limit]
        ]
        return [f"段階: {label}の実行（出力の無い実行 {len(executing)} 件）", LAUNCH, *jobs, _build_after(where)]
    if any(state == workspace.COLLECTING for _ref, state in states):
        return [f"段階: {label}の機械の検査{progress}", f"次: {_build_command(where, 'eval-collect', args)}"]
    grading = [ref for ref, state in states if state == workspace.GRADING]
    if grading:
        jobs = [
            render.render_job(
                contracts.AGENTS["grader"], f"grade-{ref.key[:8]}", _build_prompt(where, ref, layout.GRADER_PROMPT_FILE)
            )
            for ref in grading[:limit]
        ]
        return [f"段階: {label}の採点（採点の無い実行 {len(grading)} 件）", LAUNCH, *jobs, _build_after(where)]
    return [f"段階: {label}の集計{progress}", f"次: {_build_command(where, 'eval-score', args)}"]


def _build_prompt(where: layout.Layout, ref: workspace.RunRef, name: str) -> str:
    return where.display(where.run_dir(ref.key) / name)


def _build_audit_steps(where: layout.Layout, number: int | None) -> list[str]:
    """監査の次の手。監査が終わっていれば空。number が None なら最後の監査。"""
    directory = where.audit_dir(number)
    extra = " --final" if number is None else f" --round {number}"
    label = "最後の監査（テスト用、報告のみ）" if number is None else f"{number} 回目のラウンドの監査"
    if not (directory / layout.AUDIT_FILE).is_file():
        if not (directory / layout.AUDIT_PROMPT_FILE).is_file():
            return [f"段階: {label}の準備", f"次: {_build_command(where, 'audit', extra)}"]
        job = render.render_job(
            contracts.AGENTS["auditor"],
            f"audit-{'final' if number is None else number}",
            where.display(directory / layout.AUDIT_PROMPT_FILE),
        )
        return [f"段階: {label}", LAUNCH, job, f"その後: {_build_command(where, 'audit-check', extra)}"]
    if not (directory / layout.AUDIT_MD_FILE).is_file():
        return [f"段階: {label}の検査", f"次: {_build_command(where, 'audit-check', extra)}"]
    return []


def _build_fix_steps(where: layout.Layout, approved: workspace.Approved, number: int) -> list[str]:
    if workspace.load_fixes(where, number) is not None:
        return []
    current = workspace.compute_current(workspace.load_decisions(where))
    originals = workspace.list_failing_cases(where, approved, current, (plan.TRAIN, plan.VAL))
    audit = workspace.load_audit(where, number, approved, originals)
    fixable = [finding.id for finding in audit.findings if finding.fixable]
    command = f" --round {number}"
    if not fixable:
        return [
            f"段階: {number} 回目のラウンドのデータの直し（直しの提案なし）",
            f"次: {_build_command(where, 'data-fix', command + ' --none')}",
        ]
    audit_md = where.display(where.round_dir(number) / layout.AUDIT_MD_FILE)
    return [
        f"段階: {number} 回目のラウンドのデータの直し（人が決める。直しの提案 {', '.join(fixable)}）",
        f"次: {audit_md} を人に見せ、適用する指摘を AskUserQuestion で聞く",
        f"適用するなら: {_build_command(where, 'data-fix', command + APPLY_PLACEHOLDER)}",
        f"適用しないなら: {_build_command(where, 'data-fix', command + ' --none')}",
    ]


def _build_learn_steps(where: layout.Layout, approved: workspace.Approved, number: int) -> list[str]:
    directory = where.round_dir(number)
    extra = f" --round {number}"
    if not (directory / layout.LEARNER_PROMPT_FILE).is_file():
        return [f"段階: {number} 回目のラウンドの学習の準備", f"次: {_build_command(where, 'learn', extra)}"]
    if not (directory / layout.PROPOSAL_FILE).is_file():
        job = render.render_job(
            contracts.AGENTS["learner"], f"learn-{number}", where.display(directory / layout.LEARNER_PROMPT_FILE)
        )
        return [
            f"段階: {number} 回目のラウンドの学習",
            LAUNCH,
            job,
            f"その後: {_build_command(where, 'learn-check', extra)}",
        ]
    if not (directory / layout.PROPOSAL_MD_FILE).is_file():
        return [f"段階: {number} 回目のラウンドの提案の検査", f"次: {_build_command(where, 'learn-check', extra)}"]
    train_ids = [case.id for case in approved.list_cases(plan.TRAIN)]
    if workspace.load_proposal(where, number, train_ids).changes:
        version = layout.build_version(number)
        steps = _build_eval_steps(
            where, approved, version, (plan.TRAIN, plan.VAL), f"{number} 回目の候補 {version} の評価"
        )
        if steps:
            return steps
    return [
        f"段階: {number} 回目のラウンドの採否（検証用のスコアで機械的に決める）",
        f"次: {_build_command(where, 'decide', extra)}",
    ]


def _build_round_steps(where: layout.Layout, approved: workspace.Approved, number: int, current: str) -> list[str]:
    steps = _build_audit_steps(where, number) or _build_fix_steps(where, approved, number)
    if steps:
        return steps
    steps = _build_eval_steps(
        where, approved, current, (plan.TRAIN, plan.VAL), f"データを直した後の今の版 {current} の評価"
    )
    return steps or _build_learn_steps(where, approved, number)


def _build_final_steps(where: layout.Layout, approved: workspace.Approved, best: str, reason: str) -> list[str]:
    first = layout.FIRST_VERSION
    steps = _build_eval_steps(
        where, approved, first, (plan.TEST,), f"最後の評価（{reason}）: 元の版 {first} のテスト用"
    )
    if not steps and best != first:
        steps = _build_eval_steps(
            where, approved, best, (plan.TEST,), f"最後の評価（{reason}）: 最良の版 {best} のテスト用"
        )
    steps = steps or _build_audit_steps(where, None)
    if steps:
        return steps
    report_md = where.display(where.report_path)
    if not where.report_path.is_file():
        return ["段階: 報告", f"次: {_build_command(where, 'report')}"]
    if best != first and workspace.load_applied(where) is None:
        return [
            f"段階: 適用（人が決める。最良の版は {best}）",
            f"次: {report_md} の要点を人に見せ、最良の版 {best} を対象スキル {approved.model.target.skill_path} に"
            "適用するかを AskUserQuestion で聞く",
            f"適用するなら: {_build_command(where, 'apply')}",
            f"適用しないなら: {_build_command(where, 'apply', ' --skip')}",
        ]
    return ["段階: 完了", f"次: {report_md} の要点を人に見せる"]


def _build_loop_steps(where: layout.Layout, approved: workspace.Approved) -> list[str]:
    first = layout.FIRST_VERSION
    # r1 ができた後の v0 の評価のやり直しは、ラウンドの手順が受け持つ
    if not where.round_dir(1).is_dir():
        steps = _build_eval_steps(
            where, approved, first, (plan.TRAIN, plan.VAL), f"最初の評価（{first} の学習用・検証用）"
        )
        if steps:
            return steps
    decisions = workspace.load_decisions(where)
    current = workspace.compute_current(decisions)
    number = len(decisions) + 1
    if where.round_dir(number).is_dir():
        return _build_round_steps(where, approved, number, current)
    steps = _build_eval_steps(where, approved, current, (plan.TRAIN, plan.VAL), f"今の版 {current} の評価のやり直し")
    if steps:
        return steps
    reason = workspace.compute_stop_reason(
        approved.model, decisions, workspace.load_summary(where, approved, current, plan.VAL)
    )
    if reason:
        return _build_final_steps(where, approved, current, reason)
    return [f"段階: {number} 回目のラウンドの監査の準備", f"次: {_build_command(where, 'audit', f' --round {number}')}"]


def _build_plan_steps(where: layout.Layout, approval: contracts.Approval | None) -> list[str]:
    record = workspace.load_split_record(where)
    checked = record is not None and (record.plan_sha, record.dataset_sha) == (
        workspace.compute_plan_sha(where),
        workspace.compute_dataset_sha(where),
    )
    state = "未承認" if approval is None else "承認の後に変わった"
    if not checked:
        return [f"段階: 計画が{state}（検査の前）", f"次: {_build_command(where, 'check-plan')}"]
    return [
        f"段階: 計画が{state}（人が決める）",
        f"次: {where.display(where.plan_md_path)} を人に見せ、この計画で始めてよいかを AskUserQuestion で聞く",
        f"承認なら: {_build_command(where, 'approve')}",
    ]


def status(where: layout.Layout) -> str:
    if not where.plan_path.is_file():
        return "\n".join(
            ["段階: 計画が無い", "次: skill-tune の手順 A に従い、init で計画のひな形を作り、人と計画を決める"]
        )
    problems = workspace.list_dataset_problems(where)
    if problems:
        lines = [f"問題: {problem}" for problem in problems]
        return "\n".join(
            [
                "段階: 計画に問題がある",
                *lines,
                "次: skill-tune の手順 A に従って plan.json と cases.json を直し、status をやり直す",
            ]
        )
    model = workspace.load_plan(where)
    header = f"対象: {model.target.id}（{model.mode} モード、{model.target.skill_path}）"
    approval = workspace.load_approval(where)
    if not workspace.is_approved(where, approval):
        return "\n".join([header, *_build_plan_steps(where, approval)])
    approved = workspace.load_approved(where)
    decided = len(workspace.load_decisions(where))
    rounds = f"ラウンド: 決定済み {decided} / 上限 {model.budget.max_rounds}"
    return "\n".join([header, rounds, *_build_loop_steps(where, approved)])
