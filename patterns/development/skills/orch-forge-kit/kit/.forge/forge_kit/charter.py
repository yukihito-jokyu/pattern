"""charter（人と合意したゴール・指標・評価課題・環境・実行の条件・予算・承認）のモデルと検証、承認のハッシュを扱う。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from forge_kit import catalog, shape
from forge_kit.errors import InvalidFileError

SCHEMA_VERSION = 1
TOP_KEYS = (
    "schema_version",
    "target",
    "purpose",
    "goals",
    "metrics",
    "environment",
    "executor",
    "tasks",
    "budget",
    "approval",
)
NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
GOAL_ID = r"G[1-9][0-9]*"
TASK_ID = r"[TH][1-9][0-9]*"
HOLDOUT_PREFIX = "H"
KIT_PREFIX = "forge-"
SHA256 = r"[0-9a-f]{64}"
ISO_DATE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
AGENTS_BOUNDS = (1, 10)
ROUNDS_BOUNDS = (1, 10)
CHECK_TIMEOUT_BOUNDS = (10, 7200)
EXECUTOR_TIMEOUT_BOUNDS = (60, 7200)
PARALLEL_BOUNDS = (1, 20)
BUDGET_USD_MAX = 100.0
DEFAULT_AGENTS = 3
DEFAULT_MAX_ROUNDS = 3
DEFAULT_CHECK_TIMEOUT_SEC = 600
DEFAULT_EXECUTOR_TIMEOUT_SEC = 1800
DEFAULT_PARALLEL = 3
DEFAULT_BUDGET_USD = 3.0
ACCEPTANCE_KEY = "acceptance"
STEP_KEY = "step"
REPORT_KEY = "report"
REPORT_CRITERION = "最後の返答が、SKILL.md の `## 報告` の定め（書く項目と順序）に従っている"


@dataclass(frozen=True)
class Target:
    id: str
    skill_name: str


@dataclass(frozen=True)
class Goal:
    id: str
    statement: str
    metrics: tuple[str, ...]


@dataclass(frozen=True)
class MetricChoice:
    """charter で選んだ指標。criterion は独自の指標（custom_<n>）だけが持つ。"""

    id: str
    threshold: float
    priority: str
    criterion: str


@dataclass(frozen=True)
class Environment:
    check_command: str
    check_timeout_sec: int
    protected_paths: tuple[str, ...]
    skip_dirs: tuple[str, ...]
    link_dirs: tuple[str, ...]


@dataclass(frozen=True)
class Executor:
    """実行役（claude -p）の条件。model が空なら Claude Code の既定のモデルを使う。"""

    model: str
    allowed_tools: tuple[str, ...]
    max_budget_usd: float
    timeout_sec: int
    parallel: int


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    acceptance: tuple[str, ...]


@dataclass(frozen=True)
class Budget:
    agents: int
    max_rounds: int


@dataclass(frozen=True)
class Approval:
    sha256: str
    approved_on: str


@dataclass(frozen=True)
class Charter:
    schema_version: int
    target: Target
    purpose: str
    goals: tuple[Goal, ...]
    metrics: tuple[MetricChoice, ...]
    environment: Environment
    executor: Executor
    tasks: tuple[Task, ...]
    budget: Budget
    approval: Approval | None


def parse(data: object, source: str) -> Charter:
    """charter.json の中身を検証してモデルにする。問題は全部集めてから InvalidFileError にする。"""
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    shape.unknown_keys(root, TOP_KEYS, "", problems)
    charter = Charter(
        schema_version=shape.integer(root, "schema_version", "", problems, bounds=(SCHEMA_VERSION, SCHEMA_VERSION)),
        target=_target(root, problems),
        purpose=shape.filled(root, "purpose", "", problems),
        goals=_goals(root, problems),
        metrics=_metrics(root, problems),
        environment=_environment(root, problems),
        executor=_executor(root, problems),
        tasks=_tasks(root, problems),
        budget=_budget(root, problems),
        approval=_approval(root, problems),
    )
    if not problems:
        _check_relations(charter, problems)
    if problems:
        raise InvalidFileError(source, problems)
    return charter


def _target(root: dict[str, object], problems: list[str]) -> Target:
    data = shape.as_object(root.get("target"), "target", problems)
    shape.unknown_keys(data, ("id", "skill_name"), "target", problems)
    skill_name = shape.text(data, "skill_name", "target", problems, pattern=NAME)
    if skill_name.startswith(KIT_PREFIX):
        problems.append(f"target.skill_name は {KIT_PREFIX} で始めないでください（この道具のスキルと区別するため）")
    return Target(id=shape.text(data, "id", "target", problems, pattern=NAME), skill_name=skill_name)


def _goals(root: dict[str, object], problems: list[str]) -> tuple[Goal, ...]:
    goals = []
    for where, data in shape.objects(root, "goals", "", problems):
        shape.unknown_keys(data, ("id", "statement", "metrics"), where, problems)
        goals.append(
            Goal(
                id=shape.text(data, "id", where, problems, pattern=GOAL_ID),
                statement=shape.filled(data, "statement", where, problems),
                metrics=shape.texts(data, "metrics", where, problems),
            )
        )
    if not goals:
        problems.append("goals が空です。人と決めたゴールを1件以上書いてください")
    for goal_id in shape.duplicates(goal.id for goal in goals):
        problems.append(f"goals の id {goal_id} が重複しています")
    return tuple(goals)


def _metrics(root: dict[str, object], problems: list[str]) -> tuple[MetricChoice, ...]:
    choices = []
    for where, data in shape.objects(root, "metrics", "", problems):
        shape.unknown_keys(data, ("id", "threshold", "priority", "criterion"), where, problems)
        metric_id = shape.filled(data, "id", where, problems)
        custom = catalog.is_custom(metric_id)
        criterion = shape.filled(data, "criterion", where, problems) if custom else ""
        if not custom and "criterion" in data:
            problems.append(f"{where}.criterion は独自の指標（custom_<番号>）にだけ書きます")
        if not custom and metric_id and catalog.find(metric_id) is None:
            names = ", ".join(metric.id for metric in catalog.METRICS)
            problems.append(f"{where}.id {metric_id!r} はカタログにありません（{names}、custom_<番号>）")
        choice = MetricChoice(
            id=metric_id,
            threshold=shape.real(data, "threshold", where, problems),
            priority=shape.choice(data, "priority", catalog.PRIORITIES, where, problems),
            criterion=criterion,
        )
        _check_threshold(choice, where, problems)
        choices.append(choice)
    if not choices:
        problems.append("metrics が空です。人と決めた指標を1件以上書いてください")
    elif all(choice.priority != "must" for choice in choices):
        problems.append(
            "metrics に priority が must の指標が1件もありません。終わりの判定に使う指標を must にしてください"
        )
    for metric_id in shape.duplicates(choice.id for choice in choices):
        problems.append(f"metrics の id {metric_id} が重複しています")
    return tuple(choices)


def _check_threshold(choice: MetricChoice, where: str, problems: list[str]) -> None:
    metric = None if catalog.is_custom(choice.id) else catalog.find(choice.id)
    upper = catalog.RATE_MAX if metric is None else metric.max_value
    if choice.threshold < 0 or (upper is not None and choice.threshold > upper):
        limit = "0 以上" if upper is None else f"0 以上 {upper} 以下"
        problems.append(f"{where}.threshold は {limit} にしてください（今: {choice.threshold}）")


def _environment(root: dict[str, object], problems: list[str]) -> Environment:
    where = "environment"
    data = shape.as_object(root.get(where), where, problems)
    keys = ("check_command", "check_timeout_sec", "protected_paths", "skip_dirs", "link_dirs")
    shape.unknown_keys(data, keys, where, problems)
    return Environment(
        check_command=shape.text(data, "check_command", where, problems),
        check_timeout_sec=shape.integer(data, "check_timeout_sec", where, problems, bounds=CHECK_TIMEOUT_BOUNDS),
        protected_paths=shape.texts(data, "protected_paths", where, problems),
        skip_dirs=shape.texts(data, "skip_dirs", where, problems),
        link_dirs=shape.texts(data, "link_dirs", where, problems),
    )


def _executor(root: dict[str, object], problems: list[str]) -> Executor:
    where = "executor"
    data = shape.as_object(root.get(where), where, problems)
    shape.unknown_keys(data, ("model", "allowed_tools", "max_budget_usd", "timeout_sec", "parallel"), where, problems)
    budget = shape.real(data, "max_budget_usd", where, problems)
    if not 0 < budget <= BUDGET_USD_MAX:
        problems.append(f"{where}.max_budget_usd は 0 より大きく {BUDGET_USD_MAX} 以下にしてください（今: {budget}）")
    return Executor(
        model=shape.text(data, "model", where, problems, pattern=r"[A-Za-z0-9.\[\]_-]*"),
        allowed_tools=shape.texts(data, "allowed_tools", where, problems),
        max_budget_usd=budget,
        timeout_sec=shape.integer(data, "timeout_sec", where, problems, bounds=EXECUTOR_TIMEOUT_BOUNDS),
        parallel=shape.integer(data, "parallel", where, problems, bounds=PARALLEL_BOUNDS),
    )


def _tasks(root: dict[str, object], problems: list[str]) -> tuple[Task, ...]:
    tasks = []
    for where, data in shape.objects(root, "tasks", "", problems):
        shape.unknown_keys(data, ("id", "prompt", "acceptance"), where, problems)
        tasks.append(
            Task(
                id=shape.text(data, "id", where, problems, pattern=TASK_ID),
                prompt=shape.filled(data, "prompt", where, problems),
                acceptance=shape.texts(data, "acceptance", where, problems),
            )
        )
    for task_id in shape.duplicates(task.id for task in tasks):
        problems.append(f"tasks の id {task_id} が重複しています")
    return tuple(tasks)


def _budget(root: dict[str, object], problems: list[str]) -> Budget:
    data = shape.as_object(root.get("budget"), "budget", problems)
    shape.unknown_keys(data, ("agents", "max_rounds"), "budget", problems)
    return Budget(
        agents=shape.integer(data, "agents", "budget", problems, bounds=AGENTS_BOUNDS),
        max_rounds=shape.integer(data, "max_rounds", "budget", problems, bounds=ROUNDS_BOUNDS),
    )


def _approval(root: dict[str, object], problems: list[str]) -> Approval | None:
    if root.get("approval") is None:
        return None
    data = shape.as_object(root.get("approval"), "approval", problems)
    shape.unknown_keys(data, ("sha256", "approved_on"), "approval", problems)
    return Approval(
        sha256=shape.text(data, "sha256", "approval", problems, pattern=SHA256),
        approved_on=shape.text(data, "approved_on", "approval", problems, pattern=ISO_DATE),
    )


def _check_relations(charter: Charter, problems: list[str]) -> None:
    """項目どうしの関係（ゴールと指標の対応、指標の前提、評価課題）を確かめる。"""
    _check_goals(charter, problems)
    _check_prerequisites(charter, problems)


def _check_goals(charter: Charter, problems: list[str]) -> None:
    chosen = {choice.id for choice in charter.metrics}
    referenced: set[str] = set()
    for goal in charter.goals:
        if not goal.metrics:
            problems.append(f"ゴール {goal.id} に指標がありません。測る指標を1つ以上結び付けてください")
        for metric_id in goal.metrics:
            referenced.add(metric_id)
            if metric_id not in chosen:
                problems.append(f"ゴール {goal.id} の指標 {metric_id} が metrics にありません")
    for metric_id in sorted(chosen - referenced):
        problems.append(f"指標 {metric_id} がどのゴールにも結び付いていません")


def _check_prerequisites(charter: Charter, problems: list[str]) -> None:
    chosen = {choice.id for choice in charter.metrics}
    if not visible_tasks(charter):
        problems.append("tasks に、ホールドアウト（H<番号>）ではない課題（T<番号>）を1件以上書いてください")
    if "check_pass" in chosen and not charter.environment.check_command.strip():
        problems.append("check_pass を使うには environment.check_command が要ります")
    if "protected_untouched" in chosen and not charter.environment.protected_paths:
        problems.append("protected_untouched を使うには environment.protected_paths が要ります")
    if "acceptance" in chosen:
        for task in charter.tasks:
            if not task.acceptance:
                problems.append(f"acceptance を使うには、課題 {task.id} の acceptance が1件以上要ります")
    if chosen & catalog.AGREEMENT_METRICS and charter.budget.agents < 2:
        problems.append("一致度の指標は2人以上を比べるため、budget.agents を 2 以上にしてください")


def is_holdout(task_id: str) -> bool:
    return task_id.startswith(HOLDOUT_PREFIX)


def visible_tasks(charter: Charter) -> tuple[Task, ...]:
    return tuple(task for task in charter.tasks if not is_holdout(task.id))


def slot_tasks(charter: Charter, *, include_holdout: bool) -> tuple[Task, ...]:
    return charter.tasks if include_holdout else visible_tasks(charter)


def definition(choice: MetricChoice) -> catalog.Metric:
    if catalog.is_custom(choice.id):
        return catalog.custom_metric(choice.id, choice.criterion)
    metric = catalog.find(choice.id)
    if metric is None:
        raise InvalidFileError("charter", [f"指標 {choice.id} がカタログにありません"])
    return metric


def has_grader_items(charter: Charter) -> bool:
    return any(definition(choice).method == "grader" for choice in charter.metrics)


def grade_items(charter: Charter, task_id: str, steps: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """採点役が1つの実行について判定する項目の（キー, 判定の条件）。steps は SKILL.md の `## 手順` の項目。"""
    chosen = {choice.id for choice in charter.metrics}
    items: list[tuple[str, str]] = []
    task = next(task for task in charter.tasks if task.id == task_id)
    if "acceptance" in chosen:
        items += [(f"{ACCEPTANCE_KEY}:{number}", text) for number, text in enumerate(task.acceptance, 1)]
    if "flow_conformance" in chosen:
        items += [(f"{STEP_KEY}:{number}", text) for number, text in enumerate(steps, 1)]
    if "report_format" in chosen:
        items.append((REPORT_KEY, REPORT_CRITERION))
    items += [(choice.id, choice.criterion) for choice in charter.metrics if catalog.is_custom(choice.id)]
    return tuple(items)


def fragments(charter: Charter, min_chars: int) -> frozenset[str]:
    """評価課題の文（課題文と受け入れ条件の行）。スキルに写すと、課題にだけ効く改善（過剰適合）になる。"""
    texts: list[str] = []
    for task in charter.tasks:
        texts += [task.prompt, *task.acceptance]
    return frozenset(line.strip() for text in texts for line in text.splitlines() if len(line.strip()) >= min_chars)


def skeleton(target_id: str, skill_name: str) -> dict[str, object]:
    """対話の出発点になる charter。推奨の指標を既定の閾値で並べ、人と決める項目は空にしておく。"""
    metrics = [
        {"id": metric.id, "threshold": metric.default_threshold, "priority": "must"}
        for metric in catalog.METRICS
        if metric.recommended
    ]
    environment = {
        "check_command": "",
        "check_timeout_sec": DEFAULT_CHECK_TIMEOUT_SEC,
        "protected_paths": [],
        "skip_dirs": [],
        "link_dirs": [],
    }
    executor = {
        "model": "",
        "allowed_tools": [],
        "max_budget_usd": DEFAULT_BUDGET_USD,
        "timeout_sec": DEFAULT_EXECUTOR_TIMEOUT_SEC,
        "parallel": DEFAULT_PARALLEL,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "target": {"id": target_id, "skill_name": skill_name},
        "purpose": "",
        "goals": [],
        "metrics": metrics,
        "environment": environment,
        "executor": executor,
        "tasks": [],
        "budget": {"agents": DEFAULT_AGENTS, "max_rounds": DEFAULT_MAX_ROUNDS},
        "approval": None,
    }


def digest(data: dict[str, object]) -> str:
    """approval を除いた中身のハッシュ。承認の後に1文字でも変えると一致しなくなる。"""
    body = {key: value for key, value in data.items() if key != "approval"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def approval_state(data: dict[str, object], charter: Charter) -> str:
    """approved（承認済みで変更なし）、unapproved（未承認）、stale（承認の後に変えた）のどれか。"""
    if charter.approval is None:
        return "unapproved"
    return "approved" if charter.approval.sha256 == digest(data) else "stale"
