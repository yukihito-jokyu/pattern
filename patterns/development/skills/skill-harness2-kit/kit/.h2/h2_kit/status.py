"""status の段。ファイルの有無から段階と次の手を求める。各行は LINE_KINDS のどれかで始める（OPS-01）。"""

from __future__ import annotations

from h2_kit import layout, workspace
from h2_kit.errors import KitError

LINE_KINDS = ("対象:", "段階:", "進み:", "問題:", "次:")
STAGES = ("準備", "承認待ち", "実行待ち", "実行中か中断", "結果の確認", "採用済み")


def status(where: layout.Layout) -> str:
    head = f"{LINE_KINDS[0]} {where.target}"
    if not where.profile_path.is_file():
        return _render(
            [head, _render_stage(0), f"{LINE_KINDS[4]} init {where.target} --skill <対象スキルのディレクトリ>"]
        )
    try:
        workspace.load_profile(where)
        approval = workspace.load_approval(where)
    except KitError as exc:
        return _render(
            [head, _render_stage(0), f"{LINE_KINDS[3]} {exc}", f"{LINE_KINDS[4]} 直してから check {where.target}"]
        )
    if approval is None:
        return _render_unapproved(where, head)
    try:
        approved = workspace.load_approved(where)
    except KitError as exc:
        return _render(
            [
                head,
                _render_stage(1),
                f"{LINE_KINDS[3]} {exc}",
                f"{LINE_KINDS[4]} check {where.target} → 人の承認 → approve {where.target}",
            ]
        )
    return _render_approved(where, head, approved)


def _render_unapproved(where: layout.Layout, head: str) -> str:
    if not where.plan_path.is_file():
        return _render([head, _render_stage(0), f"{LINE_KINDS[4]} プロファイルとタスクを書き、check {where.target}"])
    return _render([head, _render_stage(1), f"{LINE_KINDS[4]} plan.md を人に見せ、承認を得たら approve {where.target}"])


def _render_approved(where: layout.Layout, head: str, approved: workspace.Approved) -> str:
    progress = workspace.compute_progress(where, approved)
    count = f"{LINE_KINDS[2]} ラウンド {progress.round}、{progress.finished}/{progress.total}（タスク×モード）"
    adopted = [item for item in workspace.load_adoptions(where) if item.round == approved.round]
    if adopted:
        last = adopted[-1]
        done = (
            f"{LINE_KINDS[4]} {last.task_id}/{last.mode} の {last.label} を採用済み。新しいラウンドは check → approve"
        )
        return _render([head, _render_stage(5), count, done])
    if progress.finished == progress.total:
        return _render(
            [
                head,
                _render_stage(4),
                count,
                f"{LINE_KINDS[4]} show {where.target} を人に見せ、採用する候補か「採用しない」かを聞く",
            ]
        )
    if progress.finished == 0:
        return _render([head, _render_stage(2), count, f"{LINE_KINDS[4]} run {where.target}"])
    pending = f"{LINE_KINDS[4]} run {where.target}（続きから再開する。残り: {', '.join(progress.pending)}）"
    return _render([head, _render_stage(3), count, pending])


def _render_stage(index: int) -> str:
    return f"{LINE_KINDS[1]} {STAGES[index]}"


def _render(lines: list[str]) -> str:
    return "\n".join(lines)
