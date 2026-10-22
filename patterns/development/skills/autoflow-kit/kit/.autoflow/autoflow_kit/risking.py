"""リスクの段（risk-new、risk-check）。差分から規則で段を決め、リスク判定役の判定とは大きい方を採る（GATE-06）。"""

from __future__ import annotations

from autoflow_kit import changes, context, fsops, policy, prompts, render, trail, views, workspace
from autoflow_kit.layout import Layout


def _rule_tier(ctx: context.Context) -> policy.RuleTier:
    """作業の前の tree から今の tree までの差分だけで決めた段。"""
    found = changes.stats(ctx.where.root, ctx.start.tree, ctx.tree)
    return policy.tier_of_changes(tuple(stat.path for stat in found), changes.line_count(found), ctx.profile)


def risk_new(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.RISK)
    number = ctx.next.number
    rule = _rule_tier(ctx)
    diff_path = where.risk_diff_path(run_id, number)
    fsops.write_text(diff_path, changes.diff_text(where.root, ctx.start.tree, ctx.tree))
    values = {
        "plan_md_path": where.relative(where.plan_md_path(run_id, trail.count(ctx.events, trail.PLANNED))),
        "diff_path": where.relative(diff_path),
        "rule_tier": rule.tier,
        "rule_reasons": render.bullets(rule.reasons),
        "tiers": views.render_tiers(),
        "output_path": where.relative(where.judgment_path(run_id, number)),
    }
    path = where.risk_prompt_path(run_id, number)
    fsops.write_text(path, prompts.fill("risk", values))
    event = trail.prompted(trail.RISK_ROLE, number, "", ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    return f"書いた: {where.relative(path)}（規則の段: {rule.tier}）"


def risk_check(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.RISK)
    context.require_prompted(ctx, trail.RISK_ROLE, "risk-new")
    context.require_same_tree(ctx.next.prompted_tree, ctx.tree)
    number = ctx.next.number
    judgment = workspace.load_judgment(where, run_id, number)
    rule = _rule_tier(ctx)
    tier = policy.merge_tier(rule.tier, judgment.tier)
    human_required = bool(rule.human_files) or judgment.human_required
    event = trail.risked(number, tier, human_required, (*rule.reasons, *judgment.reasons), ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    return "\n".join(
        [
            f"リスクの段: {tier}（規則 {rule.tier}、判定役 {judgment.tier}）",
            f"人が差分を読む必要: {'あり' if human_required else 'なし'}",
            render.bullets(event.reasons),
        ]
    )
