"""学習役と監査役に渡す証拠（ケースと実行の結果）を Markdown にする。"""

from __future__ import annotations

from collections.abc import Sequence

from tune_kit import contracts, fsops, layout, plan, render

RESPONSE_LIMIT = 3000


def _render_excerpt(text: str) -> str:
    if len(text) <= RESPONSE_LIMIT:
        return text
    return text[:RESPONSE_LIMIT] + f"\n…（{len(text) - RESPONSE_LIMIT} 文字を省略）"


def _render_checks(model: plan.Plan, case: plan.Case) -> str:
    rows = []
    for check in plan.list_case_checks(model, case):
        body = check.criterion or check.value or check.pattern or check.run or check.expected_file or render.MISSING
        rows.append([check.id, check.kind, check.severity, check.target, body])
    return render.render_table(["ID", "種類", "重さ", "対象", "内容"], rows)


def _render_run(where: layout.Layout, result: contracts.Result) -> list[str]:
    result_dir = where.result_dir(result.version, result.case_id, result.run_no)
    response = fsops.read_optional_text(result_dir / layout.RESPONSE_FILE) or render.MISSING
    rows = [[o.check_id, o.severity, "合格" if o.passed else "不合格", o.by, o.detail] for o in result.outcomes]
    verdict = "合格" if result.must_passed else "不合格"
    return [
        f"### 実行 {result.run_no}（{verdict}）",
        "",
        render.render_table(["検査", "重さ", "判定", "判定した者", "根拠"], rows),
        "",
        f"返答（全文: {where.display(result_dir / layout.RESPONSE_FILE)}）:",
        "",
        render.render_fence(_render_excerpt(response)),
        "",
        "変えたファイル:",
        render.render_bullets(list(result.changed)),
        f"差分: {where.display(result_dir / layout.CHANGES_FILE)}",
        "",
    ]


def render_case(
    where: layout.Layout, model: plan.Plan, case: plan.Case, split: str, results: Sequence[contracts.Result]
) -> str:
    """1件のケースの証拠。依頼、正解、入力と正解のファイル、検査、各実行の判定と返答。"""
    passed = sum(1 for result in results if result.must_passed)
    inputs = [where.display(where.input_dir(case.id) / name) for name in fsops.list_files(where.input_dir(case.id))]
    expected_files = [
        where.display(where.expected_dir(case.id) / name) for name in fsops.list_files(where.expected_dir(case.id))
    ]
    lines = [
        f"## ケース {case.id}（分割 {split}、グループ {case.group}、合格 {passed} / {len(results)}）",
        "",
        "依頼:",
        "",
        render.render_fence(case.prompt),
        "",
        "正解:",
        "",
        render.render_fence(case.expected) if case.expected is not None else "正解なし（評価項目で測る）",
        "",
        "入力のファイル:",
        render.render_bullets(inputs),
        "",
        "正解のファイル:",
        render.render_bullets(expected_files),
        "",
        "検査:",
        "",
        _render_checks(model, case),
        "",
    ]
    for result in results:
        lines += _render_run(where, result)
    return "\n".join(lines)
