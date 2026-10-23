"""plan.json と cases.json の形を定義し、検証する。問題は全部集めて返す。"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from tune_kit import checks, layout

# plan.json と cases.json の形の版。形を変えたら1上げる（PROC-06）
SCHEMA_VERSION = 1
REFERENCE = "reference"
CRITERIA = "criteria"
MODES = (REFERENCE, CRITERIA)
CASE_SANDBOX = "case"
REPO_SANDBOX = "repo"
SANDBOXES = (CASE_SANDBOX, REPO_SANDBOX)
TRAIN = "train"
VAL = "val"
TEST = "test"
SPLITS = (TRAIN, VAL, TEST)
MUST = "must"
SHOULD = "should"
SEVERITIES = (MUST, SHOULD)
DEFAULT_GROUP = "default"
DEFAULT_SEED = "skill-tune"
MIN_CASES = 3
RECOMMENDED_CASES = 10
CASE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
CHECK_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}")
# 予算の項目ごとの最小と最大
BUDGET_LIMITS = {"runs_per_case": (1, 5), "max_rounds": (1, 10), "patience": (1, 10), "parallel": (1, 10)}
CHECK_KEYS = ("id", "kind", "severity", "groups", "target", "value", "pattern", "expected_file", "run", "criterion")
CHECK_FLAGS = ("use_expected",)
CASE_KEYS = ("id", "group", "split", "prompt", "expected", "checks", "note")
PLAN_KEYS = ("schema_version", "target", "goal", "mode", "sandbox", "split", "checks", "budget")


@dataclass(frozen=True)
class Check:
    id: str
    kind: str
    severity: str
    groups: tuple[str, ...]
    target: str
    value: str
    pattern: str
    expected_file: str
    run: str
    criterion: str
    use_expected: bool


@dataclass(frozen=True)
class Case:
    """評価データの1件。expected が None なら正解を持たない（criteria モード）。"""

    id: str
    group: str
    split: str
    prompt: str
    expected: str | None
    checks: tuple[Check, ...]
    note: str


@dataclass(frozen=True)
class Target:
    id: str
    skill_path: str


@dataclass(frozen=True)
class SplitSpec:
    seed: str
    train: float
    val: float
    test: float


@dataclass(frozen=True)
class Budget:
    runs_per_case: int
    max_rounds: int
    patience: int
    parallel: int


@dataclass(frozen=True)
class Plan:
    schema_version: int
    target: Target
    goal: str
    mode: str
    sandbox: str
    split: SplitSpec
    checks: tuple[Check, ...]
    budget: Budget


def _read_record(data: object, where: str, keys: Sequence[str]) -> tuple[dict[str, object], list[str]]:
    if not isinstance(data, dict):
        return {}, [f"{where} はオブジェクトにしてください"]
    record = {str(key): value for key, value in data.items()}
    unknown = sorted(key for key in record if key not in keys)
    return record, [f"{where} に知らない項目 {key} があります（使える項目: {', '.join(keys)}）" for key in unknown]


def _read_text(record: dict[str, object], key: str, where: str, *, required: bool) -> tuple[str, list[str]]:
    value = record.get(key, "")
    if not isinstance(value, str):
        return "", [f"{where}.{key} は文字列にしてください"]
    if required and not value.strip():
        return value, [f"{where}.{key} が空です"]
    return value, []


def _read_number(record: dict[str, object], key: str, where: str) -> tuple[float, list[str]]:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0, [f"{where}.{key} は数にしてください"]
    return float(value), []


def _read_int(record: dict[str, object], key: str, where: str) -> tuple[int, list[str]]:
    value = record.get(key)
    low, high = BUDGET_LIMITS[key]
    if isinstance(value, bool) or not isinstance(value, int):
        return low, [f"{where}.{key} は整数にしてください"]
    if not low <= value <= high:
        return low, [f"{where}.{key} は {low} 以上 {high} 以下にしてください"]
    return value, []


def _read_names(record: dict[str, object], key: str, where: str) -> tuple[tuple[str, ...], list[str]]:
    value = record.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return (), [f"{where}.{key} は文字列の配列にしてください"]
    return tuple(str(item) for item in value), []


def is_safe_relative(path: str) -> bool:
    """sandbox や expected/ からの相対パスとして安全か（絶対パスと .. を許さない）。"""
    pure = PurePosixPath(path)
    return bool(path) and not pure.is_absolute() and ".." not in pure.parts and "\\" not in path


def _check_target(check: Check, where: str) -> list[str]:
    if check.target == checks.RESPONSE_TARGET:
        return []
    relative = check.target[len(checks.FILE_TARGET_PREFIX) :]
    if not check.target.startswith(checks.FILE_TARGET_PREFIX) or not is_safe_relative(relative):
        return [f"{where}.target は response か file:<sandbox からの相対パス> にしてください"]
    return []


def _check_fields(check: Check, kind: checks.Kind, where: str) -> list[str]:
    values = {
        "target": "" if check.target == checks.RESPONSE_TARGET else check.target,
        "value": check.value,
        "pattern": check.pattern,
        "expected_file": check.expected_file,
        "run": check.run,
        "criterion": check.criterion,
        "use_expected": "true" if check.use_expected else "",
    }
    problems = [f"{where}.{name} が空です（kind {kind.name} に必須）" for name in kind.required if not values[name]]
    allowed = set(kind.required) | set(kind.optional)
    problems += [
        f"{where}.{name} は kind {kind.name} では使えません"
        for name, value in values.items()
        if value and name not in allowed
    ]
    if check.pattern and not checks.is_valid_pattern(check.pattern):
        problems.append(f"{where}.pattern が正規表現として不正です")
    if check.expected_file and not is_safe_relative(check.expected_file):
        problems.append(f"{where}.expected_file は expected/ からの相対パスにしてください")
    return problems


def parse_check(data: object, where: str) -> tuple[Check | None, list[str]]:
    record, problems = _read_record(data, where, CHECK_KEYS + CHECK_FLAGS)
    if not record:
        return None, problems or [f"{where} が空です"]
    fields: dict[str, str] = {}
    for key in ("id", "kind", "severity"):
        fields[key], found = _read_text(record, key, where, required=True)
        problems += found
    for key in ("target", "value", "pattern", "expected_file", "run", "criterion"):
        fields[key], found = _read_text(record, key, where, required=False)
        problems += found
    groups, found = _read_names(record, "groups", where)
    problems += found
    use_expected = record.get("use_expected", False)
    if not isinstance(use_expected, bool):
        problems.append(f"{where}.use_expected は true か false にしてください")
    if fields["id"] and not CHECK_ID.fullmatch(fields["id"]):
        problems.append(f"{where}.id は英字で始まる英数字・_・-（32文字以内）にしてください")
    if fields["severity"] and fields["severity"] not in SEVERITIES:
        problems.append(f"{where}.severity は {' か '.join(SEVERITIES)} にしてください")
    kind = checks.KINDS.get(fields["kind"])
    if fields["kind"] and kind is None:
        problems.append(f"{where}.kind は {', '.join(checks.KINDS)} のどれかにしてください")
    check = Check(
        id=fields["id"],
        kind=fields["kind"],
        severity=fields["severity"],
        groups=groups,
        target=fields["target"] or checks.RESPONSE_TARGET,
        value=fields["value"],
        pattern=fields["pattern"],
        expected_file=fields["expected_file"],
        run=fields["run"],
        criterion=fields["criterion"],
        use_expected=use_expected is True,
    )
    if kind is not None:
        problems += _check_target(check, where) + _check_fields(check, kind, where)
    return (None if problems else check), problems


def _parse_checks(data: object, where: str) -> tuple[tuple[Check, ...], list[str]]:
    if not isinstance(data, list):
        return (), [f"{where} は配列にしてください"]
    parsed: list[Check] = []
    problems: list[str] = []
    for index, item in enumerate(data):
        check, found = parse_check(item, f"{where}[{index}]")
        problems += found
        if check is not None:
            parsed.append(check)
    return tuple(parsed), problems


def parse_case(data: object, where: str) -> tuple[Case | None, list[str]]:
    record, problems = _read_record(data, where, CASE_KEYS)
    if not record:
        return None, problems or [f"{where} が空です"]
    case_id, found = _read_text(record, "id", where, required=True)
    problems += found
    group, found = _read_text(record, "group", where, required=False)
    problems += found
    split, found = _read_text(record, "split", where, required=False)
    problems += found
    prompt, found = _read_text(record, "prompt", where, required=True)
    problems += found
    note, found = _read_text(record, "note", where, required=False)
    problems += found
    expected = record.get("expected")
    if expected is not None and not isinstance(expected, str):
        problems.append(f"{where}.expected は文字列か null にしてください")
    case_checks, found = _parse_checks(record.get("checks", []), f"{where}.checks")
    problems += found
    if case_id and not CASE_ID.fullmatch(case_id):
        problems.append(f"{where}.id は小文字の英数字とハイフン（64文字以内）にしてください")
    if group and not CASE_ID.fullmatch(group):
        problems.append(f"{where}.group は小文字の英数字とハイフン（64文字以内）にしてください")
    if split and split not in SPLITS:
        problems.append(f"{where}.split は空文字か {', '.join(SPLITS)} のどれかにしてください")
    problems += [
        f"{where}.checks の {check.id} に groups は書けません（計画の検査だけに書く）"
        for check in case_checks
        if check.groups
    ]
    case = Case(
        id=case_id,
        group=group or DEFAULT_GROUP,
        split=split,
        prompt=prompt,
        expected=expected if isinstance(expected, str) else None,
        checks=case_checks,
        note=note,
    )
    return (None if problems else case), problems


def parse_cases(data: object) -> tuple[tuple[Case, ...], list[str]]:
    record, problems = _read_record(data, layout.CASES_FILE, ("cases",))
    items = record.get("cases")
    if not isinstance(items, list):
        return (), [*problems, "cases.json の cases は配列にしてください"]
    parsed: list[Case] = []
    for index, item in enumerate(items):
        case, found = parse_case(item, f"cases[{index}]")
        problems += found
        if case is not None:
            parsed.append(case)
    return tuple(parsed), problems


def _parse_split(data: object) -> tuple[SplitSpec, list[str]]:
    record, problems = _read_record(data, "plan.split", ("seed", "ratios"))
    seed, found = _read_text(record, "seed", "plan.split", required=True)
    problems += found
    ratios, found = _read_record(record.get("ratios"), "plan.split.ratios", SPLITS)
    problems += found
    values: dict[str, float] = {}
    for name in SPLITS:
        values[name], found = _read_number(ratios, name, "plan.split.ratios")
        problems += found
    if not found and any(value <= 0 for value in values.values()):
        problems.append("plan.split.ratios の値は全部 0 より大きくしてください")
    if not math.isclose(sum(values.values()), 1.0, abs_tol=1e-9):
        problems.append("plan.split.ratios の合計を 1 にしてください")
    return SplitSpec(seed=seed, train=values[TRAIN], val=values[VAL], test=values[TEST]), problems


def _parse_budget(data: object) -> tuple[Budget, list[str]]:
    record, problems = _read_record(data, "plan.budget", tuple(BUDGET_LIMITS))
    numbers: dict[str, int] = {}
    for key in BUDGET_LIMITS:
        numbers[key], found = _read_int(record, key, "plan.budget")
        problems += found
    if numbers["patience"] > numbers["max_rounds"]:
        problems.append("plan.budget.patience は max_rounds 以下にしてください")
    budget = Budget(
        runs_per_case=numbers["runs_per_case"],
        max_rounds=numbers["max_rounds"],
        patience=numbers["patience"],
        parallel=numbers["parallel"],
    )
    return budget, problems


def _parse_target(data: object) -> tuple[Target, list[str]]:
    record, problems = _read_record(data, "plan.target", ("id", "skill_path"))
    target_id, found = _read_text(record, "id", "plan.target", required=True)
    problems += found
    skill_path, found = _read_text(record, "skill_path", "plan.target", required=True)
    problems += found
    return Target(id=target_id, skill_path=skill_path), problems


def parse_plan(data: object) -> tuple[Plan | None, list[str]]:
    record, problems = _read_record(data, layout.PLAN_FILE, PLAN_KEYS)
    missing = [key for key in PLAN_KEYS if key not in record]
    problems += [f"plan.json に {key} がありません" for key in missing]
    version = record.get("schema_version")
    if version != SCHEMA_VERSION:
        problems.append(f"plan.json の schema_version は {SCHEMA_VERSION} にしてください（今は {version}）")
    target, found = _parse_target(record.get("target"))
    problems += found
    goal, found = _read_text(record, "goal", "plan", required=True)
    problems += found
    mode, found = _read_text(record, "mode", "plan", required=True)
    problems += found
    if mode and mode not in MODES:
        problems.append(f"plan.mode は {' か '.join(MODES)} にしてください")
    sandbox, found = _read_text(record, "sandbox", "plan", required=True)
    problems += found
    if sandbox and sandbox not in SANDBOXES:
        problems.append(f"plan.sandbox は {' か '.join(SANDBOXES)} にしてください")
    split, found = _parse_split(record.get("split"))
    problems += found
    plan_checks, found = _parse_checks(record.get("checks", []), "plan.checks")
    problems += found
    budget, found = _parse_budget(record.get("budget"))
    problems += found
    model = Plan(SCHEMA_VERSION, target, goal, mode, sandbox, split, plan_checks, budget)
    return (None if problems else model), problems


def list_case_checks(model: Plan, case: Case) -> tuple[Check, ...]:
    """ケースに当てる検査。計画の検査（groups が空か、ケースの group を含むもの）の後にケースの検査を並べる。"""
    shared = tuple(check for check in model.checks if not check.groups or case.group in check.groups)
    return shared + case.checks


def _is_expected_used(check: Check) -> bool:
    if check.kind == "judge":
        return check.use_expected
    return check.kind in ("equals", "json_equals") and not check.value and not check.expected_file


def _check_case(model: Plan, case: Case) -> list[str]:
    where = f"ケース {case.id}"
    problems: list[str] = []
    applied = list_case_checks(model, case)
    ids = [check.id for check in applied]
    problems += [
        f"{where}: 検査の ID {check_id} が重複しています" for check_id in sorted({i for i in ids if ids.count(i) > 1})
    ]
    if not any(check.severity == MUST for check in applied):
        problems.append(f"{where}: severity が must の検査が1つもありません")
    if model.mode == REFERENCE and case.expected is None:
        problems.append(f"{where}: reference モードでは expected（正解）が要ります")
    if case.expected is None:
        problems += [
            f"{where}: 検査 {check.id} は正解を使うので expected が要ります"
            for check in applied
            if _is_expected_used(check)
        ]
    return problems


def check_dataset(model: Plan, cases: Sequence[Case]) -> list[str]:
    """計画とケースをまたぐ検査。ファイルの有無は見ない（workspace が見る）。"""
    problems: list[str] = []
    if len(cases) < MIN_CASES:
        problems.append(f"ケースは {MIN_CASES} 件以上にしてください（学習用・検証用・テスト用に1件ずつ要るため）")
    ids = [case.id for case in cases]
    problems += [f"ケースの ID {case_id} が重複しています" for case_id in sorted({i for i in ids if ids.count(i) > 1})]
    groups = {case.group for case in cases}
    for check in model.checks:
        problems += [
            f"計画の検査 {check.id} の groups の {name} を持つケースがありません"
            for name in check.groups
            if name not in groups
        ]
    if model.mode == CRITERIA and not any(check.kind == "judge" for check in model.checks):
        problems.append("criteria モードでは、計画の checks に kind judge の評価項目を1つ以上書いてください")
    for case in cases:
        problems += _check_case(model, case)
    return problems


def build_check_data(check: Check) -> dict[str, object]:
    """検査を JSON に書く形にする。既定値の項目は省く。"""
    data: dict[str, object] = {"id": check.id, "kind": check.kind, "severity": check.severity}
    if check.groups:
        data["groups"] = list(check.groups)
    if check.target != checks.RESPONSE_TARGET:
        data["target"] = check.target
    for key, value in (
        ("value", check.value),
        ("pattern", check.pattern),
        ("expected_file", check.expected_file),
        ("run", check.run),
        ("criterion", check.criterion),
    ):
        if value:
            data[key] = value
    if check.use_expected:
        data["use_expected"] = True
    return data


def build_case_data(case: Case) -> dict[str, object]:
    data: dict[str, object] = {"id": case.id, "group": case.group}
    if case.split:
        data["split"] = case.split
    data["prompt"] = case.prompt
    data["expected"] = case.expected
    if case.checks:
        data["checks"] = [build_check_data(check) for check in case.checks]
    if case.note:
        data["note"] = case.note
    return data


def build_plan_data(model: Plan) -> dict[str, object]:
    return {
        "schema_version": model.schema_version,
        "target": {"id": model.target.id, "skill_path": model.target.skill_path},
        "goal": model.goal,
        "mode": model.mode,
        "sandbox": model.sandbox,
        "split": {
            "seed": model.split.seed,
            "ratios": {TRAIN: model.split.train, VAL: model.split.val, TEST: model.split.test},
        },
        "checks": [build_check_data(check) for check in model.checks],
        "budget": {
            "runs_per_case": model.budget.runs_per_case,
            "max_rounds": model.budget.max_rounds,
            "patience": model.budget.patience,
            "parallel": model.budget.parallel,
        },
    }


def build_skeleton(target_id: str, skill_path: str) -> dict[str, object]:
    """init が書く plan.json のひな形。goal、mode、checks は人と決めて埋める。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "target": {"id": target_id, "skill_path": skill_path},
        "goal": "",
        "mode": "",
        "sandbox": CASE_SANDBOX,
        "split": {"seed": DEFAULT_SEED, "ratios": {TRAIN: 0.6, VAL: 0.2, TEST: 0.2}},
        "checks": [],
        "budget": {"runs_per_case": 1, "max_rounds": 3, "patience": 2, "parallel": 4},
    }
