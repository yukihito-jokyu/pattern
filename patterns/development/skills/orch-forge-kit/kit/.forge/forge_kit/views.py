"""charter と設計と見積もりを、人とサブエージェントが読む形にする。goals・designing・building・analyze が使う。"""

from __future__ import annotations

from dataclasses import dataclass

from forge_kit import charter, design, render


@dataclass(frozen=True)
class Estimate:
    """評価で起動する実行役の回数と、費用の上限（各回の max_budget_usd の合計）。"""

    runs_per_slot: int
    final_runs: int
    total_runs: int
    max_cost_usd: float


def estimate(model: charter.Charter) -> Estimate:
    per_slot = len(charter.visible_tasks(model)) * model.budget.agents
    final = len(model.tasks) * model.budget.agents
    total = per_slot * (1 + model.budget.max_rounds) + final
    return Estimate(per_slot, final, total, total * model.executor.max_budget_usd)


STATE_NAMES = {
    "approved": "承認済み",
    "unapproved": "未承認（人の確認の後に承認を記録する）",
    "stale": "承認の後に変更された（人に変更点を見せ、もう一度承認を得る）",
}


def render_charter(model: charter.Charter, state: str, *, include_holdout: bool) -> str:
    """人とサブエージェントが読む charter。サブエージェントに渡すときは include_holdout=False にする。"""
    parts = [
        f"# {model.target.id} の charter",
        "",
        f"- 対象スキル: `{model.target.skill_name}`",
        f"- 承認: {STATE_NAMES[state]}",
        "",
        "## 目的",
        "",
        model.purpose,
        "",
        "## ゴール",
        "",
        render.table(["id", "ゴール", "測る指標"], [[g.id, g.statement, ", ".join(g.metrics)] for g in model.goals]),
        "",
        "## 指標",
        "",
        _metrics_table(model),
        "",
        "## 評価課題",
        "",
        "\n\n".join(_task_block(task) for task in charter.slot_tasks(model, include_holdout=include_holdout)),
        "",
        "## 環境",
        "",
        _environment_text(model),
        "",
        "## 実行の条件と予算",
        "",
        _executor_text(model),
    ]
    return "\n".join(parts) + "\n"


def _metrics_table(model: charter.Charter) -> str:
    rows = []
    for choice in model.metrics:
        metric = charter.definition(choice)
        rows.append(
            [
                choice.id,
                metric.name,
                metric.method,
                ("≥ " if metric.direction == "higher" else "≤ ") + render.number(choice.threshold),
                choice.priority,
                metric.tells,
            ]
        )
    return render.table(["id", "名前", "測り方", "閾値", "優先度", "分かること・条件"], rows)


def _task_block(task: charter.Task) -> str:
    role = "ホールドアウト（最後の評価だけで使う）" if charter.is_holdout(task.id) else "評価と改善に使う"
    return f"### {task.id}（{role}）\n\n{task.prompt}\n\n受け入れ条件:\n\n{render.bullets(task.acceptance)}"


def _environment_text(model: charter.Charter) -> str:
    env = model.environment
    lines = [
        f"- 検査コマンド: `{env.check_command}`（{env.check_timeout_sec} 秒で打ち切り）"
        if env.check_command
        else "- 検査コマンド: なし",
        f"- 保護パス: {', '.join(f'`{p}`' for p in env.protected_paths) or 'なし'}",
        f"- コピーで除くもの: {', '.join(env.skip_dirs) or '既定のみ'}",
        f"- コピーせずリンクにするもの: {', '.join(env.link_dirs) or '既定のみ'}",
    ]
    return "\n".join(lines)


def _executor_text(model: charter.Charter) -> str:
    executor = model.executor
    cost = estimate(model)
    lines = [
        f"- モデル: {executor.model or 'Claude Code の既定'}",
        f"- 確認なしで許すツール: {', '.join(f'`{t}`' for t in executor.allowed_tools) or 'なし（編集だけ許す）'}",
        f"- 1回の実行の上限: {render.usd(executor.max_budget_usd)}、{executor.timeout_sec} 秒",
        f"- 同時に動かす実行役: {executor.parallel}",
        f"- 1課題あたりの実行役: {model.budget.agents} 人、改善のラウンドの上限: {model.budget.max_rounds}",
        f"- 実行役の起動（上限）: {cost.total_runs} 回"
        f"（1回の評価 {cost.runs_per_slot} 回、最後の評価 {cost.final_runs} 回）",
        f"- 費用の上限の見積もり: {render.usd(cost.max_cost_usd)}（各回の上限の合計。サブエージェントの費用を含む）",
    ]
    return "\n".join(lines)


def render_design(model: design.Design, state: str) -> str:
    """人が承認する設計。役、手順、人の関所、報告の形を表にする。"""
    roles = render.table(
        ["役", "サブエージェント", "受け持つこと", "道具", "受け取るもの", "返すもの"],
        [
            [r.role, f"{model.skill_name}-{r.role}", r.purpose, ", ".join(r.tools), r.input, r.output]
            for r in model.roles
        ],
    )
    steps = render.table(
        ["id", "担い手", "すること", "並行"],
        [[s.id, s.actor, s.action, "する" if s.parallel else "しない"] for s in model.steps],
    )
    gates = [f"{c.step}: {c.question}（人が答えられないときの既定: {c.default}）" for c in model.checkpoints]
    parts = [
        f"# {model.skill_name} の設計",
        "",
        f"- 承認: {STATE_NAMES[state]}",
        f"- 要約: {model.summary}",
        "",
        "## 役",
        "",
        roles,
        "",
        "## 手順",
        "",
        steps,
        "",
        "## 人に確かめること",
        "",
        render.bullets(gates),
        "",
        "## 報告に書くこと",
        "",
        render.bullets(list(model.report)),
    ]
    return "\n".join(parts) + "\n"
