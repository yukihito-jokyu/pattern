"""検証の段（verify）。検査コマンドを補助 CLI が自分で実行し、結果を tree に結び付けて証拠にする（GATE-04）。"""

from __future__ import annotations

from autoflow_kit import changes, context, contracts, escalation, fsops, proc, profile, render, shape, trail, workspace
from autoflow_kit.layout import Layout
from autoflow_kit.profile import Command

TREE_CHECK = "tree-unchanged"


def _commands(ctx: context.Context) -> tuple[Command, ...]:
    """段の種類ごとの検査。check は、プロファイルの検査と、計画の受け入れ条件のコマンドと、再現のコマンド。"""
    mode = ctx.next.mode
    if mode == trail.BASELINE:
        return ctx.profile.verify.commands
    plan = workspace.load_plan(ctx.where, ctx.run_id, trail.count(ctx.events, trail.PLANNED))
    repro = (Command("repro", plan.repro, profile.DEFAULT_TIMEOUT_SEC),) if plan.repro else ()
    if mode == trail.REPRO:
        return repro
    criteria = tuple(
        Command(f"criterion-{item.id.lower()}", item.run, profile.DEFAULT_TIMEOUT_SEC)
        for item in plan.criteria
        if item.check == contracts.COMMAND
    )
    return (*ctx.profile.verify.commands, *criteria, *repro)


def _run(ctx: context.Context, seq: int, command: Command) -> contracts.CheckResult:
    result = proc.shell(command.run, ctx.where.root, command.timeout_sec)
    log = ctx.where.evidence_log_path(ctx.run_id, seq, command.id)
    fsops.write_text(log, f"$ {command.run}\n{result.output}")
    return contracts.CheckResult(command.id, command.run, result.exit_code, result.timed_out, ctx.where.relative(log))


def _tree_check(ctx: context.Context, seq: int) -> contracts.CheckResult | None:
    """検査コマンドが作業ツリーを変えたら、失敗の結果にする（.gitignore に無い生成物か、書き換える検査）。"""
    after = changes.snapshot(ctx.where.root)
    if after == ctx.tree:
        return None
    touched = changes.changed_files(ctx.where.root, ctx.tree, after)
    log = ctx.where.evidence_log_path(ctx.run_id, seq, TREE_CHECK)
    fsops.write_text(log, "検査コマンドが変えたファイル:\n" + "\n".join(touched) + "\n")
    return contracts.CheckResult(TREE_CHECK, "git write-tree", 1, False, ctx.where.relative(log))


def verify(where: Layout, run_id: str, now: str) -> str:
    ctx = context.begin(where, run_id, trail.VERIFY)
    seq, mode = ctx.next.number, ctx.next.mode
    results = [_run(ctx, seq, command) for command in _commands(ctx)]
    changed = _tree_check(ctx, seq)
    if mode == trail.REPRO:
        passed = bool(results) and all(item.exit_code != 0 for item in results)
    else:
        passed = all(item.exit_code == 0 for item in results)
    if changed is not None:
        results.append(changed)
        passed = False
    evidence = contracts.Evidence(seq, ctx.tree, mode, passed, tuple(results))
    fsops.write_json(where.evidence_path(run_id, seq), shape.to_data(evidence))
    event = trail.verified(seq, mode, passed, ctx.tree, now)
    fsops.append_line(where.trail_path(run_id), trail.encode(event))
    stuck = (
        ()
        if mode == trail.BASELINE
        else escalation.record(where, run_id, (*ctx.events, event), ctx.profile.limits, now)
    )
    rows = [[item.id, f"`{item.run}`", render.number(item.exit_code), item.log] for item in results]
    lines = [
        f"証拠 {seq}（{mode}、tree {ctx.tree[:12]}）: {'期待どおり' if passed else '期待と違う'}",
        render.table(["検査", "コマンド", "終了コード", "ログ"], rows),
        f"記録: {where.relative(where.evidence_path(run_id, seq))}",
    ]
    lines += [f"H2 に当たった条件: {rule}" for rule in stuck]
    return "\n".join(lines)
