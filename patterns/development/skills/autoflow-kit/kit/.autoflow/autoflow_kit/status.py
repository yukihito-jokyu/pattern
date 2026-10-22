"""状態の段（status）。実行の記録から今の段を求め、次に実行するコマンド、起動するサブエージェント、人に聞くことを示す。

スキルは、この出力の行を書き出しで読み分けて動く（OPS-01）。
"""

from __future__ import annotations

from autoflow_kit import context, contracts, policy, render, trail, workspace
from autoflow_kit.layout import CLI, Layout

# status の行の書き出し。スキルはこの書き出しで行を読み分けるので、新しい種類を足さない（OPS-01）
LINE_KINDS = ("対象:", "段階:", "次:", "job ", "その後:", "人:", "選択:", "終了:", "WARN ")
LAUNCH = "次: 下の job をすべて Agent ツールで1つのメッセージにまとめて起動し、全員の完了を待つ"
STEP_LABELS = {
    trail.VERIFY: "検証",
    trail.PLAN: "計画",
    trail.DECIDE: "人の関所",
    trail.BUILD: "実装",
    trail.RISK: "リスクの判定",
    trail.REVIEW: "レビュー",
    trail.HANDOFF: "報告書",
    trail.COMMIT: "コミット",
    trail.DONE: "完了",
    trail.STOPPED: "停止",
}


def _command(name: str, run_id: str, extra: str = "") -> str:
    return f"{CLI} {name} --run {run_id}{extra}"


def _job(role: str, label: str, prompt: str) -> str:
    return render.job(contracts.AGENTS[role], label, prompt)


def _single_agent(ctx: context.Context, role: str, names: tuple[str, str], prompt: str) -> list[str]:
    """計画・実装・リスクの判定のように、1人の役を起動する段。names は (書く段, 確かめる段)。"""
    write, check = names
    if ctx.next.prompted != role:
        return [f"次: {_command(write, ctx.run_id)}"]
    label = f"{role}-{ctx.next.number}"
    return [LAUNCH, _job(role, label, prompt), f"その後: {_command(check, ctx.run_id)}"]


def _review_steps(ctx: context.Context) -> list[str]:
    where, run_id, round_no = ctx.where, ctx.run_id, ctx.next.number
    risk = trail.last(ctx.events, trail.RISKED)
    depth = policy.depth_of(risk.tier if risk is not None else policy.HIGH)
    if ctx.next.prompted == trail.FINDER:
        jobs = [
            _job(trail.FINDER, f"{lens}-r{round_no}", where.relative(where.finder_prompt_path(run_id, round_no, lens)))
            for lens in depth.lenses
        ]
        return [LAUNCH, *jobs, f"その後: {_command('review-collect', run_id)}"]
    if ctx.next.prompted == trail.VERIFIER:
        if not workspace.load_candidates(where, run_id, round_no):
            return [f"次: {_command('review-tally', run_id)}"]
        jobs = [
            _job(
                trail.VERIFIER,
                f"verifier-{voter}-r{round_no}",
                where.relative(where.verifier_prompt_path(run_id, round_no, voter)),
            )
            for voter in range(1, depth.verifiers + 1)
        ]
        return [LAUNCH, *jobs, f"その後: {_command('review-tally', run_id)}"]
    return [f"次: {_command('review-new', run_id)}"]


def _gate_steps(ctx: context.Context) -> list[str]:
    where, run_id, number = ctx.where, ctx.run_id, ctx.next.number
    gate = policy.gate_of(ctx.next.gate)
    shown = {
        policy.H1: where.plan_md_path(run_id, number),
        policy.H2: where.gate_path(run_id, policy.H2, number),
        policy.H3: where.handoff_path(run_id, number),
    }[gate.id]
    lines = [f"人: {where.relative(shown)} を人に見せ、{gate.id} {gate.label} の選択と回答を AskUserQuestion で聞く"]
    lines += [
        f"選択: {option.name}（{option.label}）→ "
        + _command("decide", run_id, f" --gate {gate.id} --choice {option.name} --answer '<人の回答の原文>'")
        for option in gate.options
    ]
    return lines


def _end(ctx: context.Context) -> list[str]:
    if ctx.next.step == trail.DONE:
        done = trail.last(ctx.events, trail.COMMITTED)
        commit = done.commit[:12] if done is not None else ""
        return [f"終了: 作業ブランチ {ctx.start.branch} にコミットした（{commit}）。リモートには送っていない"]
    return [f"終了: 止めた（{ctx.next.why}）。作業ブランチ {ctx.start.branch} と変更は残っている"]


def _steps(ctx: context.Context) -> list[str]:
    where, run_id, number, step = ctx.where, ctx.run_id, ctx.next.number, ctx.next.step
    agents = {
        trail.PLAN: (trail.PLANNER, ("plan-new", "plan-check"), where.plan_prompt_path),
        trail.BUILD: (trail.BUILDER, ("build-new", "build-check"), where.build_prompt_path),
        trail.RISK: (trail.RISK_ROLE, ("risk-new", "risk-check"), where.risk_prompt_path),
    }
    if step in agents:
        role, names, prompt_path = agents[step]
        return _single_agent(ctx, role, names, where.relative(prompt_path(run_id, number)))
    if step == trail.REVIEW:
        return _review_steps(ctx)
    if step == trail.DECIDE:
        return _gate_steps(ctx)
    if step in (trail.DONE, trail.STOPPED):
        return _end(ctx)
    return [f"次: {_command(step, run_id)}"]


def status(where: Layout, run_id: str) -> str:
    """run_id が空なら、最後に始めた実行を見る。"""
    ctx = context.peek(where, run_id or workspace.latest_run(where))
    lines = [
        f"対象: {ctx.run_id}（{ctx.start.text}）ブランチ {ctx.start.branch}",
        f"段階: {STEP_LABELS[ctx.next.step]}（{ctx.next.why}）",
        *_steps(ctx),
    ]
    return "\n".join(lines)
