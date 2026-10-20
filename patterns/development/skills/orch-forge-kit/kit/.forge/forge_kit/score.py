"""集めた事実と採点役の判定から、charter の指標を計算して scores.json と scores.md を書く。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

from forge_kit import catalog, charter, contracts, fsops, metrics, render, workspace
from forge_kit.errors import InvalidFileError, KitError, StageError
from forge_kit.layout import Layout, Slot


@dataclass(frozen=True)
class RunData:
    run: contracts.Run
    facts: contracts.Facts
    grade: contracts.Grade | None


def _is_met(data: RunData, key: str) -> bool:
    return data.grade is not None and any(item.key == key and item.met for item in data.grade.items)


def _share(data: RunData, prefix: str) -> float | None:
    """grade の中で prefix で始まる項目のうち、満たした割合。該当する項目が無ければ None。"""
    items = [item for item in data.grade.items if item.key.startswith(prefix)] if data.grade else []
    return sum(1.0 for item in items if item.met) / len(items) if items else None


def _shares(runs: Sequence[RunData], prefix: str) -> float | None:
    return metrics.mean([value for value in (_share(run, prefix) for run in runs) if value is not None])


def _delegation(runs: Sequence[RunData]) -> float | None:
    """編集のうちサブエージェントが行った割合を実行ごとに出して平均する。編集の無い実行は数えない。"""
    shares = [metrics.ratio(run.facts.edits_sub, run.facts.edits_sub + run.facts.edits_main) for run in runs]
    return metrics.mean([share for share in shares if share is not None])


def _known(values: Sequence[float | None]) -> float | None:
    return metrics.mean([value for value in values if value is not None])


Calculator = Callable[[Sequence[RunData]], "float | None"]
# カタログの指標ごとの、1つの課題での値の求め方。指標を足したら、ここと catalog.METRICS を一緒に変える
CALCULATORS: dict[str, Calculator] = {
    "check_pass": lambda runs: metrics.rate([run.facts.check_exit == 0 for run in runs]),
    "acceptance": lambda runs: _shares(runs, charter.ACCEPTANCE_KEY + ":"),
    "protected_untouched": lambda runs: metrics.rate([not run.facts.protected_changed for run in runs]),
    "completion": lambda runs: metrics.rate([run.facts.completed for run in runs]),
    "delegation": _delegation,
    "flow_conformance": lambda runs: _shares(runs, charter.STEP_KEY + ":"),
    "report_format": lambda runs: metrics.rate([_is_met(run, charter.REPORT_KEY) for run in runs]),
    "files_agreement": lambda runs: metrics.pairwise_agreement([frozenset(r.facts.changed_files) for r in runs]),
    "cost_usd": lambda runs: _known([run.facts.cost_usd for run in runs]),
    "duration_sec": lambda runs: _known([run.facts.duration_sec for run in runs]),
    "launches": lambda runs: metrics.mean([float(len(run.facts.launches)) for run in runs]),
}


def task_value(metric_id: str, runs: Sequence[RunData]) -> float | None:
    if catalog.is_custom(metric_id):
        return metrics.rate([_is_met(run, metric_id) for run in runs])
    return CALCULATORS[metric_id](runs)


def metric_scores(
    model: charter.Charter, task_ids: Sequence[str], runs: Sequence[RunData]
) -> tuple[contracts.MetricScore, ...]:
    scores = []
    for choice in model.metrics:
        metric = charter.definition(choice)
        by_task = tuple(
            contracts.TaskValue(task_id, task_value(choice.id, [r for r in runs if r.run.task_id == task_id]))
            for task_id in task_ids
        )
        value = metrics.mean([entry.value for entry in by_task if entry.value is not None])
        scores.append(
            contracts.MetricScore(
                id=choice.id,
                name=metric.name,
                priority=choice.priority,
                direction=metric.direction,
                threshold=choice.threshold,
                value=value,
                met=metrics.is_met(value, choice.threshold, metric.direction),
                by_task=by_task,
            )
        )
    return tuple(scores)


def _run_data(where: Layout, model: charter.Charter, slot: Slot, plan: contracts.Plan) -> list[RunData]:
    graded = charter.has_grader_items(model)
    runs, problems = [], []
    for run in plan.runs:
        facts = workspace.load_facts(where, slot, run.run_id)
        grade = None
        if graded:
            try:
                grade = workspace.load_grade(where, slot, run.run_id)
            except KitError as exc:
                problems.append(f"{run.run_id}: {exc.message}")
        runs.append(RunData(run, facts, grade))
    if problems:
        raise InvalidFileError(
            "採点役の出力", [*problems, "上の実行の採点役を、同じプロンプトでもう一度起動してください"]
        )
    return runs


def run_notes(data: RunData) -> tuple[str, ...]:
    facts, notes = data.facts, []
    if not facts.completed:
        notes.append("打ち切り" if facts.timed_out else "最後まで終えなかった")
    if facts.check_exit not in (None, 0):
        notes.append(f"検査が失敗（終了コード {facts.check_exit}）")
    if facts.protected_changed:
        notes.append(f"保護パスを変更: {', '.join(facts.protected_changed)}")
    if not facts.launches:
        notes.append("サブエージェントを起動しなかった")
    if facts.edits_main:
        notes.append(f"メインのセッションが {facts.edits_main} 回編集した")
    if facts.denials:
        notes.append(f"拒否された操作: {', '.join(facts.denials)}")
    for item in data.grade.items if data.grade else ():
        if not item.met:
            notes.append(f"{item.key} 未達: {item.evidence}")
    return tuple(notes)


def score(where: Layout, slot: Slot) -> str:
    model, sha = workspace.approved_charter(where)
    plan = workspace.load_plan(where, slot)
    if plan.charter_sha256 != sha:
        raise StageError(
            f"charter が {slot.name} の準備の後に変わりました。作業領域を消して prepare からやり直してください"
        )
    runs = _run_data(where, model, slot, plan)
    task_ids = list(dict.fromkeys(run.task_id for run in plan.runs))
    visible = [task_id for task_id in task_ids if not charter.is_holdout(task_id)]
    holdout = [task_id for task_id in task_ids if charter.is_holdout(task_id)]
    scores = contracts.Scores(
        slot=slot.name,
        variant=slot.variant,
        round_no=slot.round_no,
        charter_sha256=sha,
        metrics=metric_scores(model, visible, runs),
        holdout_metrics=metric_scores(model, holdout, runs) if holdout else (),
        run_notes=tuple(contracts.RunNote(r.run.run_id, r.run.task_id, run_notes(r)) for r in runs),
    )
    fsops.write_json(where.scores_path(slot), contracts.to_data(scores))
    fsops.write_text(where.scores_md_path(slot), render_scores(scores))
    verdict = "must の指標は全部達成" if scores.all_must_met else "must の指標に未達がある"
    return "\n".join([f"採点しました: {slot.name}（{verdict}）", summary_table(scores.metrics)])


def summary_table(scores: Sequence[contracts.MetricScore]) -> str:
    rows = [
        [s.id, s.name, s.priority, render.number(s.value), render.number(s.threshold), render.mark(s.met)]
        for s in scores
    ]
    return render.table(["id", "名前", "優先度", "値", "閾値", "判定"], rows)


def render_scores(scores: contracts.Scores) -> str:
    parts = [f"# {scores.slot} の採点", "", "## 指標", "", summary_table(scores.metrics), ""]
    if scores.metrics and scores.metrics[0].by_task:
        headers = ["id", *[entry.task_id for entry in scores.metrics[0].by_task]]
        rows = [[s.id, *[render.number(entry.value) for entry in s.by_task]] for s in scores.metrics]
        parts += ["## 課題ごとの値", "", render.table(headers, rows), ""]
    if scores.holdout_metrics:
        parts += ["## ホールドアウトの課題での値", "", summary_table(scores.holdout_metrics), ""]
    parts += ["## 実行ごとの所見", ""]
    for note in scores.run_notes:
        parts.append(f"### {note.run_id}\n\n{render.bullets(note.notes)}\n")
    return "\n".join(parts)
