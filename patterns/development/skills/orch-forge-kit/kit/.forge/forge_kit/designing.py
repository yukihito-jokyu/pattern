"""対象スキルの設計を進める。設計役へのプロンプトを書き、設計役が書いた design.json を検査し、人の承認を記録する。"""

from __future__ import annotations

from forge_kit import charter, contracts, design, fsops, prompts, render, views, workspace
from forge_kit.errors import StageError
from forge_kit.layout import Layout


def _require_no_skill(where: Layout, model: charter.Charter) -> None:
    if workspace.has_skill(where, model):
        raise StageError(
            f"対象スキル {model.target.skill_name} は既にあります。/forge-run で評価と改善を進めてください"
        )


def design_new(where: Layout, feedback: str) -> str:
    """設計役のプロンプトを書く。feedback があれば、前の設計と承認を退けて、直してほしいことを渡す。"""
    model, _sha = workspace.approved_charter(where)
    _require_no_skill(where, model)
    approved = where.design_approval_path.is_file()
    if approved and not feedback:
        raise StageError("設計は承認済みです。直すなら --feedback に直してほしいことを書いてください")
    if feedback:
        for path in (where.design_md_path, where.design_approval_path, where.bundle_check_path):
            fsops.remove_tree(path)
    fsops.write_text(where.visible_charter_path, views.render_charter(model, "approved", include_holdout=False))
    values = {
        "skill_name": model.target.skill_name,
        "repo": str(where.root),
        "charter_md": str(where.visible_charter_path),
        "schema_md": str(where.design_schema_path),
        "rules_md": str(where.bundle_rules_path),
        "design": str(where.design_path),
        "feedback": feedback or render.MISSING,
    }
    fsops.write_text(where.designer_prompt_path, prompts.render("designer", values))
    return "\n".join(
        [
            f"設計役を準備しました: {model.target.skill_name}",
            render.job(contracts.AGENTS["designer"], "design", str(where.designer_prompt_path)),
        ]
    )


def design_check(where: Layout) -> str:
    model, _sha = workspace.approved_charter(where)
    data, found = workspace.load_design(where, model)
    state = workspace.design_state(where, data)
    fsops.write_text(where.design_md_path, views.render_design(found, state))
    counts = f"役 {len(found.roles)}、手順 {len(found.steps)}、人の関所 {len(found.checkpoints)}"
    return f"設計: 問題なし（{counts}）\n人が読む版: {where.design_md_path}"


def design_approve(where: Layout, today: str) -> str:
    model, _sha = workspace.approved_charter(where)
    if not where.design_md_path.is_file():
        raise StageError("設計がまだ検査されていません。先に design-check を実行してください")
    data, found = workspace.load_design(where, model)
    approval = contracts.DesignApproval(design.digest(data), today)
    fsops.write_json(where.design_approval_path, contracts.to_data(approval))
    fsops.write_text(where.design_md_path, views.render_design(found, "approved"))
    return f"設計の承認を記録しました（{today}）: {where.design_approval_path}"
