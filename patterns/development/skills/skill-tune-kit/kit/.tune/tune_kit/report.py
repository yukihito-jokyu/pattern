"""最後の評価までの経過を report.md にまとめ（report）、人が決めたら最良の版を対象スキルに適用する（apply）。"""

from __future__ import annotations

from tune_kit import contracts, fsops, layout, metrics, plan, render, workspace
from tune_kit.errors import StageError


def _require_final(where: layout.Layout, approved: workspace.Approved) -> str:
    """最後の評価と最後の監査が終わっていれば、最良の版を返す。"""
    decisions = workspace.load_decisions(where)
    best = workspace.compute_current(decisions)
    tested = all(
        workspace.has_results(where, approved, version, (plan.TEST,)) for version in (layout.FIRST_VERSION, best)
    )
    if (
        where.round_dir(len(decisions) + 1).is_dir()
        or not tested
        or not (where.final_dir / layout.AUDIT_MD_FILE).is_file()
    ):
        raise StageError("報告は、最後の評価と最後の監査が終わってから書きます。status を実行してください")
    return best


def _build_advice(first: metrics.Summary, best: metrics.Summary, best_version: str) -> str:
    if best_version == layout.FIRST_VERSION:
        return "採用された候補が無い。対象スキルは変えない"
    if best.pass_rate > first.pass_rate:
        return f"最良の版 {best_version} はテスト用でも元の版より良い。適用を勧める"
    if best.pass_rate == first.pass_rate and best.check_rate >= first.check_rate:
        return f"最良の版 {best_version} はテスト用の合格率が元の版と同じ。差分を読んで決める"
    return f"最良の版 {best_version} はテスト用で元の版より悪い（検証用への合わせすぎの疑い）。適用は勧めない"


def _render_summary(where: layout.Layout, approved: workspace.Approved, best: str, reason: str) -> list[str]:
    first = workspace.load_summary(where, approved, layout.FIRST_VERSION, plan.TEST)
    final = workspace.load_summary(where, approved, best, plan.TEST)
    counts = "、".join(f"{name} {len(approved.list_cases(name))} 件" for name in plan.SPLITS)
    rows = [
        ["テスト用の合格率", render.render_rate(first.pass_rate), render.render_rate(final.pass_rate)],
        ["テスト用の検査の通過率", render.render_rate(first.check_rate), render.render_rate(final.check_rate)],
    ]
    return [
        "## 結論",
        "",
        _build_advice(first, final, best),
        "",
        render.render_table(["指標", f"元の版 {layout.FIRST_VERSION}", f"最良の版 {best}"], rows),
        "",
        render.render_table(
            ["項目", "値"],
            [
                ["対象スキル", approved.model.target.skill_path],
                ["ゴール", approved.model.goal],
                ["モード", approved.model.mode],
                ["ケース", counts],
                ["止めた理由", reason],
            ],
        ),
        "",
    ]


def _render_rounds(where: layout.Layout, approved: workspace.Approved) -> list[str]:
    train_ids = [case.id for case in approved.list_cases(plan.TRAIN)]
    rows = []
    for decision in workspace.load_decisions(where):
        proposal = workspace.load_proposal(where, decision.round, train_ids)
        changes = " / ".join(f"{change.file}: {change.summary}" for change in proposal.changes) or render.MISSING
        rows.append(
            [
                str(decision.round),
                f"{decision.current} → {decision.candidate}",
                f"{render.render_rate(decision.train_before)} → {render.render_rate(decision.train_after)}",
                f"{render.render_rate(decision.val_before)} → {render.render_rate(decision.val_after)}",
                "採用" if decision.adopted else "不採用",
                decision.reason,
                changes,
            ]
        )
    table = render.render_table(["ラウンド", "版", "学習用の合格率", "検証用の合格率", "採否", "理由", "変更"], rows)
    rounds_dir = where.display(where.target_dir / layout.ROUNDS_DIR)
    note = f"各ラウンドの比較と提案は {rounds_dir}/r<N>/ の compare.md と proposal.md にある。"
    return ["## ラウンドの経過", "", table if rows else "ラウンドなし", "", note, ""]


def _render_fixes(approved: workspace.Approved) -> list[str]:
    rows = [
        [entry.on, entry.detail, "変わった" if entry.test_changed else "変わらない"]
        for entry in approved.approval.history
        if entry.kind == contracts.DATA_FIX_KIND
    ]
    warnings = [entry.on for entry in approved.approval.history if entry.test_changed]
    lines = ["## データの直し（人が承認したもの）", ""]
    lines += [render.render_table(["日付", "直した指摘", "テスト用の採点"], rows) if rows else "なし", ""]
    if warnings:
        lines += [
            f"注意: テスト用のケースの採点が承認の後に変わった（{', '.join(warnings)}）。"
            "テスト用の結果は変わった後の基準で測った。",
            "",
        ]
    return lines


def _render_cases(where: layout.Layout, approved: workspace.Approved, best: str) -> list[str]:
    first = dict(workspace.load_summary(where, approved, layout.FIRST_VERSION, plan.TEST).case_rates)
    final = workspace.load_summary(where, approved, best, plan.TEST)
    rows = [
        [case_id, render.render_rate(first.get(case_id)), render.render_rate(rate)]
        for case_id, rate in final.case_rates
    ]
    checks = [[check_id, render.render_rate(rate)] for check_id, rate in final.check_rates]
    return [
        "## テスト用のケースごとの合格率",
        "",
        render.render_table(["ケース", layout.FIRST_VERSION, best], rows),
        "",
        f"## テスト用の検査ごとの通過率（最良の版 {best}）",
        "",
        render.render_table(["検査", "通過率"], checks),
        "",
    ]


def _render_audit(where: layout.Layout, approved: workspace.Approved, best: str) -> list[str]:
    originals = workspace.list_failing_cases(where, approved, best, (plan.TEST,))
    found = workspace.load_audit(where, None, approved, originals)
    rows = [[f.id, f.case_id, f.cause, f.summary] for f in found.findings]
    data_rows = [row for row, f in zip(rows, found.findings) if f.cause != contracts.SKILL_CAUSE]
    lines = ["## テスト用の監査（報告のみ。データは直していない）", ""]
    lines += [render.render_table(["ID", "ケース", "原因", "要約"], rows) if rows else "指摘なし", ""]
    if data_rows:
        lines += [
            f"テスト用のデータに疑わしい点が {len(data_rows)} 件ある。"
            "直すかは人が決める（直すなら計画を直して承認からやり直す）。",
            "",
        ]
    lines += [f"詳細: {where.display(where.final_dir / layout.AUDIT_MD_FILE)}", ""]
    return lines


def report(where: layout.Layout) -> str:
    approved = workspace.load_approved(where)
    best = _require_final(where, approved)
    decisions = workspace.load_decisions(where)
    reason = workspace.compute_stop_reason(
        approved.model, decisions, workspace.load_summary(where, approved, best, plan.VAL)
    )
    sections = [f"# 改善の報告: {approved.model.target.id}", ""]
    sections += _render_summary(where, approved, best, reason)
    sections += _render_rounds(where, approved)
    sections += _render_fixes(approved)
    sections += _render_cases(where, approved, best)
    sections += _render_audit(where, approved, best)
    sections += ["## 版の置き場", "", f"最良の版: {where.display(where.version_dir(best))}", ""]
    fsops.write_text(where.report_path, "\n".join(sections))
    return f"報告を書きました: {where.display(where.report_path)}（最良の版 {best}）"


def apply(where: layout.Layout, skip: bool, today: str) -> str:
    approved = workspace.load_approved(where)
    best = _require_final(where, approved)
    if not where.report_path.is_file() or workspace.load_applied(where) is not None:
        raise StageError("適用を決める段階ではありません。status を実行してください")
    if best == layout.FIRST_VERSION:
        raise StageError("採用された候補が無いので、適用するものはありません")
    if not skip and workspace.compute_skill_sha(where, approved.model) != approved.approval.skill_sha:
        raise StageError(
            f"承認の後に対象スキル {approved.model.target.skill_path} が変わりました。"
            f"手で {where.display(where.version_dir(best))} と見比べて取り込んでください"
        )
    if not skip:
        skill_dir = where.skill_dir(approved.model.target.skill_path)
        fsops.remove_tree(skill_dir)
        fsops.copy_tree(where.version_dir(best), skill_dir)
    fsops.write_json(
        where.applied_path, contracts.build_applied_data(contracts.Applied(applied=not skip, version=best, on=today))
    )
    if skip:
        return f"適用を見送りました（最良の版は {where.display(where.version_dir(best))} に残しています）"
    return f"対象スキル {approved.model.target.skill_path} を最良の版 {best} で置き換えました"
