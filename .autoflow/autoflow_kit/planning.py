"""計画の段（plan-new、plan-check）。計画役のプロンプトを書き、計画を検証して手順を組み、H1 の要否を決める。"""

from __future__ import annotations

from autoflow_kit import context, fsops, policy, prompts, render, shape, trail, views, workspace
from autoflow_kit.layout import Layout


def plan_new(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.PLAN)
    number = ctx.next.number
    replans = [event.answer for event in ctx.events if event.kind == trail.DECIDED and event.choice == policy.REPLAN]
    values = {
        "task_path": where.relative(where.task_path(run_id)),
        "guide_path": where.relative(where.guide_path(run_id)),
        "kinds": views.render_kinds(),
        "feedback": render.bullets(replans),
        "output_path": where.relative(where.plan_path(run_id, number)),
        "ref": ctx.start.ref or render.MISSING,
    }
    path = where.plan_prompt_path(run_id, number)
    fsops.write_text(path, prompts.fill("planner", values))
    fsops.append_line(where.trail_path(run_id), trail.encode(trail.prompted(trail.PLANNER, number, "", ctx.tree, now)))
    return f"書いた: {where.relative(path)}"


def plan_check(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.PLAN)
    context.require_prompted(ctx, trail.PLANNER, "plan-new")
    context.require_same_tree(ctx.next.prompted_tree, ctx.tree)
    number = ctx.next.number
    plan = workspace.load_plan(where, run_id, number)
    flow = policy.compose(plan, ctx.profile)
    fsops.write_json(where.flow_path(run_id, number), shape.to_data(flow))
    fsops.write_text(where.plan_md_path(run_id, number), views.render_plan(plan, flow))
    fsops.append_line(where.trail_path(run_id), trail.encode(trail.planned(number, flow, ctx.tree, now)))
    lines = [f"書いた: {where.relative(where.plan_md_path(run_id, number))}", "手順:", render.bullets(flow.steps)]
    if flow.h1_reasons:
        lines += ["H1 に当たった条件:", render.bullets([policy.rule_text(rule) for rule in flow.h1_reasons])]
    return "\n".join(lines)
