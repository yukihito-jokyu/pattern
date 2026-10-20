"""評価用のコピーごとに実行役（claude -p）を起動し、実行の記録を保存する。

引数はこのモジュールの command だけで組み立てる。
"""

from __future__ import annotations

from pathlib import Path

from forge_kit import charter, contracts, fsops, proc, workspace
from forge_kit.errors import StageError
from forge_kit.layout import Layout, Slot

CLAUDE = "claude"


def command(executor: charter.Executor, prompt: str, system_path: Path) -> list[str]:
    """実行役の引数（OPS-05）。権限は acceptEdits と charter の allowed_tools だけに限り、人に聞く道具を外す。"""
    args = [
        CLAUDE,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--no-session-persistence",
        "--max-budget-usd",
        str(executor.max_budget_usd),
        "--append-system-prompt-file",
        str(system_path),
    ]
    if executor.model:
        args += ["--model", executor.model]
    if executor.allowed_tools:
        args += ["--allowedTools", *executor.allowed_tools]
    return args


def _execute_run(
    where: Layout, model: charter.Charter, slot: Slot, run: contracts.Run, launcher: proc.Launcher
) -> contracts.Execution:
    prompt = fsops.read_text(where.prompt_path(slot, run.run_id)).strip()
    args = command(model.executor, prompt, where.system_path(slot, run.run_id))
    launched = launcher(args, where.copy_dir(slot, run.run_id), model.executor.timeout_sec)
    fsops.write_text(where.stream_path(slot, run.run_id), launched.stdout)
    fsops.write_text(where.stderr_path(slot, run.run_id), launched.stderr)
    execution = contracts.Execution(run.run_id, launched.exit_code, launched.timed_out)
    fsops.write_json(where.exec_path(slot, run.run_id), contracts.to_data(execution))
    return execution


def execute(where: Layout, slot: Slot, launcher: proc.Launcher) -> str:
    """まだ実行していない実行役を、charter の executor.parallel の数だけ並行に起動する。止まっても続きから回せる。"""
    model, sha = workspace.approved_charter(where)
    plan = workspace.load_plan(where, slot)
    if plan.charter_sha256 != sha:
        raise StageError(
            f"charter が {slot.name} の準備の後に変わりました。作業領域を消して prepare からやり直してください"
        )
    pending = [run for run in plan.runs if not where.exec_path(slot, run.run_id).is_file()]
    for run in pending:
        if not where.copy_dir(slot, run.run_id).is_dir():
            raise StageError(
                f"{run.run_id} の評価用のコピーがありません（OS が消した可能性）。prepare からやり直してください"
            )
    results = proc.launch_many(
        pending, model.executor.parallel, lambda run: _execute_run(where, model, slot, run, launcher)
    )
    lines = [f"実行しました: {slot.name}（今回 {len(results)} 件、済み {len(plan.runs) - len(pending)} 件）"]
    for execution in results:
        if execution.timed_out:
            lines.append(f"WARN {execution.run_id} は {model.executor.timeout_sec} 秒で打ち切りました")
        elif execution.exit_code != 0:
            lines.append(
                f"WARN {execution.run_id} は終了コード {execution.exit_code} で終わりました（stderr.txt を見る）"
            )
    return "\n".join(lines)
