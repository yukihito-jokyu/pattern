"""judge の段。事後の検査を、基準の実行と選ばれた完成品の成果物で動かす。方法には使わない（STATE-04）。"""

from __future__ import annotations

import shlex
from dataclasses import asdict, dataclass
from pathlib import Path

from h2_kit import fsops, layout, proc, render, workspace
from h2_kit.errors import CommandError

JUDGE_PREFIX = "h2-judge-"
TASK_DIR_MARK = "{task_dir}"
REPLY_FILE_MARK = "{reply_file}"
SHELL = "/bin/sh"


@dataclass(frozen=True)
class Judged:
    """1つの実行・1つの検査の結果。passed が None なら判定できなかった（0点ではない）。"""

    task_id: str
    label: str
    check: str
    passed: bool | None


def judge(where: layout.Layout, task_id: str | None) -> str:
    approved = workspace.load_approved(where)
    rows: list[list[str]] = []
    for task in approved.tasks:
        if task_id not in (None, task.task_id):
            continue
        checks = workspace.load_checks(where.checks_path(task.task_id))
        place = where.task_place(approved.round, task.task_id)
        results = [
            _run_check(place, task.task_id, mode, label, check)
            for mode, label in _list_targets(place, approved)
            for check in checks
        ]
        data = {"h2_judged": True, "round": approved.round, "results": [asdict(item) for item in results]}
        fsops.write_json(place.judged_path, data)
        rows += [[item.task_id, item.label, item.check, _render_passed(item.passed)] for item in results]
    if not rows:
        return "動かした検査はありません（checks.json が無いか、run が終わっていません）"
    table = render.render_table(["タスク", "実行", "検査", "結果"], rows)
    return f"{table}\n事後の検査は改善の方法には使っていない。採用を決める材料の1つとして人が読む"


def _list_targets(place: layout.TaskPlace, approved: workspace.Approved) -> list[tuple[str, str]]:
    """基準の実行と、モードごとに選ばれた完成品。"""
    targets = [(layout.BASE, layout.build_label(layout.BASE, index)) for index in range(1, approved.profile.k + 1)]
    for mode in approved.profile.modes:
        summary = workspace.load_summary(place, mode)
        if summary is not None and summary.chosen_label:
            targets.append((mode, summary.chosen_label))
    return [(mode, label) for mode, label in targets if place.rollout_dir(mode, label).is_dir()]


def _run_check(place: layout.TaskPlace, task_id: str, mode: str, label: str, check: workspace.Check) -> Judged:
    rollout_dir = place.rollout_dir(mode, label)
    scratch = fsops.write_temp_dir(JUDGE_PREFIX)
    try:
        work = scratch / layout.OUTPUT_DIR
        _copy_or_empty(rollout_dir, scratch)
        command = _build_command(check.command, work, scratch / layout.REPLY_FILE)
        done = proc.run_command([SHELL, "-c", command], work, "", check.timeout_sec)
        passed = None if done.timed_out else done.code == 0
    except CommandError:
        passed = None
    finally:
        fsops.remove_tree(scratch)
    return Judged(task_id, label, check.name, passed)


def _copy_or_empty(rollout_dir: Path, scratch: Path) -> None:
    """何も出さなかった実行は、空の作業場所と空の返答で検査する。"""
    if (rollout_dir / layout.OUTPUT_DIR).is_dir():
        fsops.copy_tree(rollout_dir / layout.OUTPUT_DIR, scratch / layout.OUTPUT_DIR)
    else:
        fsops.write_dir(scratch / layout.OUTPUT_DIR)
    if (rollout_dir / layout.REPLY_FILE).is_file():
        fsops.copy_file(rollout_dir / layout.REPLY_FILE, scratch / layout.REPLY_FILE)
    else:
        fsops.write_text(scratch / layout.REPLY_FILE, "")


def _build_command(template: str, work: Path, reply: Path) -> str:
    return template.replace(TASK_DIR_MARK, shlex.quote(str(work))).replace(REPLY_FILE_MARK, shlex.quote(str(reply)))


def _render_passed(passed: bool | None) -> str:
    if passed is None:
        return "判定なし"
    return "通った" if passed else "落ちた"
