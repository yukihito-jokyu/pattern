"""1回の実行（rollout）。候補のスキルを入れた作業場所でタスクを解かせ、軌跡・成果物・完了の記録を残す。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from h2_kit import fsops, layout, profile, render, runner, sandbox, skilltree, transcript, workspace

RUN_MARK_VERSION = 1
TIMEOUT_SUBTYPE = "timeout"


@dataclass(frozen=True)
class Job:
    """1回の実行の依頼。directory は rollouts/<label>/。"""

    label: str
    directory: Path
    tree: skilltree.SkillTree
    task: workspace.Task
    model: profile.Profile


@dataclass(frozen=True)
class RolloutView:
    """終わった実行。ファイルは directory の下にある。"""

    label: str
    directory: Path
    record: workspace.RunRecord


def compute_fingerprint(job: Job) -> str:
    """スキル・依頼文・材料・コマンド行・軌跡の切り詰めが同じなら、同じ指紋になる。"""
    parts = [
        skilltree.compute_fingerprint(job.tree),
        job.task.prompt,
        fsops.compute_tree_sha256(job.task.directory / layout.TASK_WORKSPACE_DIR),
        *runner.build_rollout_command(job.model),
        str(job.model.obs_trunc),
        str(RUN_MARK_VERSION),
    ]
    return fsops.compute_text_sha256("\0".join(parts))


def build_skill_name(model: profile.Profile) -> str:
    """作業場所の .claude/skills/ の下に置く名前（対象スキルのディレクトリ名）。"""
    return Path(model.skill).name


def run_rollout(job: Job) -> RolloutView:
    """実行する。同じ指紋の完了の記録があれば実行せずに使い回す。run.json は最後に書く。"""
    fingerprint = compute_fingerprint(job)
    found = workspace.load_run_record(job.directory)
    if found is not None and found.fingerprint == fingerprint and found.mark_version == RUN_MARK_VERSION:
        return RolloutView(job.label, job.directory, found)
    fsops.remove_tree(job.directory)
    source = job.task.directory / layout.TASK_WORKSPACE_DIR
    skill_name = build_skill_name(job.model)
    place = sandbox.write_sandbox(source, job.tree, skill_name)
    try:
        done = runner.run_rollout(job.model, place, job.task.prompt)
        changes = sandbox.read_changes(source, place)
        sandbox.copy_output(place, job.directory / layout.OUTPUT_DIR)
    finally:
        sandbox.remove_sandbox(place)
    outcome = transcript.parse_outcome(done.stdout)
    fsops.write_text(job.directory / layout.STREAM_FILE, done.stdout)
    fsops.write_text(job.directory / layout.STDERR_FILE, done.stderr)
    trajectory = transcript.render_trajectory(done.stdout, job.model.obs_trunc, str(place))
    fsops.write_text(job.directory / layout.TRAJECTORY_FILE, trajectory)
    fsops.write_text(job.directory / layout.REPLY_FILE, outcome.reply)
    fsops.write_text(job.directory / layout.DELIVERABLE_FILE, render_deliverable(outcome.reply, changes))
    record = workspace.RunRecord(
        label=job.label,
        fingerprint=fingerprint,
        ok=not done.timed_out and outcome.finished,
        delivered=is_delivered(job.model.deliverable, outcome, changes),
        skill_invoked=is_skill_invoked(job.task.prompt, skill_name, outcome),
        cost_usd=outcome.cost_usd,
        num_turns=outcome.num_turns,
        subtype=TIMEOUT_SUBTYPE if done.timed_out else outcome.subtype,
        permission_denials=outcome.permission_denials,
        mark_version=RUN_MARK_VERSION,
    )
    fsops.write_json(job.directory / layout.RUN_FILE, workspace.build_json(record))
    return RolloutView(job.label, job.directory, record)


def is_skill_invoked(prompt: str, skill_name: str, outcome: transcript.Outcome) -> bool:
    """スキルが呼ばれたか。依頼文が `/<名前>` で始まると、stream に Skill の呼び出しが出ずに中身が入る。"""
    words = prompt.strip().split(maxsplit=1)
    return skill_name in outcome.skills or (bool(words) and words[0] == f"/{skill_name}")


def is_delivered(deliverable: str, outcome: transcript.Outcome, changes: list[sandbox.FileChange]) -> bool:
    """成果物を出したか。files は作業場所のファイルを足すか変えたこと、reply は返答があること。"""
    wrote = any(change.kind != skilltree.REMOVED for change in changes)
    replied = outcome.finished and not outcome.is_error and bool(outcome.reply.strip())
    if deliverable == profile.FILES_DELIVERABLE:
        return wrote
    if deliverable == profile.REPLY_DELIVERABLE:
        return replied
    return wrote or replied


def render_deliverable(reply: str, changes: list[sandbox.FileChange]) -> str:
    """成果物の Markdown。最後の返答と、作業場所で変わったファイルの中身か差分。"""
    parts = ["# 最後の返答", reply.strip() or "（返答がありません）", "# 作業場所で変わったファイル"]
    if not changes:
        parts.append("（変わったファイルはありません）")
    for change in changes:
        parts.append(f"## {change.kind}: `{change.path}`")
        if change.body:
            parts.append(render.render_fence(change.body, "diff" if change.kind == skilltree.MODIFIED else ""))
        elif not change.is_text:
            parts.append("（テキストでないファイル）")
    return render.render_sections(parts)


def read_trajectory(view: RolloutView) -> str:
    return fsops.read_text_or_none(view.directory / layout.TRAJECTORY_FILE) or ""


def read_deliverable(view: RolloutView) -> str:
    return fsops.read_text_or_none(view.directory / layout.DELIVERABLE_FILE) or ""
