"""分析役へのプロンプトと、編集用の候補のバンドル（proposed）を用意し、分析役の提案を検査する。"""

from __future__ import annotations

from forge_kit import bundle, charter, contracts, fsops, prompts, render, views, workspace
from forge_kit.errors import InvalidFileError, StageError
from forge_kit.layout import Layout


def analyze(where: Layout, round_no: int) -> str:
    model, _sha = workspace.approved_charter(where)
    progress = workspace.progress(where, model)
    _require_next_round(model, progress, round_no)
    current = workspace.load_scores(where, progress.current_slot)
    if current.all_must_met:
        raise StageError(
            "今のスキルは must の指標を全部満たしています。改善のラウンドではなく、最後の評価へ進んでください"
        )
    name = model.target.skill_name
    proposed = where.proposed_dir(round_no)
    fsops.remove_tree(proposed)
    bundle.copy(where.claude_dir, proposed, name)
    plan = workspace.load_plan(where, progress.current_slot)
    fsops.write_text(where.visible_charter_path, views.render_charter(model, "approved", include_holdout=False))
    slot = progress.current_slot
    evidence = [
        f"{run.run_id}: 出力 `{where.out_dir(slot, run.run_id)}`、作業後のコピー `{where.copy_dir(slot, run.run_id)}`"
        for run in plan.runs
    ]
    values = {
        "skill_name": name,
        "charter_md": str(where.visible_charter_path),
        "scores_md": str(where.scores_md_path(slot)),
        "rules_md": str(where.bundle_rules_path),
        "evidence": render.bullets(evidence),
        "history": _history(where, progress),
        "bundle_dir": str(where.claude_dir),
        "proposed_dir": str(proposed),
        "proposal": str(where.proposal_path(round_no)),
        "causes": render.table(
            ["原因", "名前", "扱い"], [[key, label, action] for key, (label, action) in contracts.CAUSES.items()]
        ),
    }
    path = where.analyst_prompt_path(round_no)
    fsops.write_text(path, prompts.render("analyst", values))
    return "\n".join(
        [
            f"分析役を準備しました: {round_no} 回目",
            render.job(contracts.AGENTS["analyst"], f"round-{round_no}", str(path)),
        ]
    )


def _require_next_round(model: charter.Charter, progress: workspace.Progress, round_no: int) -> None:
    if not progress.baseline.scored:
        raise StageError("最初の評価（baseline）がまだ採点されていません")
    expected = progress.decided_rounds + 1
    if round_no != expected or len(progress.rounds) >= expected:
        raise StageError(
            f"今分析を始められるのは {expected} 回目ではありません。status で次にすることを確かめてください"
        )
    if progress.decided_rounds >= model.budget.max_rounds:
        raise StageError(f"改善のラウンドが上限（{model.budget.max_rounds}）に達しました。最後の評価へ進んでください")


def _history(where: Layout, progress: workspace.Progress) -> str:
    lines = []
    for item in progress.rounds:
        if item.decision is None:
            continue
        verdict = "採用" if item.decision.adopted else "不採用"
        lines.append(f"{item.round_no} 回目: 提案 `{where.proposal_md_path(item.round_no)}`、決定: {verdict}")
    return render.bullets(lines)


def propose(where: Layout, round_no: int) -> str:
    model, _sha = workspace.approved_charter(where)
    if not where.analyst_prompt_path(round_no).is_file():
        raise StageError(f"{round_no} 回目の分析役がまだ準備されていません。先に analyze を実行してください")
    proposal = workspace.load_proposal(where, model, round_no)
    name = model.target.skill_name
    proposed = where.proposed_dir(round_no)
    diff = bundle.diff(where.claude_dir, proposed, name) if bundle.has_bundle(proposed, name) else ""
    problems = _proposal_problems(where, model, proposal, round_no, diff)
    if problems:
        problems.append("分析役に、この問題を直すよう添えて、同じプロンプトでもう一度起動してください")
        raise InvalidFileError(str(where.proposal_path(round_no)), problems)
    fsops.write_text(where.proposal_md_path(round_no), render_proposal(round_no, proposal, diff))
    counts = f"変更 {len(proposal.changes)} 件、所見 {len(proposal.observations)} 件"
    return f"提案を確かめました: {counts}（{where.proposal_md_path(round_no)}）"


def _proposal_problems(
    where: Layout, model: charter.Charter, proposal: contracts.Proposal, round_no: int, diff: str
) -> list[str]:
    name = model.target.skill_name
    proposed = where.proposed_dir(round_no)
    if not bundle.has_bundle(proposed, name):
        return [f"{proposed} に {name} のバンドルがありません"]
    original = bundle.text_of(where.claude_dir, name)
    fresh = frozenset(f for f in charter.fragments(model, bundle.LEAK_MIN_CHARS) if f not in original)
    problems = bundle.check(proposed, name, fragments=fresh)
    if proposal.changes and not diff:
        problems.append("changes があるのに、候補のバンドルが今のバンドルと同じです")
    if not proposal.changes and diff:
        problems.append(
            "changes が無いのに、候補のバンドルが変わっています。変更を changes に書くか、写しを元に戻してください"
        )
    return problems


def render_proposal(round_no: int, proposal: contracts.Proposal, diff: str) -> str:
    change_rows = [
        [c.id, f"{c.cause} {contracts.CAUSES[c.cause][0]}", ", ".join(c.metrics), c.summary, ", ".join(c.evidence)]
        for c in proposal.changes
    ]
    observation_rows = [
        [f"{o.cause} {contracts.CAUSES[o.cause][0]}", o.summary, ", ".join(o.evidence)] for o in proposal.observations
    ]
    parts = [
        f"# {round_no} 回目の改善の提案",
        "",
        "## バンドルの変更",
        "",
        render.table(["id", "原因", "効かせたい指標", "内容", "根拠"], change_rows) if change_rows else "なし",
        "",
        "## バンドルでは直さない所見",
        "",
        render.table(["原因", "内容", "根拠"], observation_rows) if observation_rows else "なし",
        "",
        "## バンドルの差分",
        "",
        f"```diff\n{diff}```" if diff else "差分なし",
    ]
    return "\n".join(parts) + "\n"
