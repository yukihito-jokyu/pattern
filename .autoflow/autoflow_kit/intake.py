"""受付の段（start）。承認済みのプロファイルを確かめ、既存変更を含む開始状態と作業ブランチを記録する。"""

from __future__ import annotations

from pathlib import Path

from autoflow_kit import changes, fsops, layout, proc, trail, workspace
from autoflow_kit.errors import StageError
from autoflow_kit.layout import Layout
from autoflow_kit.profile import Profile


def _check_repo(where: Layout) -> None:
    if proc.git_toplevel(where.root) != where.root.resolve():
        raise StageError(f"{where.root} は git のリポジトリのルートではありません。ルートで実行する")
    intake = where.relative(where.intake_path)
    if not proc.git_is_ignored(where.root, intake):
        raise StageError(
            f"{layout.KIT_DIR}/{layout.RUNS_DIR}/ が .gitignore に入っていません。.gitignore に足す"
        )


def _check_origin(origin: trail.Origin) -> None:
    if origin.source not in layout.SOURCES:
        raise StageError(f"--source は {', '.join(layout.SOURCES)} のどれかにする（今: {origin.source}）")
    if layout.SOURCES[origin.source] and not origin.ref.strip():
        raise StageError(f"取得元 {origin.source} では --ref に課題の番号を渡す")
    if not origin.title.strip():
        raise StageError("--title に依頼の題名を渡す")


def _guide(where: Layout, settings: Profile) -> str:
    """開始時の版のレビューの指示。実行の途中で変わっても、探索役と検証役はこの写しを読む。"""
    parts = []
    for name in settings.review.guide_files:
        path = where.repo_path(name)
        if path.is_file():
            parts += [f"# {name}", "", fsops.read_text(path).rstrip(), ""]
    return "\n".join(parts) if parts else "- なし\n"


def _task(origin: trail.Origin, body: str) -> str:
    return "\n".join(
        [
            f"# {origin.title}",
            "",
            f"- 取得元: {origin.source}",
            f"- 番号: {origin.ref or '—'}",
            f"- URL: {origin.url or '—'}",
            "",
            "## 依頼の本文",
            "",
            body.rstrip(),
            "",
        ]
    )


def start(where: Layout, origin: trail.Origin, body_path: Path, now: str) -> str:
    settings = workspace.approved_profile(where)
    _check_origin(origin)
    _check_repo(where)
    body = fsops.read_text(body_path)
    if not body.strip():
        raise StageError(f"{body_path} が空です。依頼の本文を書いてから start する")
    run_id = layout.make_run_id(now, origin.ref)
    if where.run_dir(run_id).exists():
        raise StageError(f"実行 {run_id} は既にあります。1秒おいてから start をやり直す")
    tree = changes.snapshot(where.root)
    branch = layout.make_branch(run_id)
    proc.git_switch_new(where.root, branch)
    fsops.write_text(where.task_path(run_id), _task(origin, body))
    fsops.write_text(where.guide_path(run_id), _guide(where, settings))
    fsops.copy_file(where.profile_path, where.snapshot_profile_path(run_id))
    fsops.append_line(
        where.trail_path(run_id), trail.encode(trail.started(origin, branch, tree, now, head=proc.git_head(where.root)))
    )
    return "\n".join(
        [
            f"実行: {run_id}",
            f"作業ブランチ: {branch}",
            f"依頼: {where.relative(where.task_path(run_id))}",
            f"次: {layout.CLI} status --run {run_id}",
        ]
    )
