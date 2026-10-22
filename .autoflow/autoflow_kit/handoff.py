"""報告の段（handoff、commit）。H3 で人が読む報告書を書き、承認した tree のままならコミットする（GATE-05）。

報告書は、証拠（補助 CLI が実行した検査の出力）・レビューの結果・検査が見ていないこと・戻し方を並べる。
コミットは作業ブランチにだけ行い、リモートには送らない（OPS-05）。
"""

from __future__ import annotations

from collections.abc import Sequence

from autoflow_kit import changes, context, contracts, fsops, policy, proc, render, trail, views, workspace
from autoflow_kit.errors import StageError
from autoflow_kit.layout import Layout


def _evidence(ctx: context.Context) -> contracts.Evidence:
    """今の tree で通った、実装の後の証拠。"""
    passed = [
        event
        for event in ctx.events
        if event.kind == trail.VERIFIED and event.mode == trail.CHECK and event.passed and event.tree == ctx.tree
    ]
    if not passed:
        raise StageError("今の tree で通った証拠がありません。verify を実行する")
    return workspace.load_evidence(ctx.where, ctx.run_id, passed[-1].number)


def _overview(ctx: context.Context, plan: contracts.Plan, tier: str, rule: policy.RuleTier) -> list[str]:
    start = ctx.start
    return [
        f"# 報告書: {start.text}",
        "",
        f"- 依頼: {start.source} {start.ref or render.MISSING} {start.url or ''}".rstrip(),
        f"- 種類: `{plan.kind}`（{policy.kind_of(plan.kind).label}）",
        f"- ゴール: {plan.goal}",
        f"- 作業ブランチ: `{start.branch}`、tree `{ctx.tree[:12]}`",
        f"- リスクの段: `{tier}`（規則 `{rule.tier}` と判定役の大きい方）",
        "",
    ]


def _human_section(tier: str, rule: policy.RuleTier, judgment: contracts.RiskJudgment) -> list[str]:
    files = sorted({*rule.human_files, *judgment.attention_files})
    lines = ["## H3 で人がすること", "", policy.tier_of(tier).human, ""]
    if rule.human_files or judgment.human_required:
        lines += ["次のファイルは、差分を全部読む:", "", render.bullets([f"`{path}`" for path in files]), ""]
    lines += ["リスクの段を決めた理由:", "", render.bullets([*rule.reasons, *judgment.reasons]), ""]
    return lines


def _evidence_section(evidence: contracts.Evidence) -> list[str]:
    rows = [[item.id, f"`{item.run}`", render.number(item.exit_code), item.log] for item in evidence.results]
    return [
        "## 証拠（補助 CLI が実行した検査）",
        "",
        f"証拠 {evidence.seq}。tree `{evidence.tree[:12]}` で実行した。",
        "",
        render.table(["検査", "コマンド", "終了コード", "ログ"], rows),
        "",
    ]


def _criteria_section(plan: contracts.Plan) -> list[str]:
    how = {
        contracts.COMMAND: "証拠の検査",
        contracts.REVIEW: "レビュー（intent の観点）",
        contracts.HUMAN: "人が確かめる",
    }
    rows = [[item.id, item.text, how.get(item.check, item.check), item.run or render.MISSING] for item in plan.criteria]
    return ["## 受け入れ条件", "", render.table(["id", "条件", "確かめ方", "コマンド"], rows), ""]


def _unchecked_section(plan: contracts.Plan, results: Sequence[contracts.ReviewResult]) -> list[str]:
    """検査が見ていないこと。ここに書けないなら、人は短い承認ではなく本当のレビューをする。"""
    lines = [
        f"受け入れ条件 {item.id}（{item.check}）: {item.text}"
        for item in plan.criteria
        if item.check != contracts.COMMAND
    ]
    last = results[-1] if results else None
    if last is not None:
        lines += [f"残した Nit: {views.finding_line(item)}" for item in last.kept if item.tag == policy.NIT]
    lines += [
        f"既存の問題（この変更が持ち込んだものではない）: {views.finding_line(item)}"
        for result in results
        for item in result.kept
        if item.tag == policy.PRE_EXISTING
    ]
    lines += [f"依頼から決まらなかった値: {item.question} → 既定 {item.default}" for item in plan.open_questions]
    return ["## 検査が見ていないこと", "", render.bullets(lines), ""]


def _review_section(ctx: context.Context, results: Sequence[contracts.ReviewResult]) -> list[str]:
    rows = [
        [
            render.number(result.round_no),
            result.depth,
            *(render.number(sum(1 for item in result.kept if item.tag == tag)) for tag in policy.REVIEW.tags),
            render.number(len(result.dropped)),
        ]
        for result in results
    ]
    declined = [
        f"{resolution.finding_id}: {resolution.reason}"
        for attempt in range(1, trail.count(ctx.events, trail.BUILT) + 1)
        for resolution in workspace.load_report(ctx.where, ctx.run_id, attempt).resolutions
        if resolution.status == contracts.DECLINED
    ]
    headers = ["ラウンド", "深さ", *(views.TAG_LABELS[tag] for tag in policy.REVIEW.tags), "票で落ちた候補"]
    return ["## レビュー", "", render.table(headers, rows), "", "退けた指摘と理由:", "", render.bullets(declined), ""]


def _build_section(ctx: context.Context) -> list[str]:
    lines = ["## 実装役の報告", ""]
    for attempt in range(1, trail.count(ctx.events, trail.BUILT) + 1):
        report = workspace.load_report(ctx.where, ctx.run_id, attempt)
        lines += [f"### 実装 {attempt}: {report.summary}", "", report.explanation, ""]
    return lines


def _decision_section(events: Sequence[trail.Event]) -> list[str]:
    rows = [
        [event.gate, event.choice, event.answer, event.who or render.MISSING, event.at]
        for event in events
        if event.kind == trail.DECIDED
    ]
    return ["## 人の決定の記録", "", render.table(["関所", "選択", "回答の原文", "答えた人", "時刻"], rows), ""]


def _files_section(found: Sequence[changes.Stat]) -> list[str]:
    rows = [[f"`{stat.path}`", render.number(stat.added), render.number(stat.deleted)] for stat in found]
    return ["## 変えたファイル", "", render.table(["ファイル", "足した行", "消した行"], rows), ""]


def _message(plan: contracts.Plan, trailers: Sequence[str]) -> str:
    return plan.commit_subject + ("\n\n" + "\n".join(trailers) if trailers else "") + "\n"


def handoff(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.HANDOFF)
    number = ctx.next.number
    plan = workspace.load_plan(where, run_id, trail.count(ctx.events, trail.PLANNED))
    found = changes.stats(where.root, ctx.start.tree, ctx.tree)
    rule = policy.tier_of_changes(tuple(stat.path for stat in found), changes.line_count(found), ctx.profile)
    risk = trail.last(ctx.events, trail.RISKED)
    if risk is None:
        raise StageError("リスクの段がまだ決まっていません。status で次を確かめる")
    judgment = workspace.load_judgment(where, run_id, risk.number)
    tier = policy.merge_tier(rule.tier, risk.tier)
    results = [workspace.load_result(where, run_id, n) for n in range(1, trail.count(ctx.events, trail.REVIEWED) + 1)]
    message = _message(plan, ctx.profile.commit.trailers)
    parts = [
        *_overview(ctx, plan, tier, rule),
        *_human_section(tier, rule, judgment),
        *_evidence_section(_evidence(ctx)),
        *_criteria_section(plan),
        *_unchecked_section(plan, results),
        *_review_section(ctx, results),
        *_build_section(ctx),
        *_decision_section(ctx.events),
        *_files_section(found),
        "## 戻し方",
        "",
        plan.revert,
        "",
        "## コミットの案",
        "",
        f"承認すると、作業ブランチ `{ctx.start.branch}` に次の文でコミットする。リモートには送らない。",
        "",
        render.fence(message),
        "",
    ]
    path = where.handoff_path(run_id, number)
    fsops.write_text(path, "\n".join(parts))
    fsops.append_line(where.trail_path(run_id), trail.encode(trail.handed_off(number, tier, message, ctx.tree, now)))
    return f"書いた: {where.relative(path)}（リスクの段: {tier}）"


def commit(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.COMMIT)
    report = trail.last(ctx.events, trail.HANDED_OFF)
    if report is None:
        raise StageError("報告書がありません。status で次を確かめる")
    sha = proc.git_commit(where.root, report.text)
    fsops.append_line(where.trail_path(run_id), trail.encode(trail.committed(sha, ctx.tree, now)))
    return f"コミットした: {sha[:12]}（ブランチ {ctx.start.branch}）。リモートには送っていない"
