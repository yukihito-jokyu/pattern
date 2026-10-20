"""人と決めるゴール・指標・評価課題（charter）を作り、検査し、承認を記録する（forge-goals スキルが使う）。"""

from __future__ import annotations

from pathlib import Path

from forge_kit import catalog, charter, fsops, layout, render, views, workspace
from forge_kit.errors import KitError
from forge_kit.layout import Layout

DESCRIPTION_CHARS = 80


def targets(root: Path) -> str:
    """リポジトリのスキル（この道具の forge-* を除く）と、作業領域にある対象の一覧。"""
    skills_dir = root / layout.CLAUDE_DIR / layout.SKILLS_DIR
    rows = []
    for skill_md in sorted(skills_dir.glob(f"*/{layout.SKILL_FILE}")) if skills_dir.is_dir() else []:
        name = skill_md.parent.name
        if not name.startswith(layout.KIT_PREFIX):
            description = _description(fsops.read_text(skill_md))
            rows.append([name, description[:DESCRIPTION_CHARS]])
    known = sorted(
        path.parent.name for path in (root / layout.KIT_DIR / layout.TARGETS_DIR).glob(f"*/{layout.CHARTER_FILE}")
    )
    parts = [
        "## リポジトリのスキル",
        "",
        render.table(["スキル名", "description（先頭）"], rows) if rows else "なし",
        "",
        "## 作業領域の対象（target-id）",
        "",
        render.bullets(known),
    ]
    return "\n".join(parts)


def _description(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def metric_catalog() -> str:
    rows = [
        [
            metric.id,
            metric.name,
            metric.method,
            "高いほど良い" if metric.direction == "higher" else "低いほど良い",
            render.number(metric.default_threshold),
            "推奨" if metric.recommended else "",
            metric.tells,
            metric.requires,
        ]
        for metric in catalog.METRICS
    ]
    headers = ["id", "名前", "測り方", "向き", "既定の閾値", "推奨", "分かること", "前提"]
    custom = "表に無い観点は custom_<番号> の独自の指標にし、採点役が判定できる1文（criterion）で書く。"
    return f"{render.table(headers, rows)}\n\n{custom}"


def charter_new(where: Layout, skill_name: str) -> str:
    if where.charter_path.exists():
        raise KitError(f"{where.charter_path} は既にあります。charter-check で中身を確かめてください")
    fsops.write_json(where.charter_path, charter.skeleton(where.target, skill_name))
    exists = where.skill_md_path(skill_name).is_file()
    route = "既にあるスキルを評価して直す（forge-run）" if exists else "まだ無いスキルを作る（forge-build）"
    return f"作成: {where.charter_path}\n対象スキル: {skill_name}（{route}）"


def charter_check(where: Layout) -> str:
    data, model = workspace.load_charter(where)
    state = charter.approval_state(data, model)
    fsops.write_text(where.charter_md_path, views.render_charter(model, state, include_holdout=True))
    cost = views.estimate(model)
    lines = [
        f"charter: 問題なし（{where.charter_path}）",
        f"人が読む版: {where.charter_md_path}",
        f"承認: {views.STATE_NAMES[state]}",
        f"実行役の起動（上限）: {cost.total_runs} 回、費用の上限の見積もり: {render.usd(cost.max_cost_usd)}",
    ]
    if not any(charter.is_holdout(task.id) for task in model.tasks):
        lines.append("WARN ホールドアウト（H<番号>）の課題がありません。評価課題への過剰適合を確かめられません")
    return "\n".join(lines)


def charter_approve(where: Layout, today: str) -> str:
    data, _model = workspace.load_charter(where)
    approved = dict(data)
    approved["approval"] = {"sha256": charter.digest(data), "approved_on": today}
    model = charter.parse(approved, str(where.charter_path))
    fsops.write_json(where.charter_path, approved)
    fsops.write_text(where.charter_md_path, views.render_charter(model, "approved", include_holdout=True))
    return f"承認を記録しました（{today}）: {where.charter_path}"
