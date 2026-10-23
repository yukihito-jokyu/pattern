"""計画のひな形を作り（init）、計画を検査して分割と plan.md を書き（check-plan）、人の承認を記録する（approve）。"""

from __future__ import annotations

from tune_kit import checks, contracts, fsops, layout, plan, render, workspace
from tune_kit.errors import KitError, StageError


def init(where: layout.Layout, skill_path: str) -> str:
    if where.plan_path.exists() or where.cases_path.exists():
        raise KitError(
            f"{where.display(where.target_dir)} には既に計画があります。"
            "別の target の ID を使うか、計画を直してください"
        )
    if not (where.skill_dir(skill_path) / layout.SKILL_FILE).is_file():
        raise KitError(f"{skill_path} に {layout.SKILL_FILE} がありません。対象スキルのディレクトリを指定してください")
    fsops.write_json(where.plan_path, plan.build_skeleton(where.target, skill_path))
    fsops.write_json(where.cases_path, {"cases": []})
    fsops.write_dir(where.files_dir)
    return "\n".join(
        [
            f"作成: {where.display(where.plan_path)}（goal、mode、checks を人と決めて埋める）",
            f"作成: {where.display(where.cases_path)}（ケースを足す）",
            f"作成: {where.display(where.files_dir)}/"
            "（ケースの入力ファイルは <ケース>/input/、正解のファイルは <ケース>/expected/）",
        ]
    )


def _render_split_rows(approved_cases: tuple[plan.Case, ...], splits: dict[str, str]) -> list[list[str]]:
    rows = []
    for name in plan.SPLITS:
        members = [case for case in approved_cases if splits[case.id] == name]
        groups = sorted({case.group for case in members})
        counts = "、".join(f"{group} {sum(1 for case in members if case.group == group)}" for group in groups)
        rows.append([name, str(len(members)), counts, ", ".join(case.id for case in members)])
    return rows


def _list_split_gaps(approved_cases: tuple[plan.Case, ...], splits: dict[str, str]) -> list[str]:
    """検証用かテスト用に1件も無いグループの警告。そのグループの改善を、その分割で測れないため。"""
    warnings = []
    for group in sorted({case.group for case in approved_cases}):
        present = {splits[case.id] for case in approved_cases if case.group == group}
        missing = "、".join(name for name in (plan.VAL, plan.TEST) if name not in present)
        if missing:
            warnings.append(
                f"グループ {group} のケースが {missing} に1件もありません。"
                f"このグループの改善は {missing} で測れないので、ケースを足すか、cases.json の split で割り当てる"
            )
    return warnings


def _render_checks(model: plan.Plan) -> str:
    rows = []
    for check in model.checks:
        kind = checks.KINDS[check.kind]
        body = check.criterion or check.value or check.pattern or check.run or check.expected_file or check.target
        groups = ", ".join(check.groups) or "全部"
        rows.append([check.id, check.kind, check.severity, groups, body, "採点役" if kind.judge else "機械"])
    return render.render_table(["ID", "種類", "重さ", "当てるグループ", "内容", "判定"], rows)


def _compute_estimate(model: plan.Plan, splits: dict[str, str]) -> list[list[str]]:
    """サブエージェントの起動回数の見積もり（上限）。"""
    count = {name: sum(1 for value in splits.values() if value == name) for name in plan.SPLITS}
    runs = model.budget.runs_per_case
    judged = 2 if any(checks.KINDS[check.kind].judge for check in model.checks) else 1
    loop = (count[plan.TRAIN] + count[plan.VAL]) * runs * judged
    rows = [
        ["最初の評価（v0 の学習用・検証用）", str(loop)],
        [
            f"1ラウンド（監査1、学習1、候補の評価） × 最大 {model.budget.max_rounds}",
            str((loop + 2) * model.budget.max_rounds),
        ],
        ["最後の評価（v0 と最良の版のテスト用、監査1）", str(count[plan.TEST] * runs * judged * 2 + 1)],
    ]
    total = sum(int(row[1]) for row in rows)
    return [*rows, ["合計（データの直しによる評価のやり直しを除く）", str(total)]]


def _render_plan_md(dataset: workspace.Dataset, splits: dict[str, str]) -> str:
    model = dataset.model
    warnings = []
    if len(dataset.cases) < plan.RECOMMENDED_CASES:
        warnings.append(
            f"ケースが {len(dataset.cases)} 件です。検証用・テスト用の結果が1件の差で大きく動くため、"
            f"{plan.RECOMMENDED_CASES} 件以上を勧める"
        )
    warnings += _list_split_gaps(dataset.cases, splits)
    sections = [
        f"# 計画: {model.target.id}",
        "",
        render.render_table(
            ["項目", "値"],
            [
                ["対象スキル", model.target.skill_path],
                ["ゴール", model.goal],
                [
                    "モード",
                    f"{model.mode}（{'正解データで測る' if model.mode == plan.REFERENCE else '評価項目で測る'}）",
                ],
                ["sandbox", model.sandbox],
                ["ケースの数", str(len(dataset.cases))],
                ["1ケースを解く回数", str(model.budget.runs_per_case)],
                ["ラウンドの上限 / 続けて不採用で止める回数", f"{model.budget.max_rounds} / {model.budget.patience}"],
                ["同時に起動するサブエージェントの数", str(model.budget.parallel)],
            ],
        ),
        "",
        "## 検査（全ケースに当てるもの）",
        "",
        _render_checks(model) if model.checks else "なし（ケースごとの検査だけ）",
        "",
        "## 分割",
        "",
        render.render_table(
            ["分割", "件数", "グループごとの件数", "ケース"], _render_split_rows(dataset.cases, splits)
        ),
        "",
        "学習役に見せるのは学習用だけで、テスト用は最後に1回だけ使う。",
        "",
        "## サブエージェントの起動回数の見積もり（上限）",
        "",
        render.render_table(["段階", "回数"], _compute_estimate(model, splits)),
        "",
        "## 警告",
        "",
        render.render_bullets(warnings),
    ]
    return "\n".join(sections) + "\n"


def check_plan(where: layout.Layout) -> str:
    dataset = workspace.load_dataset(where)
    splits = workspace.compute_splits(dataset.model, dataset.cases)
    record = {
        "plan_sha": workspace.compute_plan_sha(where),
        "dataset_sha": workspace.compute_dataset_sha(where),
        "splits": dict(sorted(splits.items())),
    }
    fsops.write_json(where.split_path, record)
    fsops.write_text(where.plan_md_path, _render_plan_md(dataset, splits))
    counts = "、".join(f"{name} {sum(1 for value in splits.values() if value == name)} 件" for name in plan.SPLITS)
    return f"計画に問題はありません（{counts}）。{where.display(where.plan_md_path)} を書きました"


def approve(where: layout.Layout, today: str) -> str:
    dataset = workspace.load_dataset(where)
    record = workspace.load_split_record(where)
    plan_sha = workspace.compute_plan_sha(where)
    dataset_sha = workspace.compute_dataset_sha(where)
    if record is None or (record.plan_sha, record.dataset_sha) != (plan_sha, dataset_sha):
        raise StageError(
            "check-plan の後に計画が変わりました。check-plan を実行し、plan.md を人に見せてから承認してください"
        )
    splits = workspace.compute_splits(dataset.model, dataset.cases)
    case_shas = {case.id: workspace.compute_case_sha(where, dataset.model, case) for case in dataset.cases}
    test_sha = workspace.compute_test_sha(case_shas, splits)
    previous = workspace.load_approval(where)
    first = where.version_dir(layout.FIRST_VERSION)
    if not first.is_dir():
        fsops.copy_tree(where.skill_dir(dataset.model.target.skill_path), first)
    test_changed = previous is not None and previous.test_sha != test_sha
    entry = contracts.HistoryEntry(
        on=today, kind=contracts.APPROVE_KIND, detail="計画を承認した", test_changed=test_changed
    )
    approval = contracts.Approval(
        plan_sha=plan_sha,
        dataset_sha=dataset_sha,
        test_sha=test_sha,
        skill_sha=previous.skill_sha if previous is not None else fsops.compute_tree_sha(first),
        approved_on=today,
        history=(*(previous.history if previous is not None else ()), entry),
    )
    fsops.write_json(where.approval_path, contracts.build_approval_data(approval))
    note = "（テスト用のケースが前の承認から変わった。報告に記録する）" if test_changed else ""
    return f"承認を記録しました。対象スキルの写しは {where.display(first)}{note}"
