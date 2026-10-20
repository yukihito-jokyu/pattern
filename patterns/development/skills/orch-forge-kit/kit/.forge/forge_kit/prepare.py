"""1回の評価を準備する。評価に使うバンドルを写し、実行ごとにリポジトリのコピーとプロンプトを作り、plan.json を書く。"""

from __future__ import annotations

from pathlib import Path

from forge_kit import bundle, charter, contracts, fsops, layout, proc, prompts, workspace
from forge_kit.errors import InvalidFileError, StageError
from forge_kit.layout import Layout, Slot


def prepare(where: Layout, slot: Slot) -> str:
    model, sha = workspace.approved_charter(where)
    if where.plan_path(slot).is_file():
        raise StageError(f"{slot.name} は準備済みです。status で次にすることを確かめてください")
    name = model.target.skill_name
    source = _bundle_source(where, model, slot)
    problems = bundle.check(source, name)
    if problems:
        raise InvalidFileError(str(source), problems)
    env = model.environment
    fsops.remove_tree(where.work_dir(slot))
    fsops.remove_tree(where.slot_copies_dir(slot))
    bundle.copy(source, where.slot_bundle_dir(slot), name)
    fsops.write_json(where.fingerprint_path(slot), fsops.fingerprint(where.root, env.skip_dirs, env.link_dirs))
    runs = []
    for task in charter.slot_tasks(model, include_holdout=slot.variant == "final"):
        for agent_no in range(1, model.budget.agents + 1):
            runs.append(_prepare_run(where, model, slot, task, agent_no))
    plan = contracts.Plan(
        slot=slot.name,
        variant=slot.variant,
        round_no=slot.round_no,
        charter_sha256=sha,
        skill_name=name,
        bundle_source=str(source),
        runs=tuple(runs),
    )
    fsops.write_json(where.plan_path(slot), contracts.to_data(plan))
    return f"準備しました: {slot.name}（実行 {len(runs)} 件、コピーの置き場 {where.slot_copies_dir(slot)}）"


def _bundle_source(where: Layout, model: charter.Charter, slot: Slot) -> Path:
    if slot.variant != "candidate":
        return where.claude_dir
    if not where.proposal_md_path(slot.round_no).is_file():
        raise StageError(f"{slot.round_no} 回目の提案がまだ確かめられていません。先に propose を実行してください")
    proposed = where.proposed_dir(slot.round_no)
    if not bundle.has_bundle(proposed, model.target.skill_name):
        raise StageError(f"{proposed} に候補のバンドルがありません。分析役の出力を確かめてください")
    return proposed


def _prepare_run(where: Layout, model: charter.Charter, slot: Slot, task: charter.Task, agent_no: int) -> contracts.Run:
    run_id = layout.run_id(task.id, agent_no)
    copy = where.copy_dir(slot, run_id)
    env = model.environment
    fsops.copy_repo(where.root, copy, env.skip_dirs, env.link_dirs)
    bundle.strip_kit(copy / layout.CLAUDE_DIR)
    bundle.copy(where.slot_bundle_dir(slot), copy / layout.CLAUDE_DIR, model.target.skill_name)
    proc.git_baseline(copy)
    name = model.target.skill_name
    fsops.write_text(
        where.prompt_path(slot, run_id), prompts.render("executor", {"skill_name": name, "task_prompt": task.prompt})
    )
    fsops.write_text(where.system_path(slot, run_id), prompts.render("executor-system", {"skill_name": name}))
    return contracts.Run(run_id, task.id, agent_no)
