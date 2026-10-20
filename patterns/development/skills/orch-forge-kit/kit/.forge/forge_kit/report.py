"""全体の報告（指標の推移、ラウンドごとの判断、最後の評価、実行の条件、人に判断してほしいこと）を書く。"""

from __future__ import annotations

from forge_kit import charter, contracts, fsops, render, workspace
from forge_kit.errors import StageError
from forge_kit.layout import Layout


def report(where: Layout) -> str:
    model, _sha = workspace.approved_charter(where)
    progress = workspace.progress(where, model)
    if not progress.final.scored:
        raise StageError("最後の評価がまだ採点されていません。status で次にすることを確かめてください")
    final = workspace.load_scores(where, progress.final.slot)
    columns = [("最初", workspace.load_scores(where, progress.baseline.slot))]
    for item in progress.rounds:
        if item.candidate.scored:
            columns.append((f"{item.round_no} 回目の候補", workspace.load_scores(where, item.candidate.slot)))
    columns.append(("最後", final))
    fsops.write_text(where.report_path, render_report(where, model, progress, columns, final))
    return f"報告を書きました: {where.report_path}"


def _trend(model: charter.Charter, columns: list[tuple[str, contracts.Scores]], final: contracts.Scores) -> str:
    holdout = {score.id: score.value for score in final.holdout_metrics}
    rows = []
    for choice in model.metrics:
        values = [{s.id: s.value for s in scores.metrics}.get(choice.id) for _label, scores in columns]
        rows.append([choice.id, choice.priority, render.number(choice.threshold), *map(render.number, values)])
        rows[-1].append(render.number(holdout.get(choice.id)) if final.holdout_metrics else render.MISSING)
    headers = ["id", "優先度", "閾値", *[label for label, _scores in columns], "ホールドアウト"]
    return render.table(headers, rows)


def _rounds(where: Layout, model: charter.Charter, progress: workspace.Progress) -> str:
    rows = []
    for item in progress.rounds:
        proposal = workspace.load_proposal(where, model, item.round_no) if item.checked else None
        changes = ", ".join(f"{c.id}（{c.cause}）{c.summary}" for c in proposal.changes) if proposal else render.MISSING
        recommendation = render.MISSING
        if item.compared:
            comparison = workspace.load_comparison(where, item.round_no)
            recommendation = "採用" if comparison.recommendation == "adopt" else "不採用"
        decision = render.MISSING if item.decision is None else ("採用" if item.decision.adopted else "不採用")
        rows.append([str(item.round_no), changes, recommendation, decision])
    return render.table(["回", "バンドルの変更", "推奨", "人の決定"], rows) if rows else "改善のラウンドは行っていない"


def _observations(
    where: Layout, model: charter.Charter, progress: workspace.Progress
) -> list[tuple[int, contracts.Observation]]:
    found = []
    for item in progress.rounds:
        if item.checked:
            found += [
                (item.round_no, note) for note in workspace.load_proposal(where, model, item.round_no).observations
            ]
    return found


def _asks(
    final: contracts.Scores, observations: list[tuple[int, contracts.Observation]], *, adopted: bool
) -> list[str]:
    asks = [
        f"must の {s.id}（{s.name}）が閾値に届いていない: {render.number(s.value)}"
        for s in final.metrics
        if s.priority == "must" and not s.met
    ]
    visible = {s.id: s.met for s in final.metrics}
    for score in final.holdout_metrics:
        if visible.get(score.id) and not score.met and score.value is not None:
            # 採った変更が無ければ、スキルは課題に合わせて直されていないので、過剰適合ではない
            cause = (
                "課題への過剰適合の疑いがある"
                if adopted
                else "採った変更は無いので、課題の違いか実行の揺れと考えられる"
            )
            asks.append(f"{score.id} は評価に使った課題では達成、ホールドアウトでは未達。{cause}")
    if any(note.cause == "S6" for _round_no, note in observations):
        asks.append("評価の側の問題（S6）の所見がある。/forge-goals で charter を見直すか判断してほしい")
    return asks


def _conditions(model: charter.Charter) -> str:
    executor = model.executor
    return render.bullets(
        [
            f"モデル: {executor.model or 'Claude Code の既定'}",
            f"確認なしで許したツール: {', '.join(executor.allowed_tools) or 'なし'}",
            f"1回の実行の上限: {render.usd(executor.max_budget_usd)}、{executor.timeout_sec} 秒",
            "費用は Claude Code の推定の値である。ユーザー単位の設定とスキルも実行役に読み込まれた",
        ]
    )


def render_report(
    where: Layout,
    model: charter.Charter,
    progress: workspace.Progress,
    columns: list[tuple[str, contracts.Scores]],
    final: contracts.Scores,
) -> str:
    observations = _observations(where, model, progress)
    adopted = any(item.decision is not None and item.decision.adopted for item in progress.rounds)
    goals = render.table(["id", "ゴール", "指標"], [[g.id, g.statement, ", ".join(g.metrics)] for g in model.goals])
    parts = [
        f"# {model.target.id} の報告",
        "",
        "## 1. 目的とゴール",
        "",
        f"対象は `{model.target.skill_name}`。charter の全文は `{where.charter_md_path}` にある。",
        "",
        model.purpose,
        "",
        goals,
        "",
        "## 2. 指標の推移",
        "",
        _trend(model, columns, final),
        "",
        "## 3. ラウンドごとの変更と判断",
        "",
        _rounds(where, model, progress),
        "",
        "## 4. バンドルでは直さなかった所見",
        "",
        render.bullets(
            [f"{number} 回目 {n.cause} {contracts.CAUSES[n.cause][0]}: {n.summary}" for number, n in observations]
        ),
        "",
        "## 5. 実行の条件",
        "",
        _conditions(model),
        "",
        "## 6. 人に判断してほしいこと",
        "",
        render.bullets(_asks(final, observations, adopted=adopted)),
    ]
    return "\n".join(parts) + "\n"
