"""今のバンドルと候補（提案を入れたバンドル）の採点を比べ、採用するかの推奨を決める。決めるのは人である。"""

from __future__ import annotations

from collections.abc import Sequence

from forge_kit import contracts, fsops, metrics, render, workspace
from forge_kit.errors import StageError
from forge_kit.layout import Layout

NAMES = {"adopt": "採用", "reject": "不採用"}
CHANGE_NAMES = {"better": "改善", "worse": "悪化", "same": "同じ", "unknown": "比べられない"}


def compare_rows(baseline: contracts.Scores, candidate: contracts.Scores) -> tuple[contracts.CompareRow, ...]:
    before = {score.id: score.value for score in baseline.metrics}
    return tuple(
        contracts.CompareRow(
            id=score.id,
            name=score.name,
            priority=score.priority,
            direction=score.direction,
            threshold=score.threshold,
            baseline=before.get(score.id),
            candidate=score.value,
            change=metrics.change_of(before.get(score.id), score.value, score.direction),
            candidate_met=score.met,
        )
        for score in candidate.metrics
    )


def recommend(rows: Sequence[contracts.CompareRow]) -> tuple[str, tuple[str, ...]]:
    """推奨の決定表: must の悪化があれば不採用、無くてどれかが改善すれば採用、どれも変わらなければ不採用。"""
    worse = [row for row in rows if row.priority == "must" and row.change == "worse"]
    better = [row for row in rows if row.change == "better"]
    unmet = [f"{row.id} は閾値に未達（{render.number(row.candidate)}）" for row in rows if not row.candidate_met]
    if worse:
        return "reject", tuple(f"must の {r.id} が悪化（{_pair(r)}）" for r in worse)
    if better:
        return "adopt", tuple(f"{r.id} が改善（{_pair(r)}）" for r in better) + tuple(unmet)
    return "reject", ("どの指標も変わらなかった", *unmet)


def _pair(row: contracts.CompareRow) -> str:
    return f"{render.number(row.baseline)} → {render.number(row.candidate)}"


def compare(where: Layout, round_no: int) -> str:
    model, _sha = workspace.approved_charter(where)
    progress = workspace.progress(where, model)
    current = next((item for item in progress.rounds if item.round_no == round_no), None)
    if current is None or current.decision is not None or not current.candidate.scored:
        raise StageError(f"{round_no} 回目は比べられる段階ではありません。status で次にすることを確かめてください")
    baseline = workspace.load_scores(where, progress.current_slot)
    candidate = workspace.load_scores(where, current.candidate.slot)
    rows = compare_rows(baseline, candidate)
    recommendation, reasons = recommend(rows)
    comparison = contracts.Comparison(round_no, baseline.slot, candidate.slot, rows, recommendation, reasons)
    fsops.write_json(where.compare_path(round_no), contracts.to_data(comparison))
    fsops.write_text(
        where.compare_md_path(round_no), render_comparison(comparison, str(where.proposal_md_path(round_no)))
    )
    return "\n".join([f"比べました: {round_no} 回目（推奨: {NAMES[recommendation]}）", table(rows)])


def table(rows: Sequence[contracts.CompareRow]) -> str:
    return render.table(
        ["id", "名前", "優先度", "今", "候補", "変化", "閾値", "候補の判定"],
        [
            [
                r.id,
                r.name,
                r.priority,
                render.number(r.baseline),
                render.number(r.candidate),
                CHANGE_NAMES[r.change],
                render.number(r.threshold),
                render.mark(r.candidate_met),
            ]
            for r in rows
        ],
    )


def render_comparison(comparison: contracts.Comparison, proposal_md: str) -> str:
    parts = [
        f"# {comparison.round_no} 回目の比較",
        "",
        f"- 今のバンドルの採点: {comparison.baseline_slot}",
        f"- 候補の採点: {comparison.candidate_slot}",
        f"- 提案の内容と差分: `{proposal_md}`",
        f"- 推奨: {NAMES[comparison.recommendation]}（採用するかは人が決める）",
        "",
        "## 推奨の理由",
        "",
        render.bullets(comparison.reasons),
        "",
        "## 指標",
        "",
        table(comparison.rows),
    ]
    return "\n".join(parts) + "\n"
