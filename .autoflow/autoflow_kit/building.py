"""実装の段（build-new、build-check）。実装役のプロンプトを書き、報告を検証して、必要なら H2 を起こす。"""

from __future__ import annotations

from collections.abc import Sequence

from autoflow_kit import (
    changes,
    context,
    contracts,
    escalation,
    fsops,
    policy,
    prompts,
    render,
    trail,
    views,
    workspace,
)
from autoflow_kit.errors import InvalidFileError
from autoflow_kit.layout import Layout

ANSWERED_TAGS = (policy.IMPORTANT, policy.NIT)


def _pending_findings(where: Layout, run_id: str, events: Sequence[trail.Event]) -> tuple[contracts.Kept, ...]:
    """最後の実装の後のレビューに Important が残っていれば、回答が要る指摘（Important と Nit）。"""
    review = trail.last(trail.since_last_build(events), trail.REVIEWED)
    if review is None or review.important == 0:
        return ()
    result = workspace.load_result(where, run_id, review.number)
    return tuple(item for item in result.kept if item.tag in ANSWERED_TAGS)


def _failures(where: Layout, run_id: str, events: Sequence[trail.Event]) -> list[str]:
    """最後の実装の後の検査が期待どおりでなかったときの、検査ごとの1行。"""
    check = trail.last(trail.since_last_build(events), trail.VERIFIED)
    if check is None or check.passed:
        return []
    evidence = workspace.load_evidence(where, run_id, check.number)
    expect_failure = evidence.mode == trail.REPRO
    return [
        f"{item.id}: 終了コード {item.exit_code} — `{item.run}` — ログ {item.log}"
        for item in evidence.results
        if (item.exit_code != 0) != expect_failure
    ]


def _answer(events: Sequence[trail.Event], reason: str) -> str:
    decision = trail.last(events, trail.DECIDED)
    return decision.answer if reason == trail.HUMAN and decision is not None else render.MISSING


def build_new(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.BUILD)
    attempt, reason = ctx.next.number, ctx.next.reason
    plan_no = trail.count(ctx.events, trail.PLANNED)
    values = {
        "task_path": where.relative(where.task_path(run_id)),
        "plan_md_path": where.relative(where.plan_md_path(run_id, plan_no)),
        "reason": reason,
        "tests": render.bullets([f"`{pattern}`" for pattern in ctx.profile.paths.tests]),
        "failures": render.bullets(_failures(where, run_id, ctx.events)),
        "findings": render.bullets([views.finding_line(item) for item in _pending_findings(where, run_id, ctx.events)]),
        "answer": _answer(ctx.events, reason),
        "report_path": where.relative(where.report_path(run_id, attempt)),
    }
    path = where.build_prompt_path(run_id, attempt)
    fsops.write_text(path, prompts.fill("builder", values))
    event = trail.prompted(trail.BUILDER, attempt, reason, ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    return f"書いた: {where.relative(path)}（理由: {reason}）"


def _check_report(ctx: context.Context, report: contracts.BuildReport) -> list[str]:
    problems = []
    required = {item.id for item in _pending_findings(ctx.where, ctx.run_id, ctx.events)}
    answered = {resolution.finding_id for resolution in report.resolutions}
    problems += [f"指摘 {finding_id} への回答が resolutions にありません" for finding_id in sorted(required - answered)]
    problems += [
        f"resolutions の {finding_id} は、回答の要る指摘ではありません" for finding_id in sorted(answered - required)
    ]
    if ctx.next.reason == trail.REPRO:
        touched = changes.changed_files(ctx.where.root, ctx.next.prompted_tree, ctx.tree)
        outside = [path for path in touched if not policy.has_match(path, ctx.profile.paths.tests)]
        if outside:
            problems.append(f"再現のテストの段で変えてよいのは paths.tests のパスだけです: {', '.join(outside)}")
    return problems


def build_check(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.BUILD)
    context.require_prompted(ctx, trail.BUILDER, "build-new")
    attempt = ctx.next.number
    report = workspace.load_report(where, run_id, attempt)
    problems = _check_report(ctx, report)
    if problems:
        raise InvalidFileError(where.relative(where.report_path(run_id, attempt)), problems)
    event = trail.built(attempt, ctx.next.reason, report.blockers, ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    stuck = escalation.record(where, run_id, (*ctx.events, event), ctx.profile.limits, now)
    lines = [f"実装 {attempt}: {report.summary}"]
    lines += [f"WARN 実装役が止まった理由: {blocker}" for blocker in report.blockers]
    lines += [f"H2 に当たった条件: {policy.rule_text(rule)}" for rule in stuck]
    return "\n".join(lines)
