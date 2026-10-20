"""補助 CLI とサブエージェントが受け渡す JSON（plan、exec、facts、grade、proposal、scores など）の形を定める。"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

from forge_kit import shape
from forge_kit.errors import InvalidFileError

AGENTS = {
    "designer": "forge-designer",
    "builder": "forge-builder",
    "grader": "forge-grader",
    "analyst": "forge-analyst",
}
RECOMMENDATIONS = ("adopt", "reject")
CHANGES = ("better", "worse", "same", "unknown")
SHA256 = r"[0-9a-f]{64}"
ISO_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
# 分析役が失敗を分ける原因。S1〜S5 はバンドルを直し、S6 は charter の見直しを人に提案し、S7 は受け入れる
CAUSES = {
    "S1": ("手順が無い", "その場面の手順が SKILL.md に無い。手順を足す"),
    "S2": (
        "手順があいまい",
        "手順はあるが実行ごとに解釈が分かれた。条件と答えで書き直し、分かれた実例を悪い例にする",
    ),
    "S3": (
        "役の分け方・道具が合わない",
        "役の受け持ちが重なるか抜けている、または道具が足りない・多すぎる。役と tools を直す",
    ),
    "S4": (
        "受け渡しが足りない",
        "サブエージェントに渡す情報か、返してもらう形が決まっていない。起動のプロンプトと返す形を書く",
    ),
    "S5": ("確かめる手順が無い", "誤りが残ったまま終えた。検査を回す手順か、確かめる役を足す"),
    "S6": (
        "評価の側の問題",
        "課題文・受け入れ条件・指標・実行の条件の側に不備がある。バンドルは直さず、charter の見直しを人に提案する",
    ),
    "S7": ("害の無い揺れ", "結果と保守性に影響しない違い。受け入れて記録する"),
}
BUNDLE_CAUSES = ("S1", "S2", "S3", "S4", "S5")
OBSERVATION_CAUSES = ("S6", "S7")


@dataclass(frozen=True)
class DesignApproval:
    sha256: str
    approved_on: str


@dataclass(frozen=True)
class BundleCheck:
    """bundle-check が通ったときの下書きと設計のハッシュ。install はこの下書きだけを入れる。"""

    draft_sha256: str
    design_sha256: str


@dataclass(frozen=True)
class Installation:
    skill_name: str
    design_sha256: str
    files: tuple[str, ...]
    installed_on: str


@dataclass(frozen=True)
class Run:
    run_id: str
    task_id: str
    agent_no: int


@dataclass(frozen=True)
class Plan:
    slot: str
    variant: str
    round_no: int
    charter_sha256: str
    skill_name: str
    bundle_source: str
    runs: tuple[Run, ...]


@dataclass(frozen=True)
class Execution:
    """execute が書く、1回の実行役の起動の結果。"""

    run_id: str
    exit_code: int
    timed_out: bool


@dataclass(frozen=True)
class GradeTarget:
    key: str
    text: str


@dataclass(frozen=True)
class Facts:
    """collect が機械で集めた1つの実行の事実。check_exit は検査を回さなかったとき None。"""

    run_id: str
    task_id: str
    completed: bool
    timed_out: bool
    changed_files: tuple[str, ...]
    check_exit: int | None
    check_tail: str
    protected_changed: tuple[str, ...]
    launches: tuple[str, ...]
    edits_main: int
    edits_sub: int
    max_depth: int
    cost_usd: float | None
    duration_sec: float | None
    denials: tuple[str, ...]
    grade_targets: tuple[GradeTarget, ...]


@dataclass(frozen=True)
class GradeItem:
    key: str
    met: bool
    evidence: str


@dataclass(frozen=True)
class Grade:
    run_id: str
    items: tuple[GradeItem, ...]


@dataclass(frozen=True)
class Change:
    id: str
    cause: str
    metrics: tuple[str, ...]
    evidence: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Observation:
    cause: str
    summary: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Proposal:
    changes: tuple[Change, ...]
    observations: tuple[Observation, ...]


@dataclass(frozen=True)
class TaskValue:
    task_id: str
    value: float | None


@dataclass(frozen=True)
class MetricScore:
    id: str
    name: str
    priority: str
    direction: str
    threshold: float
    value: float | None
    met: bool
    by_task: tuple[TaskValue, ...]


@dataclass(frozen=True)
class RunNote:
    run_id: str
    task_id: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Scores:
    slot: str
    variant: str
    round_no: int
    charter_sha256: str
    metrics: tuple[MetricScore, ...]
    holdout_metrics: tuple[MetricScore, ...]
    run_notes: tuple[RunNote, ...]

    @property
    def all_must_met(self) -> bool:
        return all(score.met for score in self.metrics if score.priority == "must")


@dataclass(frozen=True)
class CompareRow:
    id: str
    name: str
    priority: str
    direction: str
    threshold: float
    baseline: float | None
    candidate: float | None
    change: str
    candidate_met: bool


@dataclass(frozen=True)
class Comparison:
    round_no: int
    baseline_slot: str
    candidate_slot: str
    rows: tuple[CompareRow, ...]
    recommendation: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    round_no: int
    adopted: bool
    decided_on: str


def to_data(value: Any) -> dict[str, Any]:
    return dataclasses.asdict(value)


def _finish(source: str, problems: list[str]) -> None:
    if problems:
        raise InvalidFileError(source, problems)


def _optional_real(data: dict[str, object], key: str, where: str, problems: list[str]) -> float | None:
    return None if data.get(key) is None else shape.real(data, key, where, problems)


def parse_design_approval(data: object, source: str) -> DesignApproval:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    shape.unknown_keys(root, ("sha256", "approved_on"), "", problems)
    approval = DesignApproval(
        sha256=shape.text(root, "sha256", "", problems, pattern=SHA256),
        approved_on=shape.text(root, "approved_on", "", problems, pattern=ISO_DATE),
    )
    _finish(source, problems)
    return approval


def parse_bundle_check(data: object, source: str) -> BundleCheck:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    check = BundleCheck(
        draft_sha256=shape.text(root, "draft_sha256", "", problems, pattern=SHA256),
        design_sha256=shape.text(root, "design_sha256", "", problems, pattern=SHA256),
    )
    _finish(source, problems)
    return check


def parse_installation(data: object, source: str) -> Installation:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    installation = Installation(
        skill_name=shape.filled(root, "skill_name", "", problems),
        design_sha256=shape.text(root, "design_sha256", "", problems, pattern=SHA256),
        files=shape.texts(root, "files", "", problems),
        installed_on=shape.text(root, "installed_on", "", problems, pattern=ISO_DATE),
    )
    _finish(source, problems)
    return installation


def parse_plan(data: object, source: str) -> Plan:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    runs = tuple(
        Run(
            run_id=shape.filled(item, "run_id", where, problems),
            task_id=shape.filled(item, "task_id", where, problems),
            agent_no=shape.integer(item, "agent_no", where, problems, bounds=(1, 99)),
        )
        for where, item in shape.objects(root, "runs", "", problems)
    )
    plan = Plan(
        slot=shape.filled(root, "slot", "", problems),
        variant=shape.filled(root, "variant", "", problems),
        round_no=shape.integer(root, "round_no", "", problems, bounds=(0, 99)),
        charter_sha256=shape.filled(root, "charter_sha256", "", problems),
        skill_name=shape.filled(root, "skill_name", "", problems),
        bundle_source=shape.filled(root, "bundle_source", "", problems),
        runs=runs,
    )
    _finish(source, problems)
    return plan


def parse_execution(data: object, source: str) -> Execution:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    execution = Execution(
        run_id=shape.filled(root, "run_id", "", problems),
        exit_code=shape.integer(root, "exit_code", "", problems, bounds=(-255, 255)),
        timed_out=shape.boolean(root, "timed_out", "", problems),
    )
    _finish(source, problems)
    return execution


def parse_facts(data: object, source: str) -> Facts:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    check_exit = root.get("check_exit")
    if check_exit is not None and (not isinstance(check_exit, int) or isinstance(check_exit, bool)):
        problems.append("check_exit は整数か null にしてください")
    targets = tuple(
        GradeTarget(shape.filled(item, "key", where, problems), shape.filled(item, "text", where, problems))
        for where, item in shape.objects(root, "grade_targets", "", problems)
    )
    facts = Facts(
        run_id=shape.filled(root, "run_id", "", problems),
        task_id=shape.filled(root, "task_id", "", problems),
        completed=shape.boolean(root, "completed", "", problems),
        timed_out=shape.boolean(root, "timed_out", "", problems),
        changed_files=shape.texts(root, "changed_files", "", problems),
        check_exit=check_exit if isinstance(check_exit, int) else None,
        check_tail=shape.text(root, "check_tail", "", problems),
        protected_changed=shape.texts(root, "protected_changed", "", problems),
        launches=shape.texts(root, "launches", "", problems),
        edits_main=shape.integer(root, "edits_main", "", problems, bounds=(0, 100000)),
        edits_sub=shape.integer(root, "edits_sub", "", problems, bounds=(0, 100000)),
        max_depth=shape.integer(root, "max_depth", "", problems, bounds=(0, 99)),
        cost_usd=_optional_real(root, "cost_usd", "", problems),
        duration_sec=_optional_real(root, "duration_sec", "", problems),
        denials=shape.texts(root, "denials", "", problems),
        grade_targets=targets,
    )
    _finish(source, problems)
    return facts


def parse_grade(data: object, source: str, *, run_id: str, keys: tuple[str, ...]) -> Grade:
    """採点役が書いた grade.json を検証する。判定する項目のキーは、プロンプトで渡した keys と完全に一致させる。"""
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    shape.unknown_keys(root, ("run_id", "items"), "", problems)
    if shape.text(root, "run_id", "", problems) != run_id:
        problems.append(f"run_id は {run_id} にしてください")
    items = []
    for where, item in shape.objects(root, "items", "", problems):
        shape.unknown_keys(item, ("key", "met", "evidence"), where, problems)
        items.append(
            GradeItem(
                key=shape.filled(item, "key", where, problems),
                met=shape.boolean(item, "met", where, problems),
                evidence=shape.filled(item, "evidence", where, problems),
            )
        )
    found = tuple(item.key for item in items)
    if found != keys:
        problems.append(
            f"items の key は次の順で全部書いてください: {', '.join(keys) or '（なし）'}（今: {', '.join(found)}）"
        )
    grade = Grade(run_id, tuple(items))
    _finish(source, problems)
    return grade


def parse_proposal(data: object, source: str, *, metric_ids: tuple[str, ...]) -> Proposal:
    """分析役が書いた proposal.json を検証する。変更は S1〜S5、所見は S6・S7 に分ける。"""
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    shape.unknown_keys(root, ("changes", "observations"), "", problems)
    changes = []
    for where, item in shape.objects(root, "changes", "", problems):
        shape.unknown_keys(item, ("id", "cause", "metrics", "evidence", "summary"), where, problems)
        change = Change(
            id=shape.text(item, "id", where, problems, pattern=r"P[1-9][0-9]*"),
            cause=shape.choice(item, "cause", BUNDLE_CAUSES, where, problems),
            metrics=shape.texts(item, "metrics", where, problems),
            evidence=shape.texts(item, "evidence", where, problems),
            summary=shape.filled(item, "summary", where, problems),
        )
        problems += [
            f"{where}.metrics の {m} は charter の指標にありません" for m in change.metrics if m not in metric_ids
        ]
        if not change.metrics or not change.evidence:
            problems.append(f"{where} には、効かせたい指標（metrics）と根拠（evidence）を1件以上書いてください")
        changes.append(change)
    observations = []
    for where, item in shape.objects(root, "observations", "", problems):
        shape.unknown_keys(item, ("cause", "summary", "evidence"), where, problems)
        observations.append(
            Observation(
                cause=shape.choice(item, "cause", OBSERVATION_CAUSES, where, problems),
                summary=shape.filled(item, "summary", where, problems),
                evidence=shape.texts(item, "evidence", where, problems),
            )
        )
    for change_id in shape.duplicates(change.id for change in changes):
        problems.append(f"changes の id {change_id} が重複しています")
    proposal = Proposal(tuple(changes), tuple(observations))
    _finish(source, problems)
    return proposal


def _metric_scores(root: dict[str, object], key: str, problems: list[str]) -> tuple[MetricScore, ...]:
    scores = []
    for where, item in shape.objects(root, key, "", problems):
        by_task = tuple(
            TaskValue(shape.filled(value, "task_id", path, problems), _optional_real(value, "value", path, problems))
            for path, value in shape.objects(item, "by_task", where, problems)
        )
        scores.append(
            MetricScore(
                id=shape.filled(item, "id", where, problems),
                name=shape.filled(item, "name", where, problems),
                priority=shape.filled(item, "priority", where, problems),
                direction=shape.filled(item, "direction", where, problems),
                threshold=shape.real(item, "threshold", where, problems),
                value=_optional_real(item, "value", where, problems),
                met=shape.boolean(item, "met", where, problems),
                by_task=by_task,
            )
        )
    return tuple(scores)


def parse_scores(data: object, source: str) -> Scores:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    notes = tuple(
        RunNote(
            shape.filled(item, "run_id", where, problems),
            shape.filled(item, "task_id", where, problems),
            shape.texts(item, "notes", where, problems),
        )
        for where, item in shape.objects(root, "run_notes", "", problems)
    )
    scores = Scores(
        slot=shape.filled(root, "slot", "", problems),
        variant=shape.filled(root, "variant", "", problems),
        round_no=shape.integer(root, "round_no", "", problems, bounds=(0, 99)),
        charter_sha256=shape.filled(root, "charter_sha256", "", problems),
        metrics=_metric_scores(root, "metrics", problems),
        holdout_metrics=_metric_scores(root, "holdout_metrics", problems),
        run_notes=notes,
    )
    _finish(source, problems)
    return scores


def parse_comparison(data: object, source: str) -> Comparison:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    rows = tuple(
        CompareRow(
            id=shape.filled(item, "id", where, problems),
            name=shape.filled(item, "name", where, problems),
            priority=shape.filled(item, "priority", where, problems),
            direction=shape.filled(item, "direction", where, problems),
            threshold=shape.real(item, "threshold", where, problems),
            baseline=_optional_real(item, "baseline", where, problems),
            candidate=_optional_real(item, "candidate", where, problems),
            change=shape.choice(item, "change", CHANGES, where, problems),
            candidate_met=shape.boolean(item, "candidate_met", where, problems),
        )
        for where, item in shape.objects(root, "rows", "", problems)
    )
    comparison = Comparison(
        round_no=shape.integer(root, "round_no", "", problems, bounds=(1, 99)),
        baseline_slot=shape.filled(root, "baseline_slot", "", problems),
        candidate_slot=shape.filled(root, "candidate_slot", "", problems),
        rows=rows,
        recommendation=shape.choice(root, "recommendation", RECOMMENDATIONS, "", problems),
        reasons=shape.texts(root, "reasons", "", problems),
    )
    _finish(source, problems)
    return comparison


def parse_decision(data: object, source: str) -> Decision:
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    decision = Decision(
        round_no=shape.integer(root, "round_no", "", problems, bounds=(1, 99)),
        adopted=shape.boolean(root, "adopted", "", problems),
        decided_on=shape.filled(root, "decided_on", "", problems),
    )
    _finish(source, problems)
    return decision
