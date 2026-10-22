"""段とサブエージェントが受け渡す JSON の型と検証、サブエージェントの名前を定義する。

サブエージェントが書く JSON（計画、実装の報告、指摘、投票、リスクの判定）と、補助 CLI が書いて段どうしで
受け渡す JSON（証拠、レビューの候補と結果）を扱う。形を変えたら、書かせるひな形と tests/support.py も変える（PROC-02）。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from autoflow_kit import shape

# 役の名前と、配布するサブエージェントの名前（kit/claude/agents/<名前>.md）
AGENTS = {
    "planner": "autoflow-planner",
    "builder": "autoflow-builder",
    "finder": "autoflow-finder",
    "verifier": "autoflow-verifier",
    "risk": "autoflow-risk",
}
LOW_IMPACT = "low"
HIGH_IMPACT = "high"
IMPACTS = (LOW_IMPACT, HIGH_IMPACT)
FIXED = "fixed"
DECLINED = "declined"
STATUSES = (FIXED, DECLINED)
REAL = "real"
NOT_REAL = "not_real"
VERDICTS = (REAL, NOT_REAL)
COMMAND = "command"
REVIEW = "review"
HUMAN = "human"
CHECKS = (COMMAND, REVIEW, HUMAN)
MODES = ("baseline", "repro", "check")
CRITERION_ID = r"C[0-9]+"
CANDIDATE_ID = r"R[0-9]+-[0-9]+"
MAX_LINE = 10_000_000
MAX_CODE = 255


@dataclass(frozen=True)
class Criterion:
    id: str
    text: str
    check: str
    run: str


@dataclass(frozen=True)
class Question:
    question: str
    default: str
    impact: str


@dataclass(frozen=True)
class Plan:
    kind: str
    goal: str
    non_goals: tuple[str, ...]
    scope: tuple[str, ...]
    criteria: tuple[Criterion, ...]
    repro: str
    root_cause: str
    open_questions: tuple[Question, ...]
    dependencies_to_add: tuple[str, ...]
    revert: str
    commit_subject: str


@dataclass(frozen=True)
class Resolution:
    finding_id: str
    status: str
    reason: str
    locations: tuple[str, ...]


@dataclass(frozen=True)
class BuildReport:
    summary: str
    explanation: str
    resolutions: tuple[Resolution, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    title: str
    file: str
    line: int
    category: str
    evidence: str
    bug_class: str
    other_locations: tuple[str, ...]
    pre_existing: bool


@dataclass(frozen=True)
class Candidate:
    """review-collect が重複をまとめた指摘。検証役はこの id ごとに投票する。"""

    id: str
    lenses: tuple[str, ...]
    finding: Finding


@dataclass(frozen=True)
class Vote:
    id: str
    verdict: str
    tag: str
    reason: str


@dataclass(frozen=True)
class Kept:
    """投票で残った指摘。tag は本物と投票した検証役の多数の重大度。"""

    id: str
    tag: str
    real_votes: int
    voters: int
    lenses: tuple[str, ...]
    finding: Finding


@dataclass(frozen=True)
class ReviewResult:
    round_no: int
    tree: str
    base: str
    depth: str
    kept: tuple[Kept, ...]
    dropped: tuple[str, ...]


@dataclass(frozen=True)
class RiskJudgment:
    tier: str
    human_required: bool
    reasons: tuple[str, ...]
    attention_files: tuple[str, ...]


@dataclass(frozen=True)
class CheckResult:
    id: str
    run: str
    exit_code: int
    timed_out: bool
    log: str


@dataclass(frozen=True)
class Evidence:
    """verify が実行した検査の結果。tree は実行したときの作業ツリーの版（GATE-04）。"""

    seq: int
    tree: str
    mode: str
    passed: bool
    results: tuple[CheckResult, ...]


def parse_plan(value: object, kinds: Iterable[str], problems: list[str]) -> Plan:
    data = shape.as_object(value, "", problems)
    keys = (
        "kind",
        "goal",
        "non_goals",
        "scope",
        "criteria",
        "repro",
        "root_cause",
        "open_questions",
        "dependencies_to_add",
        "revert",
        "commit_subject",
    )
    shape.unknown_keys(data, keys, "", problems)
    subject = shape.filled(data, "commit_subject", "", problems)
    if "\n" in subject:
        problems.append("commit_subject は1行にする")
    return Plan(
        kind=shape.choice(data, "kind", kinds, "", problems),
        goal=shape.filled(data, "goal", "", problems),
        non_goals=shape.texts(data, "non_goals", "", problems),
        scope=_nonempty_texts(data, "scope", problems),
        criteria=_parse_criteria(data, problems),
        repro=shape.text(data, "repro", "", problems),
        root_cause=shape.text(data, "root_cause", "", problems),
        open_questions=tuple(
            _parse_question(where, item, problems) for where, item in _objects(data, "open_questions", problems)
        ),
        dependencies_to_add=shape.texts(data, "dependencies_to_add", "", problems),
        revert=shape.filled(data, "revert", "", problems),
        commit_subject=subject,
    )


def _objects(data: dict[str, object], key: str, problems: list[str]) -> list[tuple[str, dict[str, object]]]:
    return shape.objects(data, key, "", problems)


def _nonempty_texts(data: dict[str, object], key: str, problems: list[str]) -> tuple[str, ...]:
    values = shape.texts(data, key, "", problems)
    if isinstance(data.get(key), list) and not values:
        problems.append(f"{key} が空です。1つ以上書く")
    return values


def _parse_criteria(data: dict[str, object], problems: list[str]) -> tuple[Criterion, ...]:
    criteria = []
    for where, item in shape.objects(data, "criteria", "", problems):
        shape.unknown_keys(item, ("id", "text", "check", "run"), where, problems)
        criterion = Criterion(
            id=shape.text(item, "id", where, problems, pattern=CRITERION_ID),
            text=shape.filled(item, "text", where, problems),
            check=shape.choice(item, "check", CHECKS, where, problems),
            run=shape.text(item, "run", where, problems),
        )
        if criterion.check == COMMAND and not criterion.run.strip():
            problems.append(f"{where}.run が空です。check が command なら、確かめるコマンドを書く")
        if criterion.check != COMMAND and criterion.run:
            problems.append(f"{where}.run は check が command のときだけ書く")
        criteria.append(criterion)
    if isinstance(data.get("criteria"), list) and not criteria:
        problems.append("criteria が空です。受け入れ条件を1つ以上書く")
    for repeated in shape.duplicates(criterion.id for criterion in criteria):
        problems.append(f"criteria の id {repeated!r} が重なっています")
    return tuple(criteria)


def _parse_question(where: str, item: dict[str, object], problems: list[str]) -> Question:
    shape.unknown_keys(item, ("question", "default", "impact"), where, problems)
    return Question(
        question=shape.filled(item, "question", where, problems),
        default=shape.filled(item, "default", where, problems),
        impact=shape.choice(item, "impact", IMPACTS, where, problems),
    )


def parse_report(value: object, problems: list[str]) -> BuildReport:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("summary", "explanation", "resolutions", "blockers"), "", problems)
    resolutions = []
    for where, item in shape.objects(data, "resolutions", "", problems):
        shape.unknown_keys(item, ("finding_id", "status", "reason", "locations"), where, problems)
        resolution = Resolution(
            finding_id=shape.text(item, "finding_id", where, problems, pattern=CANDIDATE_ID),
            status=shape.choice(item, "status", STATUSES, where, problems),
            reason=shape.text(item, "reason", where, problems),
            locations=shape.texts(item, "locations", where, problems),
        )
        if resolution.status == DECLINED and not resolution.reason.strip():
            problems.append(f"{where}.reason が空です。退けるなら理由を書く")
        resolutions.append(resolution)
    for repeated in shape.duplicates(resolution.finding_id for resolution in resolutions):
        problems.append(f"resolutions の finding_id {repeated!r} が重なっています")
    return BuildReport(
        summary=shape.filled(data, "summary", "", problems),
        explanation=shape.filled(data, "explanation", "", problems),
        resolutions=tuple(resolutions),
        blockers=shape.texts(data, "blockers", "", problems),
    )


def parse_findings(value: object, categories: Iterable[str], problems: list[str]) -> tuple[Finding, ...]:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("findings",), "", problems)
    options = tuple(categories)
    return tuple(_parse_finding(where, item, options, problems) for where, item in _objects(data, "findings", problems))


def _parse_finding(where: str, item: dict[str, object], categories: tuple[str, ...], problems: list[str]) -> Finding:
    keys = ("title", "file", "line", "category", "evidence", "bug_class", "other_locations", "pre_existing")
    shape.unknown_keys(item, keys, where, problems)
    return Finding(
        title=shape.filled(item, "title", where, problems),
        file=shape.filled(item, "file", where, problems),
        line=shape.integer(item, "line", where, problems, bounds=(1, MAX_LINE)),
        category=shape.choice(item, "category", categories, where, problems),
        evidence=shape.filled(item, "evidence", where, problems),
        bug_class=shape.filled(item, "bug_class", where, problems),
        other_locations=shape.texts(item, "other_locations", where, problems),
        pre_existing=shape.boolean(item, "pre_existing", where, problems),
    )


def parse_candidates(value: object, categories: Iterable[str], problems: list[str]) -> tuple[Candidate, ...]:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("candidates",), "", problems)
    options = tuple(categories)
    found = []
    for where, item in shape.objects(data, "candidates", "", problems):
        shape.unknown_keys(item, ("id", "lenses", "finding"), where, problems)
        found.append(
            Candidate(
                id=shape.text(item, "id", where, problems, pattern=CANDIDATE_ID),
                lenses=shape.texts(item, "lenses", where, problems),
                finding=_parse_finding(
                    f"{where}.finding",
                    shape.as_object(item.get("finding"), f"{where}.finding", problems),
                    options,
                    problems,
                ),
            )
        )
    return tuple(found)


def parse_votes(value: object, ids: Iterable[str], tags: Iterable[str], problems: list[str]) -> tuple[Vote, ...]:
    """投票。候補の id ごとにちょうど1票を求める。"""
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("votes",), "", problems)
    options = tuple(tags)
    votes = []
    for where, item in shape.objects(data, "votes", "", problems):
        shape.unknown_keys(item, ("id", "verdict", "tag", "reason"), where, problems)
        votes.append(
            Vote(
                id=shape.text(item, "id", where, problems, pattern=CANDIDATE_ID),
                verdict=shape.choice(item, "verdict", VERDICTS, where, problems),
                tag=shape.choice(item, "tag", options, where, problems),
                reason=shape.filled(item, "reason", where, problems),
            )
        )
    expected = set(ids)
    voted = [vote.id for vote in votes]
    for missing in sorted(expected - set(voted)):
        problems.append(f"候補 {missing} への票がありません")
    for extra in sorted(set(voted) - expected):
        problems.append(f"候補に無い id {extra} への票があります")
    for repeated in shape.duplicates(voted):
        problems.append(f"候補 {repeated} への票が2つ以上あります")
    return tuple(votes)


def parse_result(value: object, categories: Iterable[str], problems: list[str]) -> ReviewResult:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("round_no", "tree", "base", "depth", "kept", "dropped"), "", problems)
    options = tuple(categories)
    kept = []
    for where, item in shape.objects(data, "kept", "", problems):
        shape.unknown_keys(item, ("id", "tag", "real_votes", "voters", "lenses", "finding"), where, problems)
        kept.append(
            Kept(
                id=shape.text(item, "id", where, problems, pattern=CANDIDATE_ID),
                tag=shape.filled(item, "tag", where, problems),
                real_votes=shape.integer(item, "real_votes", where, problems, bounds=(0, MAX_LINE)),
                voters=shape.integer(item, "voters", where, problems, bounds=(0, MAX_LINE)),
                lenses=shape.texts(item, "lenses", where, problems),
                finding=_parse_finding(
                    f"{where}.finding",
                    shape.as_object(item.get("finding"), f"{where}.finding", problems),
                    options,
                    problems,
                ),
            )
        )
    return ReviewResult(
        round_no=shape.integer(data, "round_no", "", problems, bounds=(1, MAX_LINE)),
        tree=shape.filled(data, "tree", "", problems),
        base=shape.filled(data, "base", "", problems),
        depth=shape.filled(data, "depth", "", problems),
        kept=tuple(kept),
        dropped=shape.texts(data, "dropped", "", problems),
    )


def parse_judgment(value: object, tiers: Iterable[str], problems: list[str]) -> RiskJudgment:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("tier", "human_required", "reasons", "attention_files"), "", problems)
    judgment = RiskJudgment(
        tier=shape.choice(data, "tier", tiers, "", problems),
        human_required=shape.boolean(data, "human_required", "", problems),
        reasons=shape.texts(data, "reasons", "", problems),
        attention_files=shape.texts(data, "attention_files", "", problems),
    )
    if isinstance(data.get("reasons"), list) and not judgment.reasons:
        problems.append("reasons が空です。段を選んだ理由を1つ以上書く")
    return judgment


def parse_evidence(value: object, problems: list[str]) -> Evidence:
    data = shape.as_object(value, "", problems)
    shape.unknown_keys(data, ("seq", "tree", "mode", "passed", "results"), "", problems)
    results = []
    for where, item in shape.objects(data, "results", "", problems):
        shape.unknown_keys(item, ("id", "run", "exit_code", "timed_out", "log"), where, problems)
        results.append(
            CheckResult(
                id=shape.filled(item, "id", where, problems),
                run=shape.filled(item, "run", where, problems),
                exit_code=shape.integer(item, "exit_code", where, problems, bounds=(-MAX_CODE, MAX_CODE)),
                timed_out=shape.boolean(item, "timed_out", where, problems),
                log=shape.filled(item, "log", where, problems),
            )
        )
    return Evidence(
        seq=shape.integer(data, "seq", "", problems, bounds=(1, MAX_LINE)),
        tree=shape.filled(data, "tree", "", problems),
        mode=shape.choice(data, "mode", MODES, "", problems),
        passed=shape.boolean(data, "passed", "", problems),
        results=tuple(results),
    )
