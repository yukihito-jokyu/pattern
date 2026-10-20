"""実行役が終わった後の事実（差分、検査の結果、実行の記録の集計）を集め、採点役へのプロンプトを書く。"""

from __future__ import annotations

from dataclasses import dataclass

from forge_kit import bundle, charter, contracts, fsops, layout, proc, prompts, render, trace, workspace
from forge_kit.errors import StageError
from forge_kit.layout import Layout, Slot

UNFINISHED = "実行役が最後まで終えなかったため、判定できない"
SHOWN_CHANGES = 20


@dataclass(frozen=True)
class Evidence:
    """1つの実行について集めた材料。check は検査を回さなかったとき None。"""

    record: trace.Trace
    execution: contracts.Execution
    check: proc.Result | None
    steps: tuple[str, ...]


def collect(where: Layout, slot: Slot, parallel: int) -> str:
    model, sha = workspace.approved_charter(where)
    plan = workspace.load_plan(where, slot)
    if plan.charter_sha256 != sha:
        raise StageError(
            f"charter が {slot.name} の準備の後に変わりました。作業領域を消して prepare からやり直してください"
        )
    executions = {run.run_id: workspace.load_execution(where, slot, run.run_id) for run in plan.runs}
    lines = _contamination(where, model, slot)
    checks = _run_checks(where, model, slot, plan, parallel)
    skill_md = fsops.read_text(where.slot_skill_md_path(slot, plan.skill_name))
    steps = bundle.steps(skill_md)
    jobs = []
    for run in plan.runs:
        record = workspace.load_trace(where, slot, run.run_id)
        evidence = Evidence(record, executions[run.run_id], checks.get(run.run_id), steps)
        facts = _facts(where, model, slot, run, evidence)
        fsops.write_json(where.facts_path(slot, run.run_id), contracts.to_data(facts))
        fsops.write_text(where.trace_md_path(slot, run.run_id), trace.render_trace(record))
        fsops.write_text(where.result_md_path(slot, run.run_id), record.result_text + "\n")
        if not charter.has_grader_items(model):
            continue
        if record.finished:
            jobs.append(_grader_prompt(where, model, slot, run, facts))
        else:
            _unfinished_grade(where, slot, facts)
            lines.append(f"WARN {run.run_id} は最後まで終えなかったため、採点役を起動せず全項目を未達にした")
    lines.insert(0, f"集めました: {slot.name}（実行 {len(plan.runs)} 件、採点役 {len(jobs)} 件）")
    return "\n".join(lines + jobs)


def _contamination(where: Layout, model: charter.Charter, slot: Slot) -> list[str]:
    """評価の間に元のリポジトリのファイルが変わっていないかを確かめる。変わっていれば人に見せる警告を返す。"""
    before = workspace.load_fingerprint(where, slot)
    env = model.environment
    after = fsops.fingerprint(where.root, env.skip_dirs, env.link_dirs)
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    if not changed:
        return []
    shown = ", ".join(changed[:SHOWN_CHANGES]) + (
        f" ほか {len(changed) - SHOWN_CHANGES} 件" if len(changed) > SHOWN_CHANGES else ""
    )
    return [f"WARN 評価の間に元のリポジトリで {len(changed)} 件のファイルが変わりました（人に確かめる）: {shown}"]


def _run_checks(
    where: Layout, model: charter.Charter, slot: Slot, plan: contracts.Plan, parallel: int
) -> dict[str, proc.Result]:
    if "check_pass" not in {choice.id for choice in model.metrics}:
        return {}
    env = model.environment
    directories = [where.copy_dir(slot, run.run_id) for run in plan.runs]
    for directory in directories:
        if not directory.is_dir():
            raise StageError(
                f"評価用のコピー {directory} がありません（OS が消した可能性）。prepare からやり直してください"
            )
    results = proc.shell_many(env.check_command, directories, env.check_timeout_sec, parallel)
    return {run.run_id: result for run, result in zip(plan.runs, results)}


def _facts(
    where: Layout, model: charter.Charter, slot: Slot, run: contracts.Run, evidence: Evidence
) -> contracts.Facts:
    record, execution, check = evidence.record, evidence.execution, evidence.check
    copy = where.copy_dir(slot, run.run_id)
    changed = proc.git_changed(copy)
    fsops.write_text(where.patch_path(slot, run.run_id), proc.git_patch(copy))
    targets = tuple(
        contracts.GradeTarget(key, text) for key, text in charter.grade_items(model, run.task_id, evidence.steps)
    )
    return contracts.Facts(
        run_id=run.run_id,
        task_id=run.task_id,
        completed=record.completed and execution.exit_code == 0 and not execution.timed_out,
        timed_out=execution.timed_out,
        changed_files=changed,
        check_exit=None if check is None else check.code,
        check_tail="" if check is None or check.code == 0 else check.tail,
        protected_changed=tuple(p for p in changed if layout.is_matched(p, model.environment.protected_paths)),
        launches=tuple(launch.agent for launch in record.launches),
        edits_main=len(record.edits_main),
        edits_sub=len(record.edits_sub),
        max_depth=record.max_depth,
        cost_usd=record.cost_usd,
        duration_sec=record.duration_sec,
        denials=record.denials,
        grade_targets=targets,
    )


def _grader_prompt(
    where: Layout, model: charter.Charter, slot: Slot, run: contracts.Run, facts: contracts.Facts
) -> str:
    task = next(task for task in model.tasks if task.id == run.task_id)
    values = {
        "run_id": run.run_id,
        "task_prompt": task.prompt,
        "skill_md": str(where.slot_skill_md_path(slot, model.target.skill_name)),
        "trace_md": str(where.trace_md_path(slot, run.run_id)),
        "result_md": str(where.result_md_path(slot, run.run_id)),
        "patch": str(where.patch_path(slot, run.run_id)),
        "items": render.bullets([f"`{target.key}`: {target.text}" for target in facts.grade_targets]),
        "grade": str(where.grade_path(slot, run.run_id)),
    }
    path = where.grader_prompt_path(slot, run.run_id)
    fsops.write_text(path, prompts.render("grader", values))
    return render.job(contracts.AGENTS["grader"], run.run_id, str(path))


def _unfinished_grade(where: Layout, slot: Slot, facts: contracts.Facts) -> None:
    items = tuple(contracts.GradeItem(target.key, False, UNFINISHED) for target in facts.grade_targets)
    fsops.write_json(where.grade_path(slot, facts.run_id), contracts.to_data(contracts.Grade(facts.run_id, items)))
