"""学習役に候補の版を直させる準備をし（learn）、学習役の提案と候補を検査する（learn-check）。"""

from __future__ import annotations

import difflib
import unicodedata
from collections.abc import Sequence

from tune_kit import contracts, evidence, fsops, layout, plan, prompts, render, workspace
from tune_kit.errors import StageError

LINE_LIMIT = 500
# 検証用・テスト用の文の写しとみなす長さ（正規化した後の文字数。STATE-03）
COPY_MIN_CHARS = 20
DIFF_LIMIT = 400


def _require_round(where: layout.Layout, approved: workspace.Approved, number: int) -> str:
    """今のラウンドで、データの直しと今の版の評価が済んでいれば、今の版を返す。"""
    decisions = workspace.load_decisions(where)
    if len(decisions) != number - 1:
        raise StageError(
            f"{number} 回目のラウンドは今のラウンドではありません（決定済み {len(decisions)} 回）。"
            "status を実行してください"
        )
    if workspace.load_fixes(where, number) is None:
        raise StageError(f"{number} 回目のラウンドのデータの直しが決まっていません。status を実行してください")
    current = workspace.compute_current(decisions)
    if not workspace.has_results(where, approved, current, (plan.TRAIN, plan.VAL)):
        raise StageError(f"今の版 {current} の学習用・検証用の評価が終わっていません。status を実行してください")
    return current


def _render_evidence(where: layout.Layout, approved: workspace.Approved, current: str) -> str:
    """学習用のケースだけの証拠。不合格のケースを先に並べる（STATE-03）。"""
    results = workspace.load_results(where, approved, current, (plan.TRAIN,))
    cases = approved.list_cases(plan.TRAIN)
    by_case = {case.id: [result for result in results if result.case_id == case.id] for case in cases}
    ordered = sorted(cases, key=lambda case: (all(result.must_passed for result in by_case[case.id]), case.id))
    sections = [f"# 学習用の証拠（今の版 {current}）", ""]
    sections += [evidence.render_case(where, approved.model, case, plan.TRAIN, by_case[case.id]) for case in ordered]
    return "\n".join(sections) + "\n"


def _render_history(where: layout.Layout, approved: workspace.Approved) -> str:
    rows = []
    train_ids = [case.id for case in approved.list_cases(plan.TRAIN)]
    for decision in workspace.load_decisions(where):
        proposal = workspace.load_proposal(where, decision.round, train_ids)
        summary = " / ".join(change.summary for change in proposal.changes) or proposal.notes
        rows.append(
            [
                str(decision.round),
                decision.candidate,
                "採用" if decision.adopted else "不採用",
                decision.reason,
                summary,
            ]
        )
    if not rows:
        return "なし（最初のラウンド）"
    return render.render_table(["ラウンド", "候補", "採否", "理由", "変更の要約"], rows)


def _render_plan_checks(model: plan.Plan) -> str:
    rows = [
        [
            check.id,
            check.kind,
            check.severity,
            check.criterion or check.value or check.pattern or check.run or check.target,
        ]
        for check in model.checks
    ]
    return render.render_table(["ID", "種類", "重さ", "内容"], rows) if rows else "なし（ケースごとの検査だけ）"


def _write_prompt(
    where: layout.Layout, approved: workspace.Approved, number: int, current: str, problems: Sequence[str]
) -> None:
    directory = where.round_dir(number)
    values = {
        "goal": approved.model.goal,
        "checks": _render_plan_checks(approved.model),
        "current_dir": where.display(where.version_dir(current)),
        "candidate_dir": where.display(where.version_dir(layout.build_version(number))),
        "evidence_path": where.display(directory / layout.EVIDENCE_FILE),
        "proposal_path": where.display(directory / layout.PROPOSAL_FILE),
        "history": _render_history(where, approved),
        "problems": render.render_bullets(list(problems)),
        "line_limit": str(LINE_LIMIT),
        "train_ids": ", ".join(case.id for case in approved.list_cases(plan.TRAIN)),
    }
    fsops.write_text(directory / layout.LEARNER_PROMPT_FILE, prompts.render_prompt("learner", values))


def learn(where: layout.Layout, number: int) -> str:
    approved = workspace.load_approved(where)
    current = _require_round(where, approved, number)
    directory = where.round_dir(number)
    if (directory / layout.LEARNER_PROMPT_FILE).is_file():
        raise StageError(f"{number} 回目のラウンドの学習は準備済みです。status を実行してください")
    candidate = layout.build_version(number)
    fsops.copy_tree(where.version_dir(current), where.version_dir(candidate))
    fsops.write_text(directory / layout.EVIDENCE_FILE, _render_evidence(where, approved, current))
    _write_prompt(where, approved, number, current, [])
    return (
        f"学習の準備: 今の版 {current} を候補 {candidate} に写しました（{where.display(where.version_dir(candidate))}）"
    )


def _build_line(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _list_changed(where: layout.Layout, current: str, candidate: str) -> list[str]:
    before = where.version_dir(current)
    after = where.version_dir(candidate)
    names = sorted(set(fsops.list_files(before)) | set(fsops.list_files(after)))
    return [
        name
        for name in names
        if not (before / name).is_file()
        or not (after / name).is_file()
        or fsops.compute_file_sha(before / name) != fsops.compute_file_sha(after / name)
    ]


def _list_added_lines(where: layout.Layout, current: str, candidate: str, changed: Sequence[str]) -> list[str]:
    added: list[str] = []
    for name in changed:
        old = fsops.read_optional_text(where.version_dir(current) / name) or ""
        new = fsops.read_optional_text(where.version_dir(candidate) / name) or ""
        known = {_build_line(line) for line in old.splitlines()}
        added += [_build_line(line) for line in new.splitlines() if _build_line(line) not in known]
    return added


def _list_fragments(cases: Sequence[plan.Case]) -> list[tuple[str, str]]:
    """ケースの文のうち、写しとみなす長さの行と、そのケースの ID。"""
    fragments: list[tuple[str, str]] = []
    for case in cases:
        texts = [case.prompt, case.expected or ""]
        texts += [check.value + "\n" + check.criterion + "\n" + check.pattern for check in case.checks]
        for text in texts:
            fragments += [
                (case.id, line)
                for line in (_build_line(raw) for raw in text.splitlines())
                if len(line) >= COPY_MIN_CHARS
            ]
    return fragments


def _list_copies(added: Sequence[str], cases: Sequence[plan.Case]) -> list[str]:
    copies = []
    for case_id, fragment in _list_fragments(cases):
        if any(fragment in line for line in added):
            copies.append(f"{case_id}: 「{fragment[:60]}」")
    return sorted(set(copies))


def _check_candidate(
    where: layout.Layout, current: str, candidate: str, proposal: contracts.Proposal, changed: Sequence[str]
) -> list[str]:
    problems: list[str] = []
    declared = {change.file for change in proposal.changes}
    problems += [
        f"{name} を変えたのに proposal.json の changes にありません" for name in changed if name not in declared
    ]
    problems += [
        f"proposal.json の changes の {name} は変わっていません" for name in sorted(declared) if name not in changed
    ]
    skill_md = fsops.read_optional_text(where.version_dir(candidate) / layout.SKILL_FILE)
    if skill_md is None:
        return [*problems, f"候補に {layout.SKILL_FILE} がありません"]
    original = fsops.read_optional_text(where.version_dir(current) / layout.SKILL_FILE) or ""
    if workspace.find_skill_name(skill_md) != workspace.find_skill_name(original):
        problems.append("SKILL.md の frontmatter の name を変えないでください")
    if len(skill_md.splitlines()) > LINE_LIMIT:
        problems.append(
            f"SKILL.md が {len(skill_md.splitlines())} 行です。"
            f"{LINE_LIMIT} 行以内にし、詳細は references/ に移してください"
        )
    return problems


def _render_diff(where: layout.Layout, current: str, candidate: str, changed: Sequence[str]) -> str:
    lines: list[str] = []
    for name in changed:
        old = (fsops.read_optional_text(where.version_dir(current) / name) or "").splitlines()
        new = (fsops.read_optional_text(where.version_dir(candidate) / name) or "").splitlines()
        lines += difflib.unified_diff(old, new, f"{current}/{name}", f"{candidate}/{name}", lineterm="")
    if len(lines) > DIFF_LIMIT:
        lines = [*lines[:DIFF_LIMIT], f"…（{len(lines) - DIFF_LIMIT} 行を省略）"]
    return render.render_fence("\n".join(lines) or "（差分なし）", "diff")


def _render_proposal(proposal: contracts.Proposal, warnings: Sequence[str], diff: str, number: int) -> str:
    rows = [[change.file, change.summary, change.cause, ", ".join(change.cases)] for change in proposal.changes]
    return "\n".join(
        [
            f"# {number} 回目のラウンドの提案",
            "",
            render.render_table(["ファイル", "変更", "学習用の失敗の原因", "根拠のケース"], rows)
            if rows
            else "変更なし",
            "",
            "## 所見",
            "",
            proposal.notes or render.MISSING,
            "",
            "## 警告（学習用の文の写し。合わせすぎの疑い）",
            "",
            render.render_bullets(list(warnings)),
            "",
            "## 差分",
            "",
            diff,
            "",
        ]
    )


def learn_check(where: layout.Layout, number: int) -> str:
    approved = workspace.load_approved(where)
    current = _require_round(where, approved, number)
    directory = where.round_dir(number)
    candidate = layout.build_version(number)
    train_ids = [case.id for case in approved.list_cases(plan.TRAIN)]
    problems = workspace.list_proposal_problems(where, number, train_ids)
    changed = _list_changed(where, current, candidate)
    added = _list_added_lines(where, current, candidate, changed)
    held_out = approved.list_cases(plan.VAL) + approved.list_cases(plan.TEST)
    problems += [f"検証用・テスト用の文の写しがあります（{copy}）" for copy in _list_copies(added, held_out)]
    if not problems:
        proposal = workspace.load_proposal(where, number, train_ids)
        problems = _check_candidate(where, current, candidate, proposal, changed)
    if problems:
        fsops.remove_tree(directory / layout.PROPOSAL_FILE)
        _write_prompt(where, approved, number, current, problems)
        lines = "\n".join(f"  - {problem}" for problem in problems)
        raise StageError(
            f"提案に {len(problems)} 件の問題がありました。プロンプトに問題を書き足したので、"
            f"status の指示で学習役をもう一度起動してください:\n{lines}"
        )
    warnings = _list_copies(added, approved.list_cases(plan.TRAIN))
    text = _render_proposal(proposal, warnings, _render_diff(where, current, candidate, changed), number)
    fsops.write_text(directory / layout.PROPOSAL_MD_FILE, text)
    written = where.display(directory / layout.PROPOSAL_MD_FILE)
    counts = f"変更 {len(proposal.changes)} 件、写しの警告 {len(warnings)} 件"
    return f"提案に問題はありません（{counts}）。{written} を書きました"
