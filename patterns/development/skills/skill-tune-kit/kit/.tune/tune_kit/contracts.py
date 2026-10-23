"""段とサブエージェントの間で受け渡す JSON の形を定義し、検証する。問題は全部集めて返す。"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from fractions import Fraction

from tune_kit import layout, plan

# サブエージェントの名前。kit/claude/agents/<名前>.md と1対1（PROC-02）
AGENTS = {
    "executor": "tune-executor",
    "grader": "tune-grader",
    "learner": "tune-learner",
    "auditor": "tune-auditor",
}
# 監査役が失敗に付ける原因。skill 以外はデータの直しを伴う（ADR 0009）
SKILL_CAUSE = "skill"
CAUSES = (SKILL_CAUSE, "expected", "check", "input")
FINDING_ID = re.compile(r"F[0-9]{1,3}")
# decision.json の率。分数の文字列（例 2/3）で書き、評価しなかった率は空文字
RATE = re.compile(r"[0-9]+(/[1-9][0-9]*)?")
MACHINE = "machine"
GRADER = "grader"
# approval.json の history の kind
APPROVE_KIND = "approve"
DATA_FIX_KIND = "data-fix"


@dataclass(frozen=True)
class Grade:
    check_id: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class Outcome:
    """1つの検査の判定。by は判定した者（machine か grader）。"""

    check_id: str
    kind: str
    severity: str
    passed: bool
    detail: str
    by: str


@dataclass(frozen=True)
class Collected:
    """eval-collect が書く機械の検査の結果と、sandbox で変わったファイル。"""

    outcomes: tuple[Outcome, ...]
    changed: tuple[str, ...]


@dataclass(frozen=True)
class Result:
    version: str
    case_id: str
    run_no: int
    case_sha: str
    outcomes: tuple[Outcome, ...]
    changed: tuple[str, ...]

    @property
    def must_passed(self) -> bool:
        return all(outcome.passed for outcome in self.outcomes if outcome.severity == plan.MUST)


@dataclass(frozen=True)
class Change:
    file: str
    summary: str
    cause: str
    cases: tuple[str, ...]


@dataclass(frozen=True)
class Proposal:
    changes: tuple[Change, ...]
    notes: str


@dataclass(frozen=True)
class Finding:
    """監査役の指摘。fix_case か fix_check のどちらか（skill の原因と最後の監査では両方 None）。"""

    id: str
    case_id: str
    cause: str
    summary: str
    evidence: str
    fix_case: plan.Case | None
    fix_check: plan.Check | None

    @property
    def fixable(self) -> bool:
        return self.fix_case is not None or self.fix_check is not None


@dataclass(frozen=True)
class Audit:
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class HistoryEntry:
    on: str
    kind: str
    detail: str
    test_changed: bool


@dataclass(frozen=True)
class Approval:
    plan_sha: str
    dataset_sha: str
    test_sha: str
    skill_sha: str
    approved_on: str
    history: tuple[HistoryEntry, ...]


@dataclass(frozen=True)
class SplitRecord:
    plan_sha: str
    dataset_sha: str
    splits: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Fixes:
    applied: tuple[str, ...]
    rejected: tuple[str, ...]


@dataclass(frozen=True)
class DecisionRecord:
    """ラウンドの採否。率は決めた時点の合格率（後でデータが直されても報告に残すため）。"""

    round: int
    current: str
    candidate: str
    adopted: bool
    reason: str
    train_before: Fraction | None
    train_after: Fraction | None
    val_before: Fraction | None
    val_after: Fraction | None


@dataclass(frozen=True)
class Applied:
    applied: bool
    version: str
    on: str


def _read_record(data: object, where: str) -> tuple[dict[str, object], list[str]]:
    if not isinstance(data, dict):
        return {}, [f"{where} はオブジェクトにしてください"]
    return {str(key): value for key, value in data.items()}, []


def _read_text(record: dict[str, object], key: str, where: str, *, required: bool = True) -> tuple[str, list[str]]:
    value = record.get(key, "")
    if not isinstance(value, str):
        return "", [f"{where}.{key} は文字列にしてください"]
    if required and not value.strip():
        return value, [f"{where}.{key} が空です"]
    return value, []


def _read_flag(record: dict[str, object], key: str, where: str) -> tuple[bool, list[str]]:
    value = record.get(key)
    if not isinstance(value, bool):
        return False, [f"{where}.{key} は true か false にしてください"]
    return value, []


def _read_int(record: dict[str, object], key: str, where: str) -> tuple[int, list[str]]:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0, [f"{where}.{key} は整数にしてください"]
    return value, []


def _read_names(record: dict[str, object], key: str, where: str) -> tuple[tuple[str, ...], list[str]]:
    value = record.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return (), [f"{where}.{key} は文字列の配列にしてください"]
    return tuple(str(item) for item in value), []


def _read_rate(record: dict[str, object], key: str, where: str) -> tuple[Fraction | None, list[str]]:
    value = record.get(key, "")
    if value == "":
        return None, []
    if not isinstance(value, str) or not RATE.fullmatch(value):
        return None, [f"{where}.{key} は分数の文字列（例 2/3）か空文字にしてください"]
    return Fraction(value), []


def _read_items(record: dict[str, object], key: str, where: str) -> tuple[list[object], list[str]]:
    value = record.get(key)
    if not isinstance(value, list):
        return [], [f"{where}.{key} は配列にしてください"]
    return list(value), []


def parse_grades(data: object, judge_ids: Sequence[str]) -> tuple[tuple[Grade, ...], list[str]]:
    """採点役の grade.json。judge の検査の全部に1件ずつ判定がある。"""
    record, problems = _read_record(data, layout.GRADE_FILE)
    items, found = _read_items(record, "grades", layout.GRADE_FILE)
    problems += found
    grades: list[Grade] = []
    for index, item in enumerate(items):
        where = f"grade.json.grades[{index}]"
        entry, found = _read_record(item, where)
        check_id, more = _read_text(entry, "check_id", where)
        passed, flag = _read_flag(entry, "passed", where)
        reason, text = _read_text(entry, "reason", where)
        problems += found + more + flag + text
        grades.append(Grade(check_id=check_id, passed=passed, reason=reason))
    seen = [grade.check_id for grade in grades]
    problems += [f"grade.json に検査 {check_id} の判定がありません" for check_id in judge_ids if check_id not in seen]
    problems += [
        f"grade.json の {check_id} は採点する検査ではありません" for check_id in seen if check_id not in judge_ids
    ]
    problems += [
        f"grade.json に検査 {check_id} の判定が2つ以上あります"
        for check_id in sorted(set(seen))
        if seen.count(check_id) > 1
    ]
    return tuple(grades), problems


def _parse_outcome(data: object, where: str) -> tuple[Outcome, list[str]]:
    record, problems = _read_record(data, where)
    fields: dict[str, str] = {}
    for key in ("check_id", "kind", "severity", "by"):
        fields[key], found = _read_text(record, key, where)
        problems += found
    detail, found = _read_text(record, "detail", where, required=False)
    passed, flag = _read_flag(record, "passed", where)
    problems += found + flag
    outcome = Outcome(fields["check_id"], fields["kind"], fields["severity"], passed, detail, fields["by"])
    return outcome, problems


def _parse_outcomes(record: dict[str, object], where: str) -> tuple[tuple[Outcome, ...], list[str]]:
    items, problems = _read_items(record, "outcomes", where)
    outcomes: list[Outcome] = []
    for index, item in enumerate(items):
        outcome, found = _parse_outcome(item, f"{where}.outcomes[{index}]")
        problems += found
        outcomes.append(outcome)
    return tuple(outcomes), problems


def parse_collected(data: object) -> tuple[Collected, list[str]]:
    record, problems = _read_record(data, layout.CHECKS_FILE)
    outcomes, found = _parse_outcomes(record, layout.CHECKS_FILE)
    changed, more = _read_names(record, "changed", layout.CHECKS_FILE)
    return Collected(outcomes=outcomes, changed=changed), problems + found + more


def parse_result(data: object) -> tuple[Result, list[str]]:
    record, problems = _read_record(data, layout.RESULT_FILE)
    version, found = _read_text(record, "version", layout.RESULT_FILE)
    problems += found
    case_id, found = _read_text(record, "case_id", layout.RESULT_FILE)
    problems += found
    case_sha, found = _read_text(record, "case_sha", layout.RESULT_FILE)
    problems += found
    run_no, found = _read_int(record, "run_no", layout.RESULT_FILE)
    problems += found
    outcomes, found = _parse_outcomes(record, layout.RESULT_FILE)
    problems += found
    changed, found = _read_names(record, "changed", layout.RESULT_FILE)
    problems += found
    return Result(version, case_id, run_no, case_sha, outcomes, changed), problems


def parse_proposal(data: object, train_ids: Sequence[str]) -> tuple[Proposal, list[str]]:
    """学習役の proposal.json。cases に書けるのは学習用のケースだけ（STATE-03）。"""
    record, problems = _read_record(data, layout.PROPOSAL_FILE)
    items, found = _read_items(record, "changes", layout.PROPOSAL_FILE)
    notes, more = _read_text(record, "notes", layout.PROPOSAL_FILE, required=not items)
    problems += found + more
    changes: list[Change] = []
    for index, item in enumerate(items):
        where = f"proposal.json.changes[{index}]"
        entry, found = _read_record(item, where)
        problems += found
        fields: dict[str, str] = {}
        for key in ("file", "summary", "cause"):
            fields[key], found = _read_text(entry, key, where)
            problems += found
        cases, found = _read_names(entry, "cases", where)
        problems += found
        if fields["file"] and not plan.is_safe_relative(fields["file"]):
            problems.append(f"{where}.file はスキルのディレクトリからの相対パスにしてください")
        problems += [
            f"{where}.cases の {case_id} は学習用のケースではありません"
            for case_id in cases
            if case_id not in train_ids
        ]
        changes.append(Change(fields["file"], fields["summary"], fields["cause"], cases))
    return Proposal(changes=tuple(changes), notes=notes), problems


def _parse_fix(
    data: object, finding: Finding, originals: dict[str, plan.Case], check_ids: Sequence[str], where: str
) -> tuple[Finding, list[str]]:
    record, problems = _read_record(data, where)
    if sorted(record) not in (["case"], ["check"]):
        return finding, [*problems, f'{where} は {{"case": {{…}}}} か {{"check": {{…}}}} のどちらか1つにしてください']
    if "check" in record:
        check, found = plan.parse_check(record["check"], f"{where}.check")
        if check is not None and check.id not in check_ids:
            found.append(f"{where}.check.id {check.id} は計画の検査ではありません（計画の検査を置き換える形で書く）")
        return replace(finding, fix_check=check), problems + found
    case, found = plan.parse_case(record["case"], f"{where}.case")
    original = originals.get(finding.case_id)
    if case is None or original is None:
        return replace(finding, fix_case=case), problems + found
    if (case.id, case.group) != (original.id, original.group):
        found.append(f"{where}.case の id・group は元のケースと同じにしてください（分割が変わるため）")
    # split は監査役が直せない項目なので、書かれていても元の値に戻す（証拠の見出しの分割を写しがちなため）
    return replace(finding, fix_case=replace(case, split=original.split)), problems + found


def parse_audit(
    data: object, originals: dict[str, plan.Case], check_ids: Sequence[str], *, allow_fix: bool
) -> tuple[Audit, list[str]]:
    """監査役の audit.json。originals は監査の対象のケース、check_ids は計画の検査の ID。"""
    record, problems = _read_record(data, layout.AUDIT_FILE)
    items, found = _read_items(record, "findings", layout.AUDIT_FILE)
    problems += found
    findings: list[Finding] = []
    for index, item in enumerate(items):
        where = f"audit.json.findings[{index}]"
        entry, found = _read_record(item, where)
        fields: dict[str, str] = {}
        for key in ("id", "case_id", "cause", "summary", "evidence"):
            fields[key], more = _read_text(entry, key, where)
            found += more
        finding = Finding(
            fields["id"], fields["case_id"], fields["cause"], fields["summary"], fields["evidence"], None, None
        )
        found += _check_finding(finding, originals, where)
        fix = entry.get("fix")
        if fix is not None and (not allow_fix or finding.cause == SKILL_CAUSE):
            found.append(f"{where}.fix は null にしてください（原因が skill の指摘と、最後の監査では直しを書かない）")
        elif fix is None and allow_fix and finding.cause in CAUSES and finding.cause != SKILL_CAUSE:
            found.append(f"{where}.fix がありません（原因が {finding.cause} の指摘には直しを書く）")
        elif fix is not None:
            finding, more = _parse_fix(fix, finding, originals, check_ids, f"{where}.fix")
            found += more
        problems += found
        findings.append(finding)
    ids = [finding.id for finding in findings]
    problems += [
        f"audit.json の指摘の ID {finding_id} が重複しています"
        for finding_id in sorted(set(ids))
        if ids.count(finding_id) > 1
    ]
    covered = {finding.case_id for finding in findings}
    problems += [
        f"audit.json にケース {case_id} の指摘がありません（不合格のケースごとに1件以上）"
        for case_id in originals
        if case_id not in covered
    ]
    return Audit(findings=tuple(findings)), problems


def _check_finding(finding: Finding, originals: dict[str, plan.Case], where: str) -> list[str]:
    problems: list[str] = []
    if finding.id and not FINDING_ID.fullmatch(finding.id):
        problems.append(f"{where}.id は F と番号（F1、F2 …）にしてください")
    if finding.case_id and finding.case_id not in originals:
        problems.append(f"{where}.case_id {finding.case_id} は監査の対象のケースではありません")
    if finding.cause and finding.cause not in CAUSES:
        problems.append(f"{where}.cause は {', '.join(CAUSES)} のどれかにしてください")
    return problems


def _parse_history(record: dict[str, object]) -> tuple[tuple[HistoryEntry, ...], list[str]]:
    items, problems = _read_items(record, "history", layout.APPROVAL_FILE)
    entries: list[HistoryEntry] = []
    for index, item in enumerate(items):
        where = f"approval.json.history[{index}]"
        entry, found = _read_record(item, where)
        on, more = _read_text(entry, "on", where)
        kind, text = _read_text(entry, "kind", where)
        detail, note = _read_text(entry, "detail", where, required=False)
        test_changed, flag = _read_flag(entry, "test_changed", where)
        problems += found + more + text + note + flag
        entries.append(HistoryEntry(on=on, kind=kind, detail=detail, test_changed=test_changed))
    return tuple(entries), problems


def parse_approval(data: object) -> tuple[Approval, list[str]]:
    record, problems = _read_record(data, layout.APPROVAL_FILE)
    fields: dict[str, str] = {}
    for key in ("plan_sha", "dataset_sha", "test_sha", "skill_sha", "approved_on"):
        fields[key], found = _read_text(record, key, layout.APPROVAL_FILE)
        problems += found
    history, found = _parse_history(record)
    approval = Approval(
        plan_sha=fields["plan_sha"],
        dataset_sha=fields["dataset_sha"],
        test_sha=fields["test_sha"],
        skill_sha=fields["skill_sha"],
        approved_on=fields["approved_on"],
        history=history,
    )
    return approval, problems + found


def parse_split_record(data: object) -> tuple[SplitRecord, list[str]]:
    record, problems = _read_record(data, layout.SPLIT_FILE)
    plan_sha, found = _read_text(record, "plan_sha", layout.SPLIT_FILE)
    dataset_sha, more = _read_text(record, "dataset_sha", layout.SPLIT_FILE)
    splits, mapping = _read_record(record.get("splits"), "split.json.splits")
    pairs = tuple(sorted((key, value) for key, value in splits.items() if isinstance(value, str)))
    return SplitRecord(plan_sha, dataset_sha, pairs), problems + found + more + mapping


def parse_fixes(data: object) -> tuple[Fixes, list[str]]:
    record, problems = _read_record(data, layout.FIXES_FILE)
    applied, found = _read_names(record, "applied", layout.FIXES_FILE)
    rejected, more = _read_names(record, "rejected", layout.FIXES_FILE)
    return Fixes(applied=applied, rejected=rejected), problems + found + more


def parse_decision(data: object) -> tuple[DecisionRecord, list[str]]:
    record, problems = _read_record(data, layout.DECISION_FILE)
    number, found = _read_int(record, "round", layout.DECISION_FILE)
    current, more = _read_text(record, "current", layout.DECISION_FILE)
    candidate, text = _read_text(record, "candidate", layout.DECISION_FILE)
    adopted, flag = _read_flag(record, "adopted", layout.DECISION_FILE)
    reason, note = _read_text(record, "reason", layout.DECISION_FILE)
    problems += found + more + text + flag + note
    rates: dict[str, Fraction | None] = {}
    for key in ("train_before", "train_after", "val_before", "val_after"):
        rates[key], found = _read_rate(record, key, layout.DECISION_FILE)
        problems += found
    decision = DecisionRecord(
        round=number,
        current=current,
        candidate=candidate,
        adopted=adopted,
        reason=reason,
        train_before=rates["train_before"],
        train_after=rates["train_after"],
        val_before=rates["val_before"],
        val_after=rates["val_after"],
    )
    return decision, problems


def parse_applied(data: object) -> tuple[Applied, list[str]]:
    record, problems = _read_record(data, layout.APPLIED_FILE)
    applied, found = _read_flag(record, "applied", layout.APPLIED_FILE)
    version, more = _read_text(record, "version", layout.APPLIED_FILE)
    on, text = _read_text(record, "on", layout.APPLIED_FILE)
    return Applied(applied=applied, version=version, on=on), problems + found + more + text


def build_history_data(entry: HistoryEntry) -> dict[str, object]:
    return {"on": entry.on, "kind": entry.kind, "detail": entry.detail, "test_changed": entry.test_changed}


def build_approval_data(approval: Approval) -> dict[str, object]:
    return {
        "plan_sha": approval.plan_sha,
        "dataset_sha": approval.dataset_sha,
        "test_sha": approval.test_sha,
        "skill_sha": approval.skill_sha,
        "approved_on": approval.approved_on,
        "history": [build_history_data(entry) for entry in approval.history],
    }


def build_rate_data(rate: Fraction | None) -> str:
    return "" if rate is None else str(rate)


def build_decision_data(decision: DecisionRecord) -> dict[str, object]:
    return {
        "round": decision.round,
        "current": decision.current,
        "candidate": decision.candidate,
        "adopted": decision.adopted,
        "reason": decision.reason,
        "train_before": build_rate_data(decision.train_before),
        "train_after": build_rate_data(decision.train_after),
        "val_before": build_rate_data(decision.val_before),
        "val_after": build_rate_data(decision.val_after),
    }


def build_fixes_data(fixes: Fixes) -> dict[str, object]:
    return {"applied": list(fixes.applied), "rejected": list(fixes.rejected)}


def build_applied_data(applied: Applied) -> dict[str, object]:
    return {"applied": applied.applied, "version": applied.version, "on": applied.on}
