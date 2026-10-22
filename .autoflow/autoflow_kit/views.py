"""人とサブエージェントが読む版（計画、プロファイル、レビューの結果、関所の理由、表）を Markdown で作る。"""

from __future__ import annotations

from autoflow_kit import contracts, policy, profile, render

TAG_LABELS = {policy.IMPORTANT: "Important", policy.NIT: "Nit", policy.PRE_EXISTING: "Pre-existing"}


def render_kinds() -> str:
    rows = [[f"`{kind.name}`", kind.label, "要る" if kind.repro else "—", kind.checks] for kind in policy.KINDS]
    return render.table(["種類", "意味", "再現のテスト", "確かめること"], rows)


def render_tiers() -> str:
    rows = [[f"`{tier.name}`", tier.depth, tier.human] for tier in policy.TIERS]
    return render.table(["段", "レビューの深さ", "H3 で人がすること"], rows)


def render_plan(plan: contracts.Plan, flow: policy.Flow) -> str:
    kind = policy.kind_of(plan.kind)
    criteria = [[item.id, item.text, item.check, item.run or render.MISSING] for item in plan.criteria]
    questions = [[item.question, item.default, item.impact] for item in plan.open_questions]
    parts = [
        "# 計画",
        "",
        f"- 種類: `{plan.kind}`（{kind.label}）",
        f"- ゴール: {plan.goal}",
        f"- 予測のリスクの段: `{flow.forecast_tier}`",
        f"- コミットの件名の案: {plan.commit_subject}",
        "",
        "## 組んだ手順",
        "",
        render.bullets(flow.steps),
        "",
        "## H1 に当たった条件",
        "",
        render.bullets([f"`{rule}` {policy.rule_text(rule)}" for rule in flow.h1_reasons]),
        "",
        "## 範囲",
        "",
        render.bullets([f"`{path}`" for path in plan.scope]),
        "",
        "## やらないこと",
        "",
        render.bullets(plan.non_goals),
        "",
        "## 受け入れ条件と確かめ方",
        "",
        render.table(["id", "条件", "確かめ方", "コマンド"], criteria),
        "",
        "## 依頼から決まらなかった値",
        "",
        render.table(["問い", "既定で使う値", "影響"], questions) if questions else render.bullets([]),
        "",
        "## 足す依存",
        "",
        render.bullets(plan.dependencies_to_add),
        "",
        "## 戻し方",
        "",
        plan.revert,
        "",
    ]
    if kind.repro:
        parts += ["## 再現と原因", "", f"- 再現のコマンド: `{plan.repro}`", f"- 原因の見立て: {plan.root_cause}", ""]
    return "\n".join(parts)


def render_profile(settings: profile.Profile) -> str:
    commands = [
        [command.id, f"`{command.run}`", render.number(command.timeout_sec)] for command in settings.verify.commands
    ]
    limits = settings.limits
    limit_rows = [
        ["検査の失敗が続いたら H2", render.number(limits.fix_attempts)],
        ["Important が残るレビューが続いたら H2", render.number(limits.review_rounds)],
        ["計画の範囲のファイル数がこれを超えたら H1", render.number(limits.max_scope_files)],
        ["差分の行数がこれを超えたら少なくとも medium", render.number(limits.large_diff_lines)],
        ["差分の行数がこれを超えたら high", render.number(limits.huge_diff_lines)],
    ]
    return "\n".join(
        [
            "# プロファイル",
            "",
            "## 検査コマンド（verify が順に実行する）",
            "",
            render.table(["id", "コマンド", "上限（秒）"], commands),
            "",
            "## 常に人が差分を読むパス（risk.always_human）",
            "",
            render.bullets([f"`{path}`" for path in settings.risk.always_human]),
            "",
            "## リスクの段を high にするパス（risk.high）",
            "",
            render.bullets([f"`{path}`" for path in settings.risk.high]),
            "",
            "## これとテストだけなら low にするパス（risk.low）",
            "",
            render.bullets([f"`{path}`" for path in settings.risk.low]),
            "",
            "## テストのパス（paths.tests）",
            "",
            render.bullets([f"`{path}`" for path in settings.paths.tests]),
            "",
            "## レビュー",
            "",
            f"- 探索役と検証役に渡す指示: {', '.join(settings.review.guide_files) or render.MISSING}",
            f"- 指摘しないパス: {', '.join(settings.review.skip) or render.MISSING}",
            "",
            "## 上限",
            "",
            render.table(["条件", "値"], limit_rows),
            "",
            "## コミットの文の最後に足す行",
            "",
            render.bullets(settings.commit.trailers),
            "",
        ]
    )


def finding_line(item: contracts.Kept) -> str:
    """指摘の1行。プロンプトと報告書で同じ書き方にする。"""
    finding = item.finding
    others = f"（同じ種類の他の箇所: {', '.join(finding.other_locations)}）" if finding.other_locations else ""
    return (
        f"{item.id} [{TAG_LABELS.get(item.tag, item.tag)}] {finding.title} — `{finding.file}:{finding.line}`、"
        f"種類 {finding.bug_class}{others}"
    )


def render_review(result: contracts.ReviewResult) -> str:
    rows = [
        [
            item.id,
            TAG_LABELS.get(item.tag, item.tag),
            item.finding.title,
            f"{item.finding.file}:{item.finding.line}",
            item.finding.bug_class,
            f"{item.real_votes}/{item.voters}",
        ]
        for item in result.kept
    ]
    details = []
    for item in result.kept:
        details += [f"### {item.id} {item.finding.title}", "", item.finding.evidence, ""]
        if item.finding.other_locations:
            details += [render.bullets(item.finding.other_locations), ""]
    return "\n".join(
        [
            f"# レビュー ラウンド {result.round_no}",
            "",
            f"- 深さ: {result.depth}",
            f"- 差分: `{result.base[:12]}` → `{result.tree[:12]}`",
            f"- 票で落ちた候補: {', '.join(result.dropped) or render.MISSING}",
            "",
            render.table(["id", "重大度", "指摘", "場所", "バグの種類", "本物の票"], rows),
            "",
            *details,
        ]
    )


def render_gate(gate_id: str, reasons: tuple[str, ...], details: tuple[str, ...]) -> str:
    """H1・H2 の関所で人に見せる理由と選択肢。"""
    gate = policy.gate_of(gate_id)
    options = [[f"`{option.name}`", option.label, option.then] for option in gate.options]
    return "\n".join(
        [
            f"# {gate.id} {gate.label}",
            "",
            "## 当たった条件",
            "",
            render.bullets([f"`{rule}` {policy.rule_text(rule)}" for rule in reasons]),
            "",
            "## 今の状況",
            "",
            render.bullets(details),
            "",
            "## 選べること",
            "",
            render.table(["選択", "意味", "その後"], options),
            "",
        ]
    )
