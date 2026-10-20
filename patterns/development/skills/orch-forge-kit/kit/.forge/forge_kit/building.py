"""承認した設計から下書きのバンドルを作り、構築役へのプロンプトを書き、下書きを検査して、対象のリポジトリへ入れる。"""

from __future__ import annotations

from forge_kit import bundle, charter, contracts, design, fsops, layout, prompts, render, views, workspace
from forge_kit.errors import InvalidFileError, StageError
from forge_kit.layout import Layout


def _require_no_skill(where: Layout, model: charter.Charter) -> None:
    if workspace.has_skill(where, model):
        raise StageError(
            f"対象スキル {model.target.skill_name} は既にあります。/forge-run で評価と改善を進めてください"
        )


def _actor(skill_name: str, step: design.Step) -> str:
    return "" if step.actor == design.ORCHESTRATOR else f"`{skill_name}-{step.actor}` に任せる: "


def _skeleton(where: Layout, found: design.Design) -> None:
    """設計から骨組みを書く。構築役は骨組みの TODO(forge) を埋める（形を設計とそろえるため）。"""
    name = found.skill_name
    roles = render.table(
        ["役", "サブエージェント", "受け持つこと"],
        [[role.role, f"{name}-{role.role}", role.purpose] for role in found.roles],
    )
    steps = "\n".join(
        f"{number}. {_actor(name, step)}{step.action}{'（並行）' if step.parallel else ''}"
        for number, step in enumerate(found.steps, 1)
    )
    gates = [f"{c.step}: {c.question} {bundle.DEFAULT_MARK} {c.default}" for c in found.checkpoints]
    values = {
        "skill_name": name,
        "summary": found.summary,
        "roles": roles,
        "steps": steps,
        "checkpoints": render.bullets(gates),
        "report": render.bullets(list(found.report)),
    }
    fsops.write_text(bundle.skill_dir(where.draft_dir, name) / layout.SKILL_FILE, prompts.render("draft-skill", values))
    for role in found.roles:
        agent = f"{name}-{role.role}"
        agent_values = {
            "agent_name": agent,
            "purpose": role.purpose,
            "tools": ", ".join(role.tools),
            "input": role.input,
            "output": role.output,
        }
        path = where.draft_dir / layout.AGENTS_DIR / layout.agent_file(agent)
        fsops.write_text(path, prompts.render("draft-agent", agent_values))


def build(where: Layout, feedback: str) -> str:
    """下書きの骨組み（無ければ）と構築役のプロンプトを書く。前の検査の結果は消す（下書きが変わるため）。"""
    model, _sha = workspace.approved_charter(where)
    _require_no_skill(where, model)
    found, _design_sha = workspace.approved_design(where, model)
    if not bundle.has_bundle(where.draft_dir, model.target.skill_name):
        _skeleton(where, found)
    for path in (where.bundle_check_path, where.bundle_check_md_path):
        fsops.remove_tree(path)
    fsops.write_text(where.visible_charter_path, views.render_charter(model, "approved", include_holdout=False))
    values = {
        "skill_name": model.target.skill_name,
        "repo": str(where.root),
        "charter_md": str(where.visible_charter_path),
        "design_md": str(where.design_md_path),
        "rules_md": str(where.bundle_rules_path),
        "draft_dir": str(where.draft_dir),
        "feedback": feedback or render.MISSING,
    }
    fsops.write_text(where.builder_prompt_path, prompts.render("builder", values))
    return "\n".join(
        [
            f"構築役を準備しました: {where.draft_dir}",
            render.job(contracts.AGENTS["builder"], "build", str(where.builder_prompt_path)),
        ]
    )


def bundle_check(where: Layout) -> str:
    """下書きをバンドルの決まりと設計に照らして検査する。通れば、下書きと設計のハッシュを記録する。"""
    model, _sha = workspace.approved_charter(where)
    found, design_sha = workspace.approved_design(where, model)
    name = model.target.skill_name
    fragments = charter.fragments(model, bundle.LEAK_MIN_CHARS)
    problems = bundle.check(where.draft_dir, name, roles=design.roles_tools(found), fragments=fragments)
    if problems:
        problems.append("構築役に、この問題を直すよう添えて、同じプロンプトでもう一度起動してください")
        raise InvalidFileError(str(where.draft_dir), problems)
    check = contracts.BundleCheck(bundle.digest(where.draft_dir, name), design_sha)
    fsops.write_json(where.bundle_check_path, contracts.to_data(check))
    fsops.write_text(where.bundle_check_md_path, render_bundle(where, found))
    return f"下書き: 問題なし（{where.draft_dir}）\n人が読む版: {where.bundle_check_md_path}"


def render_bundle(where: Layout, found: design.Design) -> str:
    name = found.skill_name
    files = bundle.files(where.draft_dir, name)
    rows = [[f"{name}-{role.role}", ", ".join(role.tools), role.purpose] for role in found.roles]
    parts = [
        f"# {name} の下書き",
        "",
        f"- 置き場: `{where.draft_dir}`",
        f"- 入れる先: `{where.claude_dir}`（install で写す）",
        "",
        "## ファイル",
        "",
        render.bullets([f"`{relative}`" for relative in files]),
        "",
        "## サブエージェント",
        "",
        render.table(["名前", "道具", "受け持つこと"], rows),
        "",
        "## 手順",
        "",
        render.bullets(
            list(bundle.steps(fsops.read_text(bundle.skill_dir(where.draft_dir, name) / layout.SKILL_FILE)))
        ),
    ]
    return "\n".join(parts) + "\n"


def install(where: Layout, today: str) -> str:
    """検査を通った下書きを、対象のリポジトリの .claude/ に写す。検査の後に下書きか設計が変わっていれば止める。"""
    model, _sha = workspace.approved_charter(where)
    _require_no_skill(where, model)
    _found, design_sha = workspace.approved_design(where, model)
    name = model.target.skill_name
    check = workspace.load_bundle_check(where)
    if check is None:
        raise StageError("下書きがまだ検査されていません。先に bundle-check を実行してください")
    if check.draft_sha256 != bundle.digest(where.draft_dir, name) or check.design_sha256 != design_sha:
        raise StageError("検査の後に下書きか設計が変わりました。bundle-check をやり直し、人に見せ直してください")
    bundle.place(where, name, where.draft_dir)
    installation = contracts.Installation(name, design_sha, bundle.files(where.claude_dir, name), today)
    fsops.write_json(where.install_path, contracts.to_data(installation))
    return f"入れました: {where.claude_dir}（{len(installation.files)} ファイル）"
