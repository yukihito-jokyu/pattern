"""候補の版を採るかを、検証用のスコアで機械的に決める（decide。ADR 0008）。"""

from __future__ import annotations

from tune_kit import contracts, fsops, layout, metrics, plan, render, workspace
from tune_kit.errors import StageError

NO_CHANGE = "学習役が変更を提案しなかった"


def _require_round(where: layout.Layout, approved: workspace.Approved, number: int) -> None:
    decided = len(workspace.load_decisions(where))
    if decided != number - 1:
        raise StageError(
            f"{number} 回目のラウンドは今のラウンドではありません（決定済み {decided} 回）。status を実行してください"
        )
    if not (where.round_dir(number) / layout.PROPOSAL_MD_FILE).is_file():
        raise StageError(
            f"{number} 回目のラウンドの提案が検査されていません（learn-check の前）。status を実行してください"
        )
    if approved.model.budget.max_rounds < number:
        raise StageError(
            f"ラウンドの上限（{approved.model.budget.max_rounds}）を超えています。status を実行してください"
        )


def _render_rates(label: str, current: metrics.Summary, candidate: metrics.Summary) -> list[list[str]]:
    return [
        [f"{label}の合格率", render.render_rate(current.pass_rate), render.render_rate(candidate.pass_rate)],
        [f"{label}の検査の通過率", render.render_rate(current.check_rate), render.render_rate(candidate.check_rate)],
    ]


def _render_case_rows(current: metrics.Summary, candidate: metrics.Summary) -> list[list[str]]:
    after = dict(candidate.case_rates)
    rows = []
    for case_id, rate in current.case_rates:
        moved = after.get(case_id)
        mark = (
            "上がった"
            if moved is not None and moved > rate
            else "下がった"
            if moved is not None and moved < rate
            else ""
        )
        rows.append([case_id, render.render_rate(rate), render.render_rate(moved), mark])
    return rows


def _render_compare(
    number: int, names: tuple[str, str], summaries: tuple[metrics.Summary, ...], decision: metrics.Decision
) -> str:
    current_train, candidate_train, current_val, candidate_val = summaries
    rows = _render_rates("学習用", current_train, candidate_train) + _render_rates("検証用", current_val, candidate_val)
    warnings = []
    if decision.regressions:
        warnings.append(f"検証用で退行したケース: {', '.join(decision.regressions)}")
    if decision.overfit:
        warnings.append("学習用だけが良くなり、検証用は良くならなかった（学習用への合わせすぎの疑い）")
    return "\n".join(
        [
            f"# {number} 回目のラウンドの比較",
            "",
            f"結論: {'採用' if decision.adopted else '不採用'}（{decision.reason}）",
            "",
            render.render_table(["指標", f"今の版 {names[0]}", f"候補 {names[1]}"], rows),
            "",
            "## 検証用のケースごとの合格率",
            "",
            render.render_table(["ケース", names[0], names[1], "変化"], _render_case_rows(current_val, candidate_val)),
            "",
            "## 警告",
            "",
            render.render_bullets(warnings),
            "",
        ]
    )


def decide(where: layout.Layout, number: int) -> str:
    approved = workspace.load_approved(where)
    _require_round(where, approved, number)
    current = workspace.compute_current(workspace.load_decisions(where))
    candidate = layout.build_version(number)
    directory = where.round_dir(number)
    train_ids = [case.id for case in approved.list_cases(plan.TRAIN)]
    proposal = workspace.load_proposal(where, number, train_ids)
    if not proposal.changes:
        record = contracts.DecisionRecord(number, current, candidate, False, NO_CHANGE, None, None, None, None)
        fsops.write_text(
            directory / layout.COMPARE_MD_FILE, f"# {number} 回目のラウンドの比較\n\n結論: 不採用（{NO_CHANGE}）\n"
        )
    else:
        summaries = (
            workspace.load_summary(where, approved, current, plan.TRAIN),
            workspace.load_summary(where, approved, candidate, plan.TRAIN),
            workspace.load_summary(where, approved, current, plan.VAL),
            workspace.load_summary(where, approved, candidate, plan.VAL),
        )
        decision = metrics.compute_decision(summaries[2], summaries[3], summaries[0], summaries[1])
        record = contracts.DecisionRecord(
            round=number,
            current=current,
            candidate=candidate,
            adopted=decision.adopted,
            reason=decision.reason,
            train_before=summaries[0].pass_rate,
            train_after=summaries[1].pass_rate,
            val_before=summaries[2].pass_rate,
            val_after=summaries[3].pass_rate,
        )
        fsops.write_text(
            directory / layout.COMPARE_MD_FILE, _render_compare(number, (current, candidate), summaries, decision)
        )
    # decision.json は最後に書く。decision.json の有無で「ラウンドが終わった」を判定するため
    fsops.write_json(directory / layout.DECISION_FILE, contracts.build_decision_data(record))
    verdict = f"採用: 今の版は {candidate} になりました" if record.adopted else f"不採用: 今の版は {current} のままです"
    return f"{verdict}（{record.reason}）。{where.display(directory / layout.COMPARE_MD_FILE)} を書きました"
