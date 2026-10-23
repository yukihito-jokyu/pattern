"""作業場所のファイルを読み、検証済みの型と進み具合を返す。ファイルは書かない（STATE-01）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tune_kit import contracts, fsops, layout, metrics, plan, splitting
from tune_kit.errors import InvalidFileError, StageError

# 1回の実行の状態。左から順に進む
UNPREPARED = "unprepared"
EXECUTING = "executing"
COLLECTING = "collecting"
GRADING = "grading"
SCORING = "scoring"
DONE = "done"


@dataclass(frozen=True)
class Dataset:
    model: plan.Plan
    cases: tuple[plan.Case, ...]


@dataclass(frozen=True)
class Approved:
    """承認済みで、承認の後に変わっていない計画とケース。splits はケースの ID から分割の名前。"""

    model: plan.Plan
    cases: tuple[plan.Case, ...]
    splits: dict[str, str]
    case_shas: dict[str, str]
    approval: contracts.Approval

    def list_cases(self, split: str) -> tuple[plan.Case, ...]:
        return tuple(case for case in self.cases if self.splits.get(case.id) == split)

    def find_case(self, case_id: str) -> plan.Case | None:
        return next((case for case in self.cases if case.id == case_id), None)


@dataclass(frozen=True)
class RunRef:
    """1回の実行。key は作業場所の名前（版を伏せたハッシュ）。"""

    version: str
    case_id: str
    run_no: int
    case_sha: str
    key: str


def _require_valid(path: Path, problems: list[str]) -> None:
    if problems:
        raise InvalidFileError(str(path), problems)


def load_plan(where: layout.Layout) -> plan.Plan:
    model, problems = plan.parse_plan(fsops.read_json(where.plan_path))
    _require_valid(where.plan_path, problems)
    if model is None:
        raise InvalidFileError(str(where.plan_path), ["plan.json を読めません"])
    return model


def load_cases(where: layout.Layout) -> tuple[plan.Case, ...]:
    cases, problems = plan.parse_cases(fsops.read_json(where.cases_path))
    _require_valid(where.cases_path, problems)
    return cases


def check_files(where: layout.Layout, model: plan.Plan, cases: Sequence[plan.Case]) -> list[str]:
    """ファイルの有無の検査（対象スキル、正解のファイル、ケースの無いファイルのディレクトリ）。"""
    problems: list[str] = []
    skill_dir = where.skill_dir(model.target.skill_path)
    if not (skill_dir / layout.SKILL_FILE).is_file():
        problems.append(f"対象スキル {model.target.skill_path} に {layout.SKILL_FILE} がありません")
    ids = {case.id for case in cases}
    stray = sorted({relative.split("/")[0] for relative in fsops.list_files(where.files_dir)} - ids)
    problems += [f"dataset/files/{name}/ に対応するケースがありません" for name in stray]
    for case in cases:
        expected_files = fsops.list_files(where.expected_dir(case.id))
        if model.mode == plan.REFERENCE and case.expected == "" and not expected_files:
            problems.append(
                f"ケース {case.id}: expected が空で、正解のファイル（files/{case.id}/expected/）もありません"
            )
        for check in plan.list_case_checks(model, case):
            if check.expected_file and check.expected_file not in expected_files:
                problems.append(
                    f"ケース {case.id}: 検査 {check.id} の正解のファイル {check.expected_file} がありません"
                )
    return problems


def compute_splits(model: plan.Plan, cases: Sequence[plan.Case]) -> dict[str, str]:
    items = [splitting.SplitItem(case_id=case.id, group=case.group, pinned=case.split) for case in cases]
    ratios = splitting.Ratios(train=model.split.train, val=model.split.val, test=model.split.test)
    return splitting.compute_split(items, model.split.seed, ratios)


def check_splits(splits: dict[str, str]) -> list[str]:
    counts = {name: sum(1 for value in splits.values() if value == name) for name in plan.SPLITS}
    return [
        f"分割 {name} のケースが0件です（ケースの split の固定を見直す）"
        for name, count in counts.items()
        if count == 0
    ]


def list_dataset_problems(where: layout.Layout) -> list[str]:
    """計画とケースの問題を、ファイルの有無と分割まで含めて全部集める。status が表示に使う。"""
    plan_data, problems = fsops.read_json_problems(where.plan_path)
    cases_data, found = fsops.read_json_problems(where.cases_path)
    problems += found
    if problems:
        return problems
    model, problems = plan.parse_plan(plan_data)
    cases, found = plan.parse_cases(cases_data)
    problems += found
    if problems or model is None:
        return problems
    problems = plan.check_dataset(model, cases) + check_files(where, model, cases)
    return problems or check_splits(compute_splits(model, cases))


def load_dataset(where: layout.Layout) -> Dataset:
    """計画とケースを読む。問題があれば全部まとめて投げる。"""
    _require_valid(where.target_dir, list_dataset_problems(where))
    return Dataset(model=load_plan(where), cases=load_cases(where))


def compute_plan_sha(where: layout.Layout) -> str:
    return fsops.compute_data_sha(fsops.read_json(where.plan_path))


def compute_dataset_sha(where: layout.Layout) -> str:
    return fsops.compute_data_sha([fsops.read_json(where.cases_path), fsops.compute_tree_sha(where.files_dir)])


def compute_case_sha(where: layout.Layout, model: plan.Plan, case: plan.Case) -> str:
    """ケースの中身のハッシュ。入力、正解、当てる検査、sandbox の形が変われば変わる（結果が古くなる）。"""
    return fsops.compute_data_sha(
        {
            "case": plan.build_case_data(case),
            "checks": [plan.build_check_data(check) for check in plan.list_case_checks(model, case)],
            "sandbox": model.sandbox,
            "input": fsops.compute_tree_sha(where.input_dir(case.id)),
            "expected": fsops.compute_tree_sha(where.expected_dir(case.id)),
        }
    )


def compute_test_sha(case_shas: dict[str, str], splits: dict[str, str]) -> str:
    return fsops.compute_data_sha(sorted(sha for case_id, sha in case_shas.items() if splits.get(case_id) == plan.TEST))


def compute_skill_sha(where: layout.Layout, model: plan.Plan) -> str:
    return fsops.compute_tree_sha(where.skill_dir(model.target.skill_path))


def load_split_record(where: layout.Layout) -> contracts.SplitRecord | None:
    if not where.split_path.is_file():
        return None
    record, problems = contracts.parse_split_record(fsops.read_json(where.split_path))
    _require_valid(where.split_path, problems)
    return record


def load_approval(where: layout.Layout) -> contracts.Approval | None:
    if not where.approval_path.is_file():
        return None
    approval, problems = contracts.parse_approval(fsops.read_json(where.approval_path))
    _require_valid(where.approval_path, problems)
    return approval


def is_approved(where: layout.Layout, approval: contracts.Approval | None) -> bool:
    """承認があり、承認の後に plan.json と dataset/ が変わっていない。"""
    if approval is None:
        return False
    return approval.plan_sha == compute_plan_sha(where) and approval.dataset_sha == compute_dataset_sha(where)


def load_approved(where: layout.Layout) -> Approved:
    """評価を進める段の入口が最初に呼ぶ（OPS-04）。承認が無いか古ければ止める。"""
    dataset = load_dataset(where)
    approval = load_approval(where)
    if approval is None or not is_approved(where, approval):
        raise StageError("計画が未承認か、承認の後に変わりました。status を実行し、計画の承認からやり直してください")
    case_shas = {case.id: compute_case_sha(where, dataset.model, case) for case in dataset.cases}
    return Approved(dataset.model, dataset.cases, compute_splits(dataset.model, dataset.cases), case_shas, approval)


def list_runs(approved: Approved, version: str, splits: Sequence[str]) -> tuple[RunRef, ...]:
    """版と分割に対して要る実行の一覧（ケースの順 × 回）。"""
    refs: list[RunRef] = []
    for case in approved.cases:
        if approved.splits.get(case.id) not in splits:
            continue
        sha = approved.case_shas[case.id]
        for run_no in range(1, approved.model.budget.runs_per_case + 1):
            key = layout.build_run_key(version, case.id, run_no, sha)
            refs.append(RunRef(version=version, case_id=case.id, run_no=run_no, case_sha=sha, key=key))
    return tuple(refs)


def load_result(where: layout.Layout, ref: RunRef) -> contracts.Result | None:
    """有効な結果。無いか、ケースが変わって古ければ None。"""
    path = where.result_dir(ref.version, ref.case_id, ref.run_no) / layout.RESULT_FILE
    if not path.is_file():
        return None
    result, problems = contracts.parse_result(fsops.read_json(path))
    _require_valid(path, problems)
    return result if result.case_sha == ref.case_sha else None


def list_judge_ids(approved: Approved, case_id: str) -> tuple[str, ...]:
    case = approved.find_case(case_id)
    if case is None:
        return ()
    return tuple(check.id for check in plan.list_case_checks(approved.model, case) if check.kind == "judge")


def compute_run_state(where: layout.Layout, approved: Approved, ref: RunRef) -> str:
    if load_result(where, ref) is not None:
        return DONE
    run_dir = where.run_dir(ref.key)
    if not (run_dir / layout.EXECUTOR_PROMPT_FILE).is_file():
        return UNPREPARED
    if not (run_dir / layout.RESPONSE_FILE).is_file():
        return EXECUTING
    if not (run_dir / layout.CHECKS_FILE).is_file():
        return COLLECTING
    if list_judge_ids(approved, ref.case_id) and not (run_dir / layout.GRADE_FILE).is_file():
        return GRADING
    return SCORING


def load_collected(where: layout.Layout, ref: RunRef) -> contracts.Collected:
    path = where.run_dir(ref.key) / layout.CHECKS_FILE
    collected, problems = contracts.parse_collected(fsops.read_json(path))
    _require_valid(path, problems)
    return collected


def list_grade_problems(where: layout.Layout, ref: RunRef, judge_ids: Sequence[str]) -> list[str]:
    """採点役の grade.json の問題。例外にしないのは、問題のある採点だけをやり直させるため。"""
    data, problems = fsops.read_json_problems(where.run_dir(ref.key) / layout.GRADE_FILE)
    if problems:
        return problems
    return contracts.parse_grades(data, judge_ids)[1]


def load_grades(where: layout.Layout, ref: RunRef, judge_ids: Sequence[str]) -> tuple[contracts.Grade, ...]:
    path = where.run_dir(ref.key) / layout.GRADE_FILE
    grades, problems = contracts.parse_grades(fsops.read_json(path), judge_ids)
    _require_valid(path, problems)
    return grades


def load_results(
    where: layout.Layout, approved: Approved, version: str, splits: Sequence[str]
) -> tuple[contracts.Result, ...]:
    """版と分割の全部の結果。足りなければ止める。"""
    refs = list_runs(approved, version, splits)
    results = [load_result(where, ref) for ref in refs]
    missing = [ref for ref, result in zip(refs, results) if result is None]
    if missing:
        raise StageError(
            f"{version} の評価（{', '.join(splits)}）が {len(missing)} 件終わっていません。status を実行してください"
        )
    return tuple(result for result in results if result is not None)


def compute_scores(results: Sequence[contracts.Result]) -> list[metrics.RunScore]:
    return [
        metrics.RunScore(
            case_id=result.case_id,
            must_passed=result.must_passed,
            checks=tuple((outcome.check_id, outcome.passed) for outcome in result.outcomes),
        )
        for result in results
    ]


def load_summary(where: layout.Layout, approved: Approved, version: str, split: str) -> metrics.Summary:
    return metrics.compute_summary(compute_scores(load_results(where, approved, version, [split])))


def has_results(where: layout.Layout, approved: Approved, version: str, splits: Sequence[str]) -> bool:
    return all(load_result(where, ref) is not None for ref in list_runs(approved, version, splits))


def load_decisions(where: layout.Layout) -> tuple[contracts.DecisionRecord, ...]:
    """r1 から続けて決定のあるラウンドの決定。"""
    decisions: list[contracts.DecisionRecord] = []
    number = 1
    while (where.round_dir(number) / layout.DECISION_FILE).is_file():
        path = where.round_dir(number) / layout.DECISION_FILE
        decision, problems = contracts.parse_decision(fsops.read_json(path))
        _require_valid(path, problems)
        decisions.append(decision)
        number += 1
    return tuple(decisions)


def compute_current(decisions: Sequence[contracts.DecisionRecord]) -> str:
    """今の版。採用された最後の候補、無ければ v0。"""
    adopted = [decision.candidate for decision in decisions if decision.adopted]
    return adopted[-1] if adopted else layout.FIRST_VERSION


def compute_stop_reason(
    model: plan.Plan, decisions: Sequence[contracts.DecisionRecord], current_val: metrics.Summary
) -> str:
    """ラウンドを止める理由。続けるなら空文字（architecture.md の表）。"""
    if metrics.is_perfect(current_val):
        return "今の版が検証用で全ケース・全検査に合格した"
    if len(decisions) >= model.budget.max_rounds:
        return f"ラウンドが上限（{model.budget.max_rounds}）に達した"
    recent = decisions[-model.budget.patience :]
    if len(recent) == model.budget.patience and not any(decision.adopted for decision in recent):
        return f"直近 {model.budget.patience} 回が続けて不採用だった"
    return ""


def list_proposal_problems(where: layout.Layout, number: int, train_ids: Sequence[str]) -> list[str]:
    """学習役の proposal.json の問題。例外にしないのは、問題をプロンプトに書き足してやり直させるため。"""
    data, problems = fsops.read_json_problems(where.round_dir(number) / layout.PROPOSAL_FILE)
    if problems:
        return problems
    return contracts.parse_proposal(data, train_ids)[1]


def load_proposal(where: layout.Layout, number: int, train_ids: Sequence[str]) -> contracts.Proposal:
    path = where.round_dir(number) / layout.PROPOSAL_FILE
    proposal, problems = contracts.parse_proposal(fsops.read_json(path), train_ids)
    _require_valid(path, problems)
    return proposal


def list_audit_problems(
    where: layout.Layout, number: int | None, approved: Approved, originals: dict[str, plan.Case]
) -> list[str]:
    """監査役の audit.json の問題。例外にしないのは、問題をプロンプトに書き足してやり直させるため。"""
    data, problems = fsops.read_json_problems(where.audit_dir(number) / layout.AUDIT_FILE)
    if problems:
        return problems
    check_ids = [check.id for check in approved.model.checks]
    return contracts.parse_audit(data, originals, check_ids, allow_fix=number is not None)[1]


def load_audit(
    where: layout.Layout, number: int | None, approved: Approved, originals: dict[str, plan.Case]
) -> contracts.Audit:
    path = where.audit_dir(number) / layout.AUDIT_FILE
    check_ids = [check.id for check in approved.model.checks]
    audit, problems = contracts.parse_audit(fsops.read_json(path), originals, check_ids, allow_fix=number is not None)
    _require_valid(path, problems)
    return audit


def load_fixes(where: layout.Layout, number: int) -> contracts.Fixes | None:
    path = where.round_dir(number) / layout.FIXES_FILE
    if not path.is_file():
        return None
    fixes, problems = contracts.parse_fixes(fsops.read_json(path))
    _require_valid(path, problems)
    return fixes


def load_applied(where: layout.Layout) -> contracts.Applied | None:
    if not where.applied_path.is_file():
        return None
    applied, problems = contracts.parse_applied(fsops.read_json(where.applied_path))
    _require_valid(where.applied_path, problems)
    return applied


def list_failures(
    where: layout.Layout, approved: Approved, version: str, splits: Sequence[str]
) -> dict[str, tuple[contracts.Result, ...]]:
    """不合格の実行があるケースと、そのケースの全実行の結果。"""
    failures: dict[str, list[contracts.Result]] = {}
    for result in load_results(where, approved, version, splits):
        failures.setdefault(result.case_id, []).append(result)
    return {case_id: tuple(items) for case_id, items in failures.items() if not all(item.must_passed for item in items)}


def list_failing_cases(
    where: layout.Layout, approved: Approved, version: str, splits: Sequence[str]
) -> dict[str, plan.Case]:
    """不合格の実行があるケース。監査の対象（監査役が直してよいケース）になる。"""
    failures = list_failures(where, approved, version, splits)
    return {case.id: case for case in approved.cases if case.id in failures}


def find_skill_name(skill_md: str) -> str:
    """SKILL.md の frontmatter の name。無ければ空文字。"""
    lines = skill_md.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            return ""
        key, _, value = line.partition(":")
        if key.strip() == "name":
            return value.strip().strip("\"'")
    return ""
