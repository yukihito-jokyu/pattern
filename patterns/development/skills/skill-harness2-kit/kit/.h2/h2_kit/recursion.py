"""提案・試行・合成の段。並列モード（幅）と逐次モード（深さ）を、harness2 の順と予算 R = 4k、P = 3k で回す。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from h2_kit import (
    context,
    contracts,
    fsops,
    guards,
    layout,
    ledger,
    parallel,
    profile,
    prompts,
    render,
    rollout,
    runner,
    skilltree,
    validate,
    workspace,
)
from h2_kit.errors import CommandError, InvalidFileError, LeakError

STAGE_ATTEMPTS = 2
ERROR_LIMIT = 400
SEQUENTIAL_WIDTH = 2


@dataclass(frozen=True)
class Env:
    """1つのタスク・モードの改善に共通の値。base は基準の実行、library は前のタスクの分のライブラリ。"""

    model: profile.Profile
    task: workspace.Task
    place: layout.TaskPlace
    mode: str
    base_tree: skilltree.SkillTree
    base: tuple[rollout.RolloutView, ...]
    library: Path | None
    templates: Path


@dataclass(frozen=True)
class StageSpec:
    """1つの段の依頼。fallback は段の入力の木で、落ちたらこれを使う。"""

    label: str
    job: str
    fallback: skilltree.SkillTree
    evidence: context.Evidence


@dataclass(frozen=True)
class Stage:
    """1つの段の結果。fell_back なら tree は入力の木で、error に理由がある。"""

    label: str
    tree: skilltree.SkillTree
    notes: str
    kept_base: bool
    fell_back: bool
    error: str
    cost_usd: float
    autolinked: tuple[str, ...]


@dataclass(frozen=True)
class Checked:
    """返ってきた木を確かめた結果。rejected は差し戻しのときに次の試みの作業場所へ書き戻す木。"""

    tree: skilltree.SkillTree
    problems: str
    rejected: skilltree.SkillTree | None
    linked: tuple[str, ...]


@dataclass(frozen=True)
class ModeResult:
    """1つのモードの結果。views は台帳の順の全実行（基準を含む）、finals は完成品の段。"""

    stages: tuple[Stage, ...]
    views: tuple[rollout.RolloutView, ...]
    finals: tuple[Stage, ...]
    book: ledger.Book
    diversity: float


def run_base(
    model: profile.Profile, task: workspace.Task, place: layout.TaskPlace, tree: skilltree.SkillTree
) -> list[rollout.RolloutView]:
    """基準の実行 base1..k。モードで共有する。"""
    labels = [layout.build_label(layout.BASE, index) for index in range(1, model.k + 1)]
    jobs = [rollout.Job(label, place.rollout_dir(layout.BASE, label), tree, task, model) for label in labels]
    return parallel.run_ordered([partial(rollout.run_rollout, job) for job in jobs], model.width)


def run_mode(env: Env) -> ModeResult:
    if env.mode == layout.SEQUENTIAL:
        return _run_sequential(env)
    return _run_parallel(env)


def _run_parallel(env: Env) -> ModeResult:
    """幅：同じ証拠から 2k 個の候補を作り、k 人が独立に合成する。"""
    k = env.model.k
    evidence = _build_evidence(env, env.base_tree, (), ())
    specs = [
        _build_proposal(env, dimension, index, None, evidence)
        for index in range(1, k + 1)
        for dimension in (layout.INV, layout.DOM)
    ]
    proposals = _run_stages(env, specs, env.model.width)
    candidates = _run_rolls(env, proposals)
    pool = tuple(context.PoolEntry(stage.label, stage.tree, view) for stage, view in zip(proposals, candidates))
    composing = _build_evidence(env, env.base_tree, pool, _list_decisions(proposals))
    composers = [
        StageSpec(layout.build_label(layout.AGG, index), _render_compose(env, index), env.base_tree, composing)
        for index in range(1, k + 1)
    ]
    finals = _run_stages(env, composers, env.model.width)
    views = [*env.base, *candidates, *_run_rolls(env, finals)]
    return _build_result(env, [*proposals, *finals], views, finals)


def _run_sequential(env: Env) -> ModeResult:
    """深さ：k 段を順に回し、各段は今の版とそれまでの全候補・全版を読む。"""
    k = env.model.k
    current = env.base_tree
    history: list[context.PoolEntry] = []
    stages: list[Stage] = []
    views = list(env.base)
    checkpoints: list[Stage] = []
    for t in range(1, k + 1):
        evidence = _build_evidence(env, current, tuple(history), _list_decisions(stages))
        specs = [
            _build_proposal(env, dimension, t, t if k > 1 else None, evidence) for dimension in (layout.INV, layout.DOM)
        ]
        proposals = _run_stages(env, specs, min(SEQUENTIAL_WIDTH, env.model.width))
        rolled = _run_rolls(env, proposals)
        stages += proposals
        views += rolled
        history += [context.PoolEntry(stage.label, stage.tree, view) for stage, view in zip(proposals, rolled)]
        job = _render_compose(env, 1) if k == 1 else _render_round(env, t)
        composing = _build_evidence(env, current, tuple(history), _list_decisions(stages))
        spec = StageSpec(layout.build_label(layout.CHECKPOINT, t), job, current, composing)
        checkpoint = _run_stages(env, [spec], 1)[0]
        view = _run_roll(env, checkpoint)
        stages.append(checkpoint)
        views.append(view)
        checkpoints.append(checkpoint)
        history.append(context.PoolEntry(checkpoint.label, checkpoint.tree, view))
        current = checkpoint.tree
    return _build_result(env, stages, views, checkpoints)


def _run_stages(env: Env, specs: Sequence[StageSpec], width: int) -> list[Stage]:
    """段を並行に動かし、notes は入力の順で書く（ASYNC-01）。"""
    stages = parallel.run_ordered([partial(_run_stage, env, spec) for spec in specs], width)
    for stage in stages:
        fsops.write_text(env.place.decision_path(env.mode, stage.label), _build_decision(stage))
    return stages


def _run_stage(env: Env, spec: StageSpec) -> Stage:
    """証拠を作り、提案させ、検証に落ちたら1回だけ差し戻す。それでも落ちたら入力の木に戻す（fell_back）。"""
    first = env.place.session_dir(env.mode, spec.label, 1) / layout.CONTEXT_DIR
    try:
        built = context.write_context(first, spec.evidence, env.model.leak_globs)
    except (LeakError, InvalidFileError) as exc:
        return _build_fallback(spec, f"証拠を作れません: {exc}", 0.0)
    mission = prompts.render_prompt(env.templates, "mission", {"job": spec.job, "layout": built.layout})
    problems = ""
    cost = 0.0
    rejected: skilltree.SkillTree | None = None
    for attempt in range(1, STAGE_ATTEMPTS + 1):
        session = env.place.session_dir(env.mode, spec.label, attempt)
        if attempt > 1:
            _write_retry_context(first, session / layout.CONTEXT_DIR, rejected)
        try:
            reply = runner.run_session(env.model, session, mission + _render_rejected(env, problems), runner.EDIT_TOOLS)
        except (CommandError, InvalidFileError) as exc:
            return _build_fallback(spec, str(exc), cost)
        cost += reply.cost_usd
        if not reply.ok:
            return _build_fallback(spec, reply.error, cost)
        checked = _check_reply(env, spec, reply)
        if not checked.problems:
            return _build_accepted(spec, reply, checked, cost)
        problems, rejected = checked.problems, checked.rejected
    return _build_fallback(spec, problems, cost)


def _check_reply(env: Env, spec: StageSpec, reply: runner.Reply) -> Checked:
    """返ってきた木を読み、参照の名指しを直してから検証する。"""
    if reply.harness is None:
        return Checked(
            spec.fallback, "context/harness/ が返ってきませんでした。その場のファイルを編集してください", None, ()
        )
    tree, outside = skilltree.read_tree(reply.harness)
    if not tree.files and not outside:
        return Checked(spec.fallback, "context/harness/ が空で返ってきました。全部を消さずに編集してください", None, ())
    tree, linked = validate.build_autolinked(tree)
    found = validate.check_tree(tree, spec.fallback, outside)
    found += [
        f"{path} は leak_globs に当たります" for path in tree.paths if guards.is_leak_path(path, env.model.leak_globs)
    ]
    if not found:
        return Checked(tree, "", None, tuple(linked))
    # 編集面の外のファイルは書き戻さない（harness2 と同じく、次の試みは入力の木から始める）
    return Checked(tree, render.render_bullets(found), None if outside else tree, tuple(linked))


def _write_retry_context(first: Path, target: Path, rejected: skilltree.SkillTree | None) -> None:
    fsops.copy_tree(first, target)
    if rejected is not None:
        skilltree.write_tree(rejected, target / layout.HARNESS_DIR)


def _render_rejected(env: Env, problems: str) -> str:
    if not problems:
        return ""
    return "\n" + prompts.render_prompt(env.templates, "_rejected", {"problems": problems})


def _build_accepted(spec: StageSpec, reply: runner.Reply, checked: Checked, cost: float) -> Stage:
    kept = not skilltree.compute_changes(spec.fallback, checked.tree)
    notes = contracts.parse_notes(reply.text)
    return Stage(spec.label, checked.tree, notes, kept, False, "", cost, checked.linked)


def _build_fallback(spec: StageSpec, problems: str, cost: float) -> Stage:
    return Stage(spec.label, spec.fallback, "", False, True, problems[:ERROR_LIMIT], cost, ())


def _build_decision(stage: Stage) -> str:
    """後の段に渡す決定。harness2 と同じく notes、落ちた段はエラー。"""
    return stage.notes or stage.error


def _list_decisions(stages: Sequence[Stage]) -> tuple[tuple[str, str], ...]:
    return tuple((stage.label, _build_decision(stage)) for stage in stages)


def _build_evidence(
    env: Env,
    harness: skilltree.SkillTree,
    pool: tuple[context.PoolEntry, ...],
    decisions: tuple[tuple[str, str], ...],
) -> context.Evidence:
    return context.Evidence(
        prompt=env.task.prompt,
        source=env.task.directory / layout.TASK_WORKSPACE_DIR,
        rollouts=env.base,
        harness=harness,
        pool=pool,
        library=env.library,
        decisions=decisions,
    )


def _build_proposal(env: Env, dimension: str, index: int, round_t: int | None, evidence: context.Evidence) -> StageSpec:
    model = env.model
    values = {
        "work": model.work,
        "deliverable_word": model.deliverable_word,
        "domain_word": model.domain_word,
        "levers": model.inv_levers if dimension == layout.INV else model.dom_levers,
        "yardstick": prompts.render_part(env.templates, "_yardstick", {"text": model.yardstick}, bool(model.yardstick)),
        "candidate_of": prompts.render_part(
            env.templates, "_candidate-of", {"index": str(index), "k": str(model.k)}, model.k > 1
        ),
        "round": prompts.render_part(env.templates, "_round", {"t": str(round_t)}, round_t is not None),
    }
    job = prompts.render_prompt(env.templates, f"propose-{dimension}", values)
    harness = evidence.harness or env.base_tree
    return StageSpec(layout.build_label(dimension, index), job, harness, evidence)


def _render_compose(env: Env, index: int) -> str:
    """並列モードの agg<index> と、k が 1 の逐次モードの合成（harness2 は k = 1 で aggregate を使う）。"""
    k = env.model.k
    values = {
        "work": env.model.work,
        "domain_word": env.model.domain_word,
        "k": str(k),
        "candidate_count": str(2 * k),
        "example_failed": str(min(max(k - 1, 2), k)),
        "parallel_composers": prompts.render_part(
            env.templates, "_parallel-composers", {"k": str(k), "index": str(index)}, k > 1
        ),
        "yardstick": prompts.render_part(
            env.templates, "_yardstick", {"text": env.model.yardstick}, bool(env.model.yardstick)
        ),
    }
    return prompts.render_prompt(env.templates, "compose", values)


def _render_round(env: Env, t: int) -> str:
    k = env.model.k
    final = t >= k
    values = {
        "work": env.model.work,
        "domain_word": env.model.domain_word,
        "t": str(t),
        "k": str(k),
        "first_round": prompts.render_part(env.templates, "_first-round", {}, t == 1),
        "round_job": prompts.render_prompt(
            env.templates, "_compose-final" if final else "_compose-checkpoint", {"t": str(t)}
        ),
    }
    return prompts.render_prompt(env.templates, "compose-round", values)


def _run_rolls(env: Env, stages: Sequence[Stage]) -> list[rollout.RolloutView]:
    return parallel.run_ordered([partial(_run_roll, env, stage) for stage in stages], env.model.width)


def _run_roll(env: Env, stage: Stage) -> rollout.RolloutView:
    """段の木を harnesses/<label>/ に書いてから1回実行する。"""
    skilltree.write_tree(stage.tree, env.place.harness_dir(env.mode, stage.label))
    job = rollout.Job(stage.label, env.place.rollout_dir(env.mode, stage.label), stage.tree, env.task, env.model)
    return rollout.run_rollout(job)


def _build_result(
    env: Env, stages: Sequence[Stage], views: Sequence[rollout.RolloutView], finals: Sequence[Stage]
) -> ModeResult:
    book = ledger.build_book([view.label for view in views], [stage.label for stage in stages])
    ledger.require_identity(book, env.model.k)
    diversity = skilltree.compute_diversity([stage.tree for stage in finals])
    return ModeResult(tuple(stages), tuple(views), tuple(finals), book, diversity)
