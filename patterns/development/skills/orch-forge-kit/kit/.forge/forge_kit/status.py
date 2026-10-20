"""作業領域のファイルから今の段階を求め、次に実行するコマンドか、起動するサブエージェントか、人に聞くことを示す。"""

from __future__ import annotations

from forge_kit import bundle, charter, contracts, render, workspace
from forge_kit.errors import InvalidFileError
from forge_kit.layout import Layout

CLI = "python3 .forge/forge.py"
GOALS = "（forge-goals）"
BUILD = "（forge-build）"
RUN = "（forge-run）"
# status の行の書き出し。スキルはこの書き出しで行を読み分けるので、新しい種類を足さない（OPS-01）
LINE_KINDS = (
    "対象:",
    "段階:",
    "改善のラウンド:",
    "次:",
    "その後:",
    "問題が出たら:",
    "承認なら:",
    "直すなら:",
    "採用なら:",
    "不採用なら:",
    "job ",
)
LAUNCH = "次: 下の job をすべて Agent ツールで1つのメッセージにまとめて起動し、全員の完了を待つ"


def _command(name: str, where: Layout, extra: str = "") -> str:
    return f"{CLI} {name} --target {where.target}{extra}"


def _build_steps(where: Layout, progress: workspace.BuildProgress) -> list[str]:
    if not progress.designer_prompted:
        return [f"段階: 設計の準備{BUILD}", f"次: {_command('design-new', where)}"]
    if not progress.designed:
        return [
            f"段階: 設計役の作業{BUILD}",
            LAUNCH,
            render.job(contracts.AGENTS["designer"], "design", str(where.designer_prompt_path)),
            f"その後: {_command('design-check', where)}",
        ]
    if not progress.design_checked:
        return [
            f"段階: 設計の検査{BUILD}",
            f"次: {_command('design-check', where)}",
            "問題が出たら: 問題の一覧を添えて設計役をもう一度起動し、終わったら design-check をやり直す",
        ]
    if progress.design_state != "approved":
        return [
            f"段階: 設計の確認（人が決める）{BUILD}",
            f"次: {where.design_md_path} を人に見せ、承認するかを聞く",
            f"承認なら: {_command('design-approve', where)}",
            "直すなら: " + _command("design-new", where, " --feedback '<直してほしいこと>'"),
        ]
    return _draft_steps(where, progress)


def _draft_steps(where: Layout, progress: workspace.BuildProgress) -> list[str]:
    if not progress.builder_prompted:
        return [f"段階: 構築の準備{BUILD}", f"次: {_command('build', where)}"]
    if not progress.bundle_checked:
        return [
            f"段階: 構築役の作業{BUILD}",
            LAUNCH,
            render.job(contracts.AGENTS["builder"], "build", str(where.builder_prompt_path)),
            f"その後: {_command('bundle-check', where)}",
            "問題が出たら: 問題の一覧を添えて構築役をもう一度起動し、終わったら bundle-check をやり直す",
        ]
    return [
        f"段階: 下書きの確認（人が決める）{BUILD}",
        f"次: {where.bundle_check_md_path} と {where.draft_dir} の下書きを人に見せ、入れるかを聞く",
        f"承認なら: {_command('install', where)}",
        "直すなら: " + _command("build", where, " --feedback '<直してほしいこと>'"),
    ]


def _slot_args(slot: workspace.SlotProgress) -> str:
    if slot.slot.variant == "final":
        return " --variant final"
    return f" --variant {slot.slot.variant} --round {slot.slot.round_no}"


def _slot_steps(where: Layout, slot: workspace.SlotProgress, label: str) -> list[str]:
    """1回の評価の次の手。評価が採点まで終わっていれば空。"""
    args = _slot_args(slot)
    if not slot.planned:
        return [f"段階: {label}の準備{RUN}", f"次: {_command('prepare', where, args)}"]
    if slot.pending_runs:
        return [
            f"段階: {label}の実行（未実行 {len(slot.pending_runs)} 件）{RUN}",
            f"次: {_command('execute', where, args)}",
            f"その後: {_command('collect', where, args)}",
        ]
    if not slot.collected:
        return [f"段階: {label}の集計の準備{RUN}", f"次: {_command('collect', where, args)}"]
    if slot.pending_grades:
        jobs = [
            render.job(contracts.AGENTS["grader"], run.run_id, str(where.grader_prompt_path(slot.slot, run.run_id)))
            for run in slot.pending_grades
        ]
        return [
            f"段階: {label}の採点（採点が無い実行 {len(jobs)} 件）{RUN}",
            LAUNCH,
            *jobs,
            f"その後: {_command('score', where, args)}",
        ]
    if not slot.scored:
        return [f"段階: {label}の集計{RUN}", f"次: {_command('score', where, args)}"]
    return []


def _round_steps(where: Layout, item: workspace.RoundProgress) -> list[str]:
    number = item.round_no
    label = f"{number} 回目の改善"
    round_arg = f" --round {number}"
    if not item.proposed:
        return [
            f"段階: {label}の分析{RUN}",
            LAUNCH,
            render.job(contracts.AGENTS["analyst"], f"round-{number}", str(where.analyst_prompt_path(number))),
            f"その後: {_command('propose', where, round_arg)}",
        ]
    if not item.checked:
        return [
            f"段階: {label}の提案の検査{RUN}",
            f"次: {_command('propose', where, round_arg)}",
            "問題が出たら: 問題の一覧を添えて分析役をもう一度起動し、終わったら propose をやり直す",
        ]
    if not item.has_changes:
        return [
            f"段階: {label}（バンドルの変更が無い提案）{RUN}",
            f"次: {where.proposal_md_path(number)} の所見を人に見せる",
            f"その後: {_command('decide', where, round_arg + ' --reject')}",
        ]
    steps = _slot_steps(where, item.candidate, f"{label}の候補の評価")
    if steps:
        return steps
    if not item.compared:
        return [f"段階: {label}の比較{RUN}", f"次: {_command('compare', where, round_arg)}"]
    return [
        f"段階: {label}の採否（人が決める）{RUN}",
        f"次: {where.compare_md_path(number)} と {where.proposal_md_path(number)} を人に見せ、採用するかを聞く",
        f"採用なら: {_command('decide', where, round_arg + ' --adopt')}",
        f"不採用なら: {_command('decide', where, round_arg + ' --reject')}",
    ]


def _run_steps(where: Layout, model: charter.Charter, progress: workspace.Progress) -> list[str]:
    steps = _slot_steps(where, progress.baseline, "最初の評価")
    if steps:
        return steps
    open_round = next((item for item in progress.rounds if item.decision is None), None)
    if open_round is not None:
        return _round_steps(where, open_round)
    current = workspace.load_scores(where, progress.current_slot)
    if not current.all_must_met and progress.decided_rounds < model.budget.max_rounds:
        number = progress.decided_rounds + 1
        return [f"段階: {number} 回目の改善の準備{RUN}", f"次: {_command('analyze', where, f' --round {number}')}"]
    steps = _slot_steps(where, progress.final, "最後の評価（ホールドアウトを含む）")
    if steps:
        return steps
    if not progress.reported:
        return [f"段階: 報告{RUN}", f"次: {_command('report', where)}"]
    return [f"段階: 完了{RUN}", f"次: {where.report_path} を人に見せる"]


def _evaluation(where: Layout, model: charter.Charter) -> list[str]:
    problems = bundle.check(where.claude_dir, model.target.skill_name)
    if problems:
        return [
            f"段階: 対象スキルがバンドルの決まりを満たしていない{RUN}",
            *[f"  - {problem}" for problem in problems],
            f"次: 問題を人に見せ、{where.bundle_rules_path} に沿って直すかを相談する",
        ]
    progress = workspace.progress(where, model)
    rounds = f"改善のラウンド: {progress.decided_rounds} / {model.budget.max_rounds} 回が決定済み"
    return [rounds, *_run_steps(where, model, progress)]


def status(where: Layout) -> str:
    if not where.charter_path.is_file():
        return "\n".join([f"段階: charter が無い{GOALS}", "次: /forge-goals で、人とゴール・指標・評価課題を決める"])
    try:
        data, model = workspace.load_charter(where)
    except InvalidFileError as exc:
        return "\n".join([f"段階: charter に問題がある{GOALS}", exc.message, "次: /forge-goals で直す"])
    header = f"対象: {model.target.id}（スキル {model.target.skill_name}）"
    state = charter.approval_state(data, model)
    if state != "approved":
        reason = "未承認" if state == "unapproved" else "承認の後に変更された"
        return "\n".join([header, f"段階: charter が{reason}{GOALS}", "次: /forge-goals で人に確かめ、承認を記録する"])
    if not workspace.has_skill(where, model):
        return "\n".join([header, *_build_steps(where, workspace.build_progress(where, model))])
    return "\n".join([header, *_evaluation(where, model)])
