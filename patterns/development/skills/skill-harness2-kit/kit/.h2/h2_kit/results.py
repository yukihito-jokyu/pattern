"""show の段。タスク・モードごとに、選ばれた候補、理由、元との差分、notes、振り返り、台帳、採用のコマンドを出す。"""

from __future__ import annotations

from h2_kit import fsops, layout, ledger, render, skilltree, workspace
from h2_kit.errors import StageError


def show(where: layout.Layout, task_id: str | None, mode: str | None) -> str:
    approval = workspace.load_approval(where)
    if approval is None:
        raise StageError("承認がありません。check → 人の承認 → approve → run の後に show を実行してください")
    if task_id is not None and task_id not in approval.task_order:
        raise StageError(f"タスク {task_id} は承認したタスク（{', '.join(approval.task_order)}）にありません")
    base, _ = skilltree.read_tree(where.base_skill_dir(approval.round))
    parts: list[str] = []
    for current in approval.task_order:
        if task_id not in (None, current):
            continue
        place = where.task_place(approval.round, current)
        for name in layout.MODES:
            summary = workspace.load_summary(place, name)
            if mode in (None, name) and summary is not None:
                parts.append(_render_section(where, place, summary, base))
    if not parts:
        return (
            "表示できる結果がありません（run が終わっていないか、指定したタスク・モードがありません）\n次: status "
            + where.target
        )
    parts.append("次: 人に見せ、採用する候補か「採用しない」かを決めてもらう。採用するなら上の採用のコマンドを実行する")
    return render.render_sections(parts)


def _render_section(
    where: layout.Layout, place: layout.TaskPlace, summary: workspace.Summary, base: skilltree.SkillTree
) -> str:
    head = f"# {summary.task_id} / {summary.mode}"
    if not summary.chosen_label:
        return render.render_sections(
            [
                head,
                f"選ばれた候補はありません: {summary.error or '成果物を出した完成品がありません'}",
                _render_ledger(summary),
            ]
        )
    tree, _ = skilltree.read_tree(place.harness_dir(summary.mode, summary.chosen_label))
    code = skilltree.build_confirm_code(summary.chosen_fingerprint)
    changes = skilltree.compute_changes(base, tree)
    command = f"python3 .h2/h2.py adopt {where.target} --task {summary.task_id} --mode {summary.mode} --confirm {code}"
    facts = [
        f"選ばれた候補: `{summary.chosen_label}`（匿名の ID: {summary.chosen_id}）",
        f"選び方: {_render_how(summary)}",
        f"元のスキルからの変化: {_render_changes(changes)}",
        f"確認の符号: {code}",
        f"採用のコマンド: `{command}`",
    ]
    parts = [
        head,
        render.render_bullets(facts),
        "## 選んだ理由",
        summary.why or "（理由はありません）",
        "## 元のスキルとの差分",
        render.render_fence(skilltree.compute_diff(base, tree) or "（差分はありません）", "diff"),
        "## 合成の notes",
        fsops.read_text_or_none(place.decision_path(summary.mode, summary.chosen_label)) or "（notes はありません）",
        "## 振り返り（編集ごとの効果）",
        fsops.read_text_or_none(place.reflection_dir(summary.mode) / layout.EDITS_FILE) or "（編集の行はありません）",
        f"移せる教訓: {'ライブラリに残した' if summary.lesson else '残していない（NO_ENTRY か、読めない返答）'}",
        _render_ledger(summary),
        _render_finals(place, summary),
    ]
    return render.render_sections(parts)


def _render_how(summary: workspace.Summary) -> str:
    if summary.fallback:
        return f"選択役が失敗したため、並べた最初の完成品にした（{summary.error}）"
    if summary.k == 1:
        return "k = 1 のため選択役を起動していない"
    return "選択役が匿名の成果物を比べて選んだ"


def _render_changes(changes: list[skilltree.Change]) -> str:
    if not changes:
        return "変化なし（元のまま）"
    counts = {
        kind: sum(1 for change in changes if change.kind == kind)
        for kind in (skilltree.ADDED, skilltree.MODIFIED, skilltree.REMOVED)
    }
    added, modified, removed = counts[skilltree.ADDED], counts[skilltree.MODIFIED], counts[skilltree.REMOVED]
    return f"{len(changes)} ファイル（追加 {added}、変更 {modified}、削除 {removed}）"


def _render_ledger(summary: workspace.Summary) -> str:
    rows = [
        ["実行", str(len(summary.rollouts)), f"R = 4k = {ledger.compute_expected_rollouts(summary.k)}"],
        ["編集のセッション", str(len(summary.sessions)), f"P = 3k = {ledger.compute_expected_sessions(summary.k)}"],
    ]
    facts = [
        f"完成品の多様性（行の Jaccard の平均。1.0 は全部同じ）: {summary.diversity}",
        f"落ちて入力の木に戻った段: {', '.join(summary.fell_back) or 'なし'}",
        f"変えなかった段（KEEP_BASE）: {', '.join(summary.kept_base) or 'なし'}",
        f"このモードの費用（基準の実行を除く）: {render.render_usd(summary.cost_usd)}",
    ]
    return render.render_sections(
        ["## 台帳", render.render_table(["種類", "回数", "恒等式"], rows), render.render_bullets(facts)]
    )


def _render_finals(place: layout.TaskPlace, summary: workspace.Summary) -> str:
    rows = []
    for label in [*[name for name in summary.rollouts if layout.is_base_label(name)], *summary.finals]:
        mode = layout.BASE if layout.is_base_label(label) else summary.mode
        record = workspace.load_run_record(place.rollout_dir(mode, label))
        if record is None:
            continue
        rows.append(
            [
                label,
                "あり" if record.delivered else "なし",
                "あり" if record.skill_invoked else "なし",
                str(record.num_turns),
                record.subtype,
                render.render_usd(record.cost_usd),
            ]
        )
    table = render.render_table(["ラベル", "成果物", "スキルの呼び出し", "ターン", "終わり方", "費用"], rows)
    return render.render_sections(["## 基準の実行と完成品", table])
