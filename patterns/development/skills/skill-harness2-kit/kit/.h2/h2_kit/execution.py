"""run の段。承認したタスクを順に流し、モードごとに改善・選択・振り返りを行い、summary.json を書く。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from h2_kit import (
    context,
    fsops,
    layout,
    library,
    recursion,
    reflection,
    render,
    rollout,
    selection,
    skilltree,
    workspace,
)
from h2_kit.errors import StageError


@dataclass(frozen=True)
class Round:
    """承認したラウンドの、全タスクに共通の値。"""

    where: layout.Layout
    approved: workspace.Approved
    base_tree: skilltree.SkillTree
    report: Callable[[str], None]


def run(where: layout.Layout, task_id: str | None, report: Callable[[str], None]) -> str:
    """承認したタスクを順に流す。終わったタスク・モード（summary.json がある）は飛ばす。"""
    approved = workspace.load_approved(where)
    current, _ = workspace.load_skill(where, approved.profile)
    if skilltree.compute_fingerprint(current) != approved.skill_fingerprint:
        raise StageError("承認の後に対象スキルが変わりました。check を見せ直してから approve を実行してください")
    ids = [task.task_id for task in approved.tasks]
    if task_id is not None and task_id not in ids:
        raise StageError(f"タスク {task_id} は承認したタスク（{', '.join(ids)}）にありません")
    base_tree, _ = skilltree.read_tree(where.base_skill_dir(approved.round))
    state = Round(where, approved, base_tree, report)
    for position, task in enumerate(approved.tasks):
        if task_id in (None, task.task_id):
            _run_task(state, task, ids[:position])
    return _render_overview(where, approved)


def _render_overview(where: layout.Layout, approved: workspace.Approved) -> str:
    rows = []
    for task in approved.tasks:
        place = where.task_place(approved.round, task.task_id)
        for mode in approved.profile.modes:
            summary = workspace.load_summary(place, mode)
            chosen = (summary.chosen_label or "なし") if summary is not None else "未完了"
            cost = render.render_usd(summary.cost_usd) if summary is not None else ""
            rows.append([task.task_id, mode, chosen, cost])
    table = render.render_table(["タスク", "モード", "選ばれた候補", "費用"], rows)
    return f"{table}\n次: show {where.target} を人に見せる"


def _run_task(state: Round, task: workspace.Task, earlier: Sequence[str]) -> None:
    place = state.where.task_place(state.approved.round, task.task_id)
    modes = [mode for mode in state.approved.profile.modes if workspace.load_summary(place, mode) is None]
    if not modes:
        state.report(f"{task.task_id}: 終わっています")
        return
    state.report(f"{task.task_id}: 基準の実行 {state.approved.profile.k} 回")
    base = recursion.run_base(state.approved.profile, task, place, state.base_tree)
    for mode in modes:
        state.report(f"{task.task_id}/{mode}: 提案・試行・合成")
        _run_mode(state, task, earlier, tuple(base), mode)


def _run_mode(
    state: Round, task: workspace.Task, earlier: Sequence[str], base: tuple[rollout.RolloutView, ...], mode: str
) -> None:
    where = state.where
    model = state.approved.profile
    place = where.task_place(state.approved.round, task.task_id)
    view = library.copy_earlier(where.library_dir(state.approved.round, mode), earlier, place.library_view_dir(mode))
    env = recursion.Env(model, task, place, mode, state.base_tree, base, view, where.templates_dir)
    result = recursion.run_mode(env)
    finals = [found for found in result.views if found.label in {stage.label for stage in result.finals}]
    source = task.directory / layout.TASK_WORKSPACE_DIR
    request = selection.Request(
        model, task.prompt, source, place.selection_dir(mode), where.templates_dir, task.task_id, mode
    )
    selected = selection.run_selection(request, selection.build_pool(finals))
    reflected = _run_reflection(state, task, env, result, selected) if selected.chosen_label else None
    tree = _find_tree(result, selected.chosen_label, state.base_tree)
    if reflected is not None and reflected.experience is not None:
        entry = library.Entry(task.task_id, selected.chosen_label, selected.why, reflected.edits, reflected.experience)
        library.write_entry(where.library_dir(state.approved.round, mode), tree, entry)
    summary = _build_summary(task.task_id, mode, result, selected, reflected, tree)
    fsops.write_json(place.summary_path(mode), workspace.build_json(summary))
    state.report(f"{task.task_id}/{mode}: 選ばれた候補 {selected.chosen_label or 'なし'}")


def _run_reflection(
    state: Round, task: workspace.Task, env: recursion.Env, result: recursion.ModeResult, selected: selection.Selected
) -> reflection.Reflected:
    views = {view.label: view for view in result.views}
    pool = tuple(context.PoolEntry(stage.label, stage.tree, views.get(stage.label)) for stage in result.stages)
    chosen = next(entry for entry in pool if entry.label == selected.chosen_label)
    request = reflection.Request(
        model=env.model,
        prompt=task.prompt,
        source_dir=task.directory / layout.TASK_WORKSPACE_DIR,
        place=env.place.reflection_dir(env.mode),
        templates=env.templates,
        views=result.views,
        chosen=chosen,
        base_tree=state.base_tree,
        candidates=pool,
        decisions=tuple((stage.label, stage.notes or stage.error) for stage in result.stages),
    )
    return reflection.run_reflection(request, selected.chosen_id, selected.why, selected.id_map)


def _find_tree(result: recursion.ModeResult, label: str, fallback: skilltree.SkillTree) -> skilltree.SkillTree:
    return next((stage.tree for stage in result.stages if stage.label == label), fallback)


def _build_summary(
    task_id: str,
    mode: str,
    result: recursion.ModeResult,
    selected: selection.Selected,
    reflected: reflection.Reflected | None,
    tree: skilltree.SkillTree,
) -> workspace.Summary:
    own = [view for view in result.views if not layout.is_base_label(view.label)]
    cost = sum(stage.cost_usd for stage in result.stages) + sum(view.record.cost_usd for view in own)
    cost += selected.cost_usd + (reflected.cost_usd if reflected is not None else 0.0)
    return workspace.Summary(
        task_id=task_id,
        mode=mode,
        k=len(result.finals),
        chosen_label=selected.chosen_label,
        chosen_id=selected.chosen_id,
        why=selected.why,
        fallback=selected.fallback,
        error=selected.error,
        chosen_fingerprint=skilltree.compute_fingerprint(tree) if selected.chosen_label else "",
        finals=tuple(stage.label for stage in result.finals),
        delivered=tuple(view.label for view in result.views if view.record.delivered),
        kept_base=tuple(stage.label for stage in result.stages if stage.kept_base),
        fell_back=tuple(stage.label for stage in result.stages if stage.fell_back),
        rollouts=result.book.rollouts,
        sessions=result.book.sessions,
        diversity=result.diversity,
        lesson=reflected is not None and reflected.experience is not None,
        cost_usd=round(cost, 4),
    )
