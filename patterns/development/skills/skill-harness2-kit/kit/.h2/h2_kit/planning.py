"""init・check・approve の段。プロファイルとタスクを検証し、予算と順番を plan.md に書き、人の承認を記録する。"""

from __future__ import annotations

from dataclasses import dataclass

from h2_kit import fsops, guards, layout, ledger, profile, render, skilltree, validate, workspace
from h2_kit.errors import StageError

# check の結果が変わらない限り、同じ予算の数え方を使う。差し戻しで編集のセッションは最大2回動く
SESSION_ATTEMPTS = 2


@dataclass(frozen=True)
class Plan:
    """check が組み立てる計画。problems が空なら approve できる。"""

    model: profile.Profile
    tree: skilltree.SkillTree
    order: tuple[str, ...]
    checks: tuple[tuple[str, int], ...]
    problems: tuple[str, ...]
    notes: tuple[str, ...]


def init(where: layout.Layout, skill: str) -> str:
    """profile.json のひな形と tasks/ を作る。既にあれば何もしない。"""
    if where.profile_path.is_file():
        raise StageError(f"{where.profile_path} は既にあります。作り直すなら消してから init を実行してください")
    path, problems = profile.parse_skill_path(skill)
    if problems:
        raise StageError("、".join(problems))
    if not (where.skill_dir(path) / layout.SKILL_FILE).is_file():
        raise StageError(
            f"{where.skill_dir(path)} に {layout.SKILL_FILE} がありません。--skill に対象スキルを渡してください"
        )
    fsops.write_json(where.profile_path, profile.build_default_profile(path))
    fsops.write_dir(where.tasks_dir)
    lines = [
        f"{where.profile_path} と {where.tasks_dir}/ を作りました",
        "次: references/profile-guide.md に沿って profile.json を書き、"
        "references/task-guide.md に沿って tasks/<id>/task.md と tasks/<id>/workspace/ を作り、check を実行する",
    ]
    return "\n".join(lines)


def check(where: layout.Layout) -> str:
    """検証し、問題が無ければ plan.md を書いて中身を返す。問題があれば StageError で全部を返す。"""
    plan = _build_plan(where)
    if plan.problems:
        raise StageError("check で問題が見つかりました:\n" + render.render_bullets(plan.problems))
    text = _render_plan(where, plan)
    fsops.write_text(where.plan_path, text)
    return text + "\n次: plan.md を人に見せ、承認を得てから approve を実行する"


def approve(where: layout.Layout, today: str) -> str:
    """承認を記録する。ラウンドを1つ進め、承認時のスキルの木（H0）を runs/r<N>/base-skill/ に残す。"""
    plan = _build_plan(where)
    if plan.problems:
        raise StageError(
            "check で問題が見つかります。直して check を見せ直してください:\n" + render.render_bullets(plan.problems)
        )
    if not where.plan_path.is_file() or fsops.read_text(where.plan_path) != _render_plan(where, plan):
        raise StageError(
            "plan.md が今の profile.json と tasks/ と合いません。check を実行して plan.md を見せ直してください"
        )
    previous = workspace.load_approval(where)
    number = previous.round + 1 if previous is not None else 1
    skilltree.write_tree(plan.tree, where.base_skill_dir(number))
    approval = workspace.Approval(
        round=number,
        profile_sha256=workspace.compute_profile_sha256(where),
        tasks_sha256=workspace.compute_tasks_sha256(where),
        skill_fingerprint=skilltree.compute_fingerprint(plan.tree),
        task_order=plan.order,
        approved_on=today,
    )
    fsops.write_json(where.approval_path, workspace.build_json(approval))
    lines = [
        f"ラウンド {number} を承認しました",
        "次: run を実行する（時間がかかるので、バックグラウンドで動かし status で進みを見る）",
    ]
    return "\n".join(lines)


def _render_plan(where: layout.Layout, plan: Plan) -> str:
    model = plan.model
    budget = ledger.compute_budget(model.k, len(model.modes), model.k > 1)
    tasks = len(plan.order)
    rollouts = budget.rollouts * tasks
    sessions = budget.sessions * tasks * SESSION_ATTEMPTS + budget.side_sessions * tasks
    limit = rollouts * model.rollout.max_budget_usd + sessions * model.improver.max_budget_usd
    fingerprint = skilltree.compute_fingerprint(plan.tree)
    parts = [
        f"# 改善の計画（{where.target}）",
        render.render_bullets(
            [
                f"対象スキル: `{model.skill}`（指紋 {skilltree.build_confirm_code(fingerprint)}）",
                f"k: {model.k}、モード: {'、'.join(model.modes)}、並行の幅: {model.width}",
                f"タスクの順: {'種 ' + str(model.seed) + ' でシャッフル' if model.seed is not None else '名前の順'}",
            ]
        ),
        "## タスク",
        render.render_table(
            ["順", "タスク", "事後の検査"], [[str(i), t, f"{n} 件"] for i, (t, n) in enumerate(plan.checks, 1)]
        ),
        "## 1タスクあたりの回数",
        render.render_table(
            ["種類", "回数", "内訳"],
            [
                [
                    "実行",
                    str(budget.rollouts),
                    f"基準 {model.k}（モードで共有）＋ モードごとに候補 {2 * model.k} と完成品 {model.k}",
                ],
                [
                    "編集のセッション",
                    str(budget.sessions),
                    f"モードごとに P = 3k = {3 * model.k}（差し戻しで最大 {SESSION_ATTEMPTS} 倍）",
                ],
                ["選択・振り返り", str(budget.side_sessions), "モードごとに振り返り1回と、k が2以上なら選択1回"],
            ],
        ),
        "## 費用の上限",
        render.render_table(
            ["種類", "最大の回数", "1回の上限", "上限の合計"],
            [
                [
                    "実行",
                    str(rollouts),
                    render.render_usd(model.rollout.max_budget_usd),
                    render.render_usd(rollouts * model.rollout.max_budget_usd),
                ],
                [
                    "セッション",
                    str(sessions),
                    render.render_usd(model.improver.max_budget_usd),
                    render.render_usd(sessions * model.improver.max_budget_usd),
                ],
                ["合計", "", "", render.render_usd(limit)],
            ],
        ),
        "## 注意",
        render.render_bullets(list(plan.notes) or ["なし"]),
    ]
    return render.render_sections(parts)


def _build_plan(where: layout.Layout) -> Plan:
    model = workspace.load_profile(where)
    tree, outside = workspace.load_skill(where, model)
    problems = [
        f"対象スキルの {path} は編集面の外にあるか、UTF-8 で読めません（採用で消えるため扱えません）"
        for path in outside
    ]
    notes = validate.check_tree(tree, skilltree.build_tree({}), [])
    tasks = workspace.load_tasks(where)
    if not tasks:
        problems.append(f"{where.tasks_dir} にタスクがありません（tasks/<id>/task.md を作ってください）")
    checks: dict[str, int] = {}
    for task in tasks:
        problems += guards.check_text_markers(f"{task.task_id}/{layout.TASK_FILE}", task.prompt)
        material = task.directory / layout.TASK_WORKSPACE_DIR
        problems += [
            f"{task.task_id}/{layout.TASK_WORKSPACE_DIR}: {problem}"
            for problem in guards.check_directory(material, model.leak_globs)
        ]
        checks[task.task_id] = len(workspace.load_checks(where.checks_path(task.task_id)))
    order = workspace.compute_task_order([task.task_id for task in tasks], model.seed, where.target)
    return Plan(
        model, tree, tuple(order), tuple((task_id, checks[task_id]) for task_id in order), tuple(problems), tuple(notes)
    )
