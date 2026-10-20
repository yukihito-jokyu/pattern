"""設計（対象スキルの役・手順・人の関所・報告の形）のモデルと検証、承認のハッシュを扱う。

設計役が design.json を書く。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from forge_kit import bundle, shape
from forge_kit.errors import InvalidFileError

SCHEMA_VERSION = 1
TOP_KEYS = ("schema_version", "skill_name", "summary", "roles", "steps", "checkpoints", "report")
ORCHESTRATOR = "orchestrator"
STEP_ID = r"S[1-9][0-9]*"
REPORT_BOUNDS = (1, 12)


@dataclass(frozen=True)
class Role:
    role: str
    purpose: str
    tools: tuple[str, ...]
    input: str
    output: str


@dataclass(frozen=True)
class Step:
    """手順の1項目。actor は orchestrator（メインのセッション）か、役の名前。"""

    id: str
    actor: str
    action: str
    parallel: bool


@dataclass(frozen=True)
class Checkpoint:
    step: str
    question: str
    default: str


@dataclass(frozen=True)
class Design:
    schema_version: int
    skill_name: str
    summary: str
    roles: tuple[Role, ...]
    steps: tuple[Step, ...]
    checkpoints: tuple[Checkpoint, ...]
    report: tuple[str, ...]


def parse(data: object, source: str, *, skill_name: str) -> Design:
    """design.json の中身を検証してモデルにする。skill_name は charter の target.skill_name。"""
    problems: list[str] = []
    root = shape.as_object(data, "", problems)
    shape.unknown_keys(root, TOP_KEYS, "", problems)
    summary = shape.filled(root, "summary", "", problems)
    if "\n" in summary:
        problems.append("summary は1行にしてください（SKILL.md の description になる）")
    design = Design(
        schema_version=shape.integer(root, "schema_version", "", problems, bounds=(SCHEMA_VERSION, SCHEMA_VERSION)),
        skill_name=shape.filled(root, "skill_name", "", problems),
        summary=summary,
        roles=_roles(root, problems),
        steps=_steps(root, problems),
        checkpoints=_checkpoints(root, problems),
        report=shape.texts(root, "report", "", problems),
    )
    if design.skill_name and design.skill_name != skill_name:
        problems.append(f"skill_name を charter の target.skill_name（{skill_name}）と同じにしてください")
    if not REPORT_BOUNDS[0] <= len(design.report) <= REPORT_BOUNDS[1]:
        problems.append(f"report には報告に書く項目を {REPORT_BOUNDS[0]}〜{REPORT_BOUNDS[1]} 個書いてください")
    if not problems:
        _check_relations(design, problems)
    if problems:
        raise InvalidFileError(source, problems)
    return design


def _roles(root: dict[str, object], problems: list[str]) -> tuple[Role, ...]:
    roles = []
    for where, data in shape.objects(root, "roles", "", problems):
        shape.unknown_keys(data, ("role", "purpose", "tools", "input", "output"), where, problems)
        tools = shape.texts(data, "tools", where, problems)
        extra = [tool for tool in tools if tool not in bundle.AGENT_TOOLS]
        if not tools or extra:
            problems.append(f"{where}.tools は {', '.join(bundle.AGENT_TOOLS)} から1つ以上選んでください")
        if bundle.has_hidden_search(tools):
            problems.append(f"{where}.tools に Bash と Glob・Grep を一緒に入れないでください")
        roles.append(
            Role(
                role=shape.text(data, "role", where, problems, pattern=bundle.ROLE_PATTERN),
                purpose=shape.filled(data, "purpose", where, problems),
                tools=tools,
                input=shape.filled(data, "input", where, problems),
                output=shape.filled(data, "output", where, problems),
            )
        )
    low, high = bundle.AGENTS_BOUNDS
    if not low <= len(roles) <= high:
        problems.append(f"roles は {low}〜{high} 個にしてください（今: {len(roles)}）")
    for role in shape.duplicates(role.role for role in roles):
        problems.append(f"roles の role {role} が重複しています")
    return tuple(roles)


def _steps(root: dict[str, object], problems: list[str]) -> tuple[Step, ...]:
    steps = []
    for where, data in shape.objects(root, "steps", "", problems):
        shape.unknown_keys(data, ("id", "actor", "action", "parallel"), where, problems)
        steps.append(
            Step(
                id=shape.text(data, "id", where, problems, pattern=STEP_ID),
                actor=shape.filled(data, "actor", where, problems),
                action=shape.filled(data, "action", where, problems),
                parallel=shape.boolean(data, "parallel", where, problems),
            )
        )
    low, high = bundle.STEPS_BOUNDS
    if not low <= len(steps) <= high:
        problems.append(f"steps は {low}〜{high} 個にしてください（今: {len(steps)}）")
    return tuple(steps)


def _checkpoints(root: dict[str, object], problems: list[str]) -> tuple[Checkpoint, ...]:
    found = []
    for where, data in shape.objects(root, "checkpoints", "", problems):
        shape.unknown_keys(data, ("step", "question", "default"), where, problems)
        found.append(
            Checkpoint(
                step=shape.text(data, "step", where, problems, pattern=STEP_ID),
                question=shape.filled(data, "question", where, problems),
                default=shape.filled(data, "default", where, problems),
            )
        )
    return tuple(found)


def _check_relations(design: Design, problems: list[str]) -> None:
    """手順の番号、手順の担い手と役、人の関所と手順の対応を確かめる。"""
    expected = [f"S{number}" for number in range(1, len(design.steps) + 1)]
    if [step.id for step in design.steps] != expected:
        problems.append(f"steps の id は S1 から順に振ってください（{', '.join(expected)}）")
    roles = {role.role for role in design.roles}
    for step in design.steps:
        if step.actor != ORCHESTRATOR and step.actor not in roles:
            problems.append(
                f"手順 {step.id} の actor は {ORCHESTRATOR} か roles の役にしてください（今: {step.actor}）"
            )
    used = {step.actor for step in design.steps}
    problems += [f"役 {role} を担い手にする手順がありません" for role in sorted(roles - used)]
    steps = {step.id: step for step in design.steps}
    for checkpoint in design.checkpoints:
        found = steps.get(checkpoint.step)
        if found is None:
            problems.append(f"人の関所の step {checkpoint.step} が steps にありません")
        elif found.actor != ORCHESTRATOR:
            problems.append(
                f"人の関所の手順 {found.id} は {ORCHESTRATOR} の手順にしてください（サブエージェントは人に聞けない）"
            )


def roles_tools(design: Design) -> dict[str, tuple[str, ...]]:
    return {role.role: role.tools for role in design.roles}


def digest(data: object) -> str:
    """design.json の中身のハッシュ。承認の後に変えると一致しなくなる。"""
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
