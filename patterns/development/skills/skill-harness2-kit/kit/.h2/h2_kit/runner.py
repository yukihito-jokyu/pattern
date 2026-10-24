"""`claude -p` のコマンド行を組み立て、実行と編集のセッションを動かす。閉じ込めのフラグはここだけに書く（OPS-05）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from h2_kit import fsops, layout, proc, profile, transcript, workspace

ROLLOUT_GUARD_FLAGS = (
    "--setting-sources",
    "project",
    "--strict-mcp-config",
    "--no-session-persistence",
    "--permission-prompts",
    "none",
)
SESSION_GUARD_FLAGS = (
    "--restricted",
    "--disable-slash-commands",
    "--strict-mcp-config",
    "--no-session-persistence",
    "--permission-prompts",
    "none",
)
EDIT_TOOLS = ("Read", "Edit", "Write", "Glob", "Grep")
READ_TOOLS = ("Read", "Glob", "Grep")
SESSION_PREFIX = "h2-session-"


@dataclass(frozen=True)
class Reply:
    """1回のセッションの結果。harness は返ってきた context/harness/ の写し（無ければ None）。"""

    text: str
    ok: bool
    cost_usd: float
    error: str
    harness: Path | None
    cached: bool


def build_rollout_tools(model: profile.Profile) -> list[str]:
    """実行の道具。対象スキルを呼べるように Skill を必ず含める。"""
    tools = list(model.rollout.tools)
    return tools if transcript.SKILL_TOOL in tools else [*tools, transcript.SKILL_TOOL]


def build_rollout_command(model: profile.Profile) -> list[str]:
    """実行のコマンド行。依頼文は標準入力で渡す。"""
    command = [*model.claude, "-p", "--output-format", "stream-json", "--verbose", *ROLLOUT_GUARD_FLAGS]
    command += ["--permission-mode", "acceptEdits", "--max-budget-usd", str(model.rollout.max_budget_usd)]
    if model.rollout.model:
        command += ["--model", model.rollout.model]
    return [*command, "--allowedTools", *build_rollout_tools(model)]


def build_session_command(model: profile.Profile, tools: Sequence[str]) -> list[str]:
    """編集・選択・振り返りのセッションのコマンド行。作業場所の外を読めず、コマンドを実行できない。"""
    command = [*model.claude, "-p", "--output-format", "json", *SESSION_GUARD_FLAGS, "--tools", ",".join(tools)]
    command += ["--permission-mode", "acceptEdits", "--max-budget-usd", str(model.improver.max_budget_usd)]
    if model.improver.model:
        command += ["--model", model.improver.model]
    if model.improver.effort:
        command += ["--effort", model.improver.effort]
    return command


def run_rollout(model: profile.Profile, sandbox: Path, prompt: str) -> proc.Completed:
    return proc.run_command(build_rollout_command(model), sandbox, prompt, model.rollout.timeout_sec)


def run_session(model: profile.Profile, session_dir: Path, prompt: str, tools: Sequence[str]) -> Reply:
    """session_dir/context を使い捨ての場所に写してセッションを動かし、context/harness/ を回収する。

    プロンプト・証拠・コマンド行が前回と同じなら、前回の結果を使い回す（harness2 のセッションのキャッシュ）。
    """
    command = build_session_command(model, tools)
    context_dir = session_dir / layout.CONTEXT_DIR
    key = fsops.compute_text_sha256("\0".join([prompt, fsops.compute_tree_sha256(context_dir), *command]))
    cached = workspace.load_session_record(session_dir)
    if cached is not None and cached.key == key and cached.ok:
        return _build_reply(session_dir, cached, was_cached=True)
    place = fsops.write_temp_dir(SESSION_PREFIX)
    try:
        fsops.copy_tree(context_dir, place / layout.CONTEXT_DIR)
        done = proc.run_command(command, place, prompt, model.improver.timeout_sec)
        _write_harvest(place / layout.CONTEXT_DIR / layout.HARNESS_DIR, session_dir / layout.HARNESS_DIR)
    finally:
        fsops.remove_tree(place)
    outcome = transcript.parse_result_json(done.stdout)
    record = workspace.SessionRecord(key, _is_ok(done, outcome), outcome.cost_usd, _build_error(done, outcome, model))
    fsops.write_text(session_dir / layout.MISSION_FILE, prompt)
    fsops.write_text(session_dir / layout.REPLY_FILE, outcome.reply)
    fsops.write_text(session_dir / layout.STDERR_FILE, done.stderr)
    fsops.write_json(session_dir / layout.SESSION_FILE, workspace.build_json(record))
    return _build_reply(session_dir, record, was_cached=False)


def _write_harvest(source: Path, target: Path) -> None:
    if source.is_dir():
        fsops.copy_tree(source, target)
    else:
        fsops.remove_tree(target)


def _build_reply(session_dir: Path, record: workspace.SessionRecord, was_cached: bool) -> Reply:
    harness = session_dir / layout.HARNESS_DIR
    return Reply(
        text=fsops.read_text_or_none(session_dir / layout.REPLY_FILE) or "",
        ok=record.ok,
        cost_usd=record.cost_usd,
        error=record.error,
        harness=harness if harness.is_dir() else None,
        cached=was_cached,
    )


def _is_ok(done: proc.Completed, outcome: transcript.Outcome) -> bool:
    return not done.timed_out and outcome.finished and not outcome.is_error


def _build_error(done: proc.Completed, outcome: transcript.Outcome, model: profile.Profile) -> str:
    if done.timed_out:
        return f"{model.improver.timeout_sec} 秒で時間切れになりました"
    if not outcome.finished:
        tail = " / ".join(done.stderr.strip().splitlines()[-3:])
        return f"claude の出力に結果がありません（終了コード {done.code}）: {tail}"
    if outcome.is_error:
        return f"claude がエラーで終わりました（{outcome.subtype}）: {outcome.reply[:200]}"
    return ""
