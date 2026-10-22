"""レビューの段（review-new、review-collect、review-tally）。

観点ごとの探索役を並列に起動し、重複と既出をまとめ、検証役の票で閾値以上の指摘だけを残す。
2ラウンド目からは、前のラウンドの tree からの差分だけを見せる。
"""

from __future__ import annotations

from collections import Counter

from autoflow_kit import (
    changes,
    context,
    contracts,
    escalation,
    fsops,
    policy,
    prompts,
    render,
    shape,
    trail,
    views,
    workspace,
)
from autoflow_kit.layout import Layout


def _depth(ctx: context.Context) -> policy.Depth:
    risk = trail.last(ctx.events, trail.RISKED)
    return policy.depth_of(risk.tier if risk is not None else policy.HIGH)


def _base(ctx: context.Context, round_no: int) -> str:
    """差分の起点。最初のラウンドは作業の前の tree、diff_only_from_round からは前のラウンドの tree。"""
    previous = trail.last(ctx.events, trail.REVIEWED)
    if previous is None or round_no < policy.REVIEW.diff_only_from_round:
        return ctx.start.tree
    return previous.tree


def _answers(ctx: context.Context) -> dict[str, contracts.Resolution]:
    found = {}
    for attempt in range(1, trail.count(ctx.events, trail.BUILT) + 1):
        for resolution in workspace.load_report(ctx.where, ctx.run_id, attempt).resolutions:
            found[resolution.finding_id] = resolution
    return found


def _prior(ctx: context.Context, round_no: int) -> list[tuple[contracts.Kept, contracts.Resolution | None]]:
    answers = _answers(ctx)
    return [
        (item, answers.get(item.id))
        for number in range(1, round_no)
        for item in workspace.load_result(ctx.where, ctx.run_id, number).kept
    ]


def _prior_findings_line(item: contracts.Kept, answer: contracts.Resolution | None) -> str:
    status = f"{answer.status}（{answer.reason or render.MISSING}）" if answer is not None else render.MISSING
    return f"{views.finding_line(item)} — 回答: {status}"


def review_new(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.REVIEW)
    round_no, depth = ctx.next.number, _depth(ctx)
    diff_path = where.review_diff_path(run_id, round_no)
    fsops.write_text(diff_path, changes.diff_text(where.root, _base(ctx, round_no), ctx.tree))
    shared = {
        "plan_md_path": where.relative(where.plan_md_path(run_id, trail.count(ctx.events, trail.PLANNED))),
        "guide_path": where.relative(where.guide_path(run_id)),
        "diff_path": where.relative(diff_path),
        "round_no": str(round_no),
        "prior_findings": render.bullets(
            [_prior_findings_line(item, answer) for item, answer in _prior(ctx, round_no)]
        ),
        "skip": render.bullets([f"`{pattern}`" for pattern in ctx.profile.review.skip]),
    }
    written = []
    for lens in depth.lenses:
        values = {**shared, "lens": lens, "output_path": where.relative(where.findings_path(run_id, round_no, lens))}
        path = where.finder_prompt_path(run_id, round_no, lens)
        fsops.write_text(path, prompts.fill("finder", values))
        written.append(where.relative(path))
    event = trail.prompted(trail.FINDER, round_no, "", ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    return "\n".join([f"レビュー ラウンド {round_no}（深さ {depth.name}）。書いた:", render.bullets(written)])


def _candidates(ctx: context.Context, round_no: int, depth: policy.Depth) -> tuple[contracts.Candidate, ...]:
    """探索役の指摘から、指摘しないパスと、退けた既出の指摘を除き、同じ場所の指摘を1つにまとめる。"""
    declined = {
        (item.finding.file, item.finding.title)
        for item, answer in _prior(ctx, round_no)
        if answer is not None and answer.status == contracts.DECLINED
    }
    merged: dict[tuple[str, int], tuple[contracts.Finding, list[str]]] = {}
    for lens in depth.lenses:
        for finding in workspace.load_findings(ctx.where, ctx.run_id, round_no, lens):
            if policy.has_match(finding.file, ctx.profile.review.skip) or (finding.file, finding.title) in declined:
                continue
            key = (finding.file, finding.line)
            if key in merged:
                merged[key][1].append(lens)
            else:
                merged[key] = (finding, [lens])
    return tuple(
        contracts.Candidate(f"R{round_no}-{index}", tuple(lenses), finding)
        for index, (finding, lenses) in enumerate(merged.values(), 1)
    )


def review_collect(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.REVIEW)
    context.require_prompted(ctx, trail.FINDER, "review-new")
    context.require_same_tree(ctx.next.prompted_tree, ctx.tree)
    round_no, depth = ctx.next.number, _depth(ctx)
    candidates = _candidates(ctx, round_no, depth)
    candidates_path = where.candidates_path(run_id, round_no)
    fsops.write_json(candidates_path, {"candidates": [shape.to_data(item) for item in candidates]})
    written = []
    for voter in range(1, depth.verifiers + 1) if candidates else ():
        values = {
            "plan_md_path": where.relative(where.plan_md_path(run_id, trail.count(ctx.events, trail.PLANNED))),
            "guide_path": where.relative(where.guide_path(run_id)),
            "diff_path": where.relative(where.review_diff_path(run_id, round_no)),
            "candidates_path": where.relative(candidates_path),
            "output_path": where.relative(where.votes_path(run_id, round_no, voter)),
        }
        path = where.verifier_prompt_path(run_id, round_no, voter)
        fsops.write_text(path, prompts.fill("verifier", values))
        written.append(where.relative(path))
    event = trail.prompted(trail.VERIFIER, round_no, "", ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    return "\n".join([f"候補: {len(candidates)} 件。書いた:", render.bullets(written)])


def _tag(votes: list[contracts.Vote]) -> str:
    """本物と投票した票の多数の重大度。同じ数なら重い方（REVIEW.tags の前の方）にする。"""
    counted = Counter(vote.tag for vote in votes)
    return max(policy.REVIEW.tags, key=lambda tag: (counted[tag], -policy.REVIEW.tags.index(tag)))


def _tally(ctx: context.Context, round_no: int, depth: policy.Depth) -> contracts.ReviewResult:
    candidates = workspace.load_candidates(ctx.where, ctx.run_id, round_no)
    ids = [candidate.id for candidate in candidates]
    ballots = [
        workspace.load_votes(ctx.where, ctx.run_id, round_no, voter, ids)
        for voter in (range(1, depth.verifiers + 1) if candidates else ())
    ]
    kept, dropped = [], []
    for candidate in candidates:
        votes = [vote for ballot in ballots for vote in ballot if vote.id == candidate.id]
        real = [vote for vote in votes if vote.verdict == contracts.REAL]
        if len(real) >= depth.threshold:
            kept.append(
                contracts.Kept(candidate.id, _tag(real), len(real), len(votes), candidate.lenses, candidate.finding)
            )
        else:
            dropped.append(candidate.id)
    return contracts.ReviewResult(round_no, ctx.tree, _base(ctx, round_no), depth.name, tuple(kept), tuple(dropped))


def review_tally(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.REVIEW)
    context.require_prompted(ctx, trail.VERIFIER, "review-collect")
    context.require_same_tree(ctx.next.prompted_tree, ctx.tree)
    round_no = ctx.next.number
    result = _tally(ctx, round_no, _depth(ctx))
    fsops.write_json(where.result_path(run_id, round_no), shape.to_data(result))
    fsops.write_text(where.result_md_path(run_id, round_no), views.render_review(result))
    counts = tuple(
        sum(1 for item in result.kept if item.tag == tag) for tag in (policy.IMPORTANT, policy.NIT, policy.PRE_EXISTING)
    )
    event = trail.reviewed(round_no, (counts[0], counts[1], counts[2]), ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    stuck = escalation.record(where, run_id, (*ctx.events, event), ctx.profile.limits, now) if counts[0] else ()
    lines = [
        f"レビュー ラウンド {round_no}: Important {counts[0]}、Nit {counts[1]}、Pre-existing {counts[2]}",
        f"書いた: {where.relative(where.result_md_path(run_id, round_no))}",
    ]
    lines += [f"H2 に当たった条件: {policy.rule_text(rule)}" for rule in stuck]
    return "\n".join(lines)
