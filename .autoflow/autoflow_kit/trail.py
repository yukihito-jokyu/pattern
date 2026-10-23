"""実行の記録（trail.jsonl）の出来事の型と、記録と今の tree から次の段を決める状態機械を置く。

記録は追記だけで増やし、段の進み具合はここからだけ求める（STATE-01）。
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Callable

from autoflow_kit import policy, shape
from autoflow_kit.errors import StageError

# 段。次に実行するサブコマンドの組を表す
VERIFY = "verify"
PLAN = "plan"
DECIDE = "decide"
BUILD = "build"
RISK = "risk"
REVIEW = "review"
HANDOFF = "handoff"
COMMIT = "commit"
DONE = "done"
STOPPED = "stopped"
STEPS = (VERIFY, PLAN, DECIDE, BUILD, RISK, REVIEW, HANDOFF, COMMIT, DONE, STOPPED)

# 出来事の種類
STARTED = "started"
PROMPTED = "prompted"
PLANNED = "planned"
DECIDED = "decided"
BUILT = "built"
VERIFIED = "verified"
ESCALATED = "escalated"
RISKED = "risked"
REVIEWED = "reviewed"
HANDED_OFF = "handed_off"
COMMITTED = "committed"
INCIDENT = "incident"
EVENTS = (
    STARTED,
    PROMPTED,
    PLANNED,
    DECIDED,
    BUILT,
    VERIFIED,
    ESCALATED,
    RISKED,
    REVIEWED,
    HANDED_OFF,
    COMMITTED,
    INCIDENT,
)

# 実装の理由（build-new が実装役に渡す）
FIRST = "first"
REPRO = "repro"
FAILED = "failed"
FINDINGS = "findings"
HUMAN = "human"
REASONS = (FIRST, REPRO, FAILED, FINDINGS, HUMAN)

# 検査の種類（verify）。baseline は作業の前、repro は再現のテスト、check は実装の後
BASELINE = "baseline"
CHECK = "check"
MODES = (BASELINE, REPRO, CHECK)

# プロンプトを書いた役。contracts.AGENTS のキーと同じ
PLANNER = "planner"
BUILDER = "builder"
FINDER = "finder"
VERIFIER = "verifier"
RISK_ROLE = "risk"
ROLES = (PLANNER, BUILDER, FINDER, VERIFIER, RISK_ROLE)
MAX_NUMBER = 1_000_000


@dataclass(frozen=True)
class Origin:
    """依頼の出所。start の引数から作る。"""

    source: str
    ref: str
    url: str
    title: str


@dataclass(frozen=True)
class Event:
    """記録の1行。kind ごとに使う項目だけを持ち、他は既定値のまま書かない。"""

    kind: str
    at: str
    tree: str
    role: str = ""
    number: int = 0
    reason: str = ""
    mode: str = ""
    passed: bool = False
    repro: bool = False
    gate: str = ""
    choice: str = ""
    answer: str = ""
    who: str = ""
    reasons: tuple[str, ...] = ()
    tier: str = ""
    human_required: bool = False
    important: int = 0
    nit: int = 0
    pre_existing: int = 0
    text: str = ""
    source: str = ""
    ref: str = ""
    url: str = ""
    branch: str = ""
    commit: str = ""


@dataclass(frozen=True)
class Next:
    """次の段。number は今の段の番号（計画・実装・証拠・リスク・レビュー・報告書の n、H2 の関所の n）。"""

    step: str
    gate: str = ""
    why: str = ""
    reason: str = ""
    mode: str = ""
    number: int = 0
    prompted: str = ""
    prompted_tree: str = ""


@dataclass(frozen=True)
class _Memory:
    """状態機械が、計画ごとに覚えておくこと。"""

    repro: bool = False
    reproduced: bool = False
    risked: bool = False


def started(origin: Origin, branch: str, tree: str, now: str, *, head: str = "") -> Event:
    return Event(
        STARTED,
        now,
        tree,
        text=origin.title,
        source=origin.source,
        ref=origin.ref,
        url=origin.url,
        branch=branch,
        commit=head,
    )


def prompted(role: str, number: int, reason: str, tree: str, now: str) -> Event:
    return Event(PROMPTED, now, tree, role=role, number=number, reason=reason)


def planned(number: int, flow: policy.Flow, tree: str, now: str) -> Event:
    return Event(PLANNED, now, tree, number=number, repro=flow.repro, reasons=flow.h1_reasons, tier=flow.forecast_tier)


def decided(gate: str, choice: str, answer: str, tree: str, who: str, now: str) -> Event:
    """人の関所の決定。作ってよいのは deciding だけ（GATE-05）。"""
    return Event(DECIDED, now, tree, gate=gate, choice=choice, answer=answer, who=who)


def built(number: int, reason: str, blockers: tuple[str, ...], tree: str, now: str) -> Event:
    return Event(BUILT, now, tree, number=number, reason=reason, reasons=blockers)


def verified(number: int, mode: str, passed: bool, tree: str, now: str) -> Event:
    return Event(VERIFIED, now, tree, number=number, mode=mode, passed=passed)


def escalate(number: int, reasons: tuple[str, ...], tree: str, now: str) -> Event:
    """H2 の関所を起こす。reasons は policy.H2_RULES の id。"""
    return Event(ESCALATED, now, tree, number=number, gate=policy.H2, reasons=reasons)


def risked(number: int, tier: str, human_required: bool, reasons: tuple[str, ...], tree: str, now: str) -> Event:
    return Event(RISKED, now, tree, number=number, tier=tier, human_required=human_required, reasons=reasons)


def reviewed(number: int, counts: tuple[int, int, int], tree: str, now: str) -> Event:
    """counts は (Important, Nit, Pre-existing) の件数。"""
    important, nit, pre_existing = counts
    return Event(REVIEWED, now, tree, number=number, important=important, nit=nit, pre_existing=pre_existing)


def handed_off(number: int, tier: str, message: str, tree: str, now: str) -> Event:
    return Event(HANDED_OFF, now, tree, number=number, tier=tier, text=message)


def committed(commit: str, tree: str, now: str) -> Event:
    return Event(COMMITTED, now, tree, commit=commit)


def incident(text: str, tree: str, now: str) -> Event:
    return Event(INCIDENT, now, tree, text=text)


def encode(event: Event) -> str:
    """1行の JSON。既定値の項目は書かない。"""
    data = shape.to_data(event)
    defaults = shape.to_data(Event(event.kind, event.at, event.tree))
    kept = {key: value for key, value in data.items() if key in ("kind", "at", "tree") or value != defaults[key]}
    return json.dumps(kept, ensure_ascii=False)


def parse_event(value: object, where: str, problems: list[str]) -> Event:
    data = shape.as_object(value, where, problems)
    shape.unknown_keys(data, [field.name for field in dataclasses.fields(Event)], where, problems)

    def text(key: str) -> str:
        return shape.text(data, key, where, problems) if key in data else ""

    def number(key: str) -> int:
        return shape.integer(data, key, where, problems, bounds=(0, MAX_NUMBER)) if key in data else 0

    def boolean(key: str) -> bool:
        return shape.boolean(data, key, where, problems) if key in data else False

    return Event(
        kind=shape.choice(data, "kind", EVENTS, where, problems),
        at=shape.filled(data, "at", where, problems),
        tree=shape.text(data, "tree", where, problems),
        role=text("role"),
        number=number("number"),
        reason=text("reason"),
        mode=text("mode"),
        passed=boolean("passed"),
        repro=boolean("repro"),
        gate=text("gate"),
        choice=text("choice"),
        answer=text("answer"),
        who=text("who"),
        reasons=shape.texts(data, "reasons", where, problems) if "reasons" in data else (),
        tier=text("tier"),
        human_required=boolean("human_required"),
        important=number("important"),
        nit=number("nit"),
        pre_existing=number("pre_existing"),
        text=text("text"),
        source=text("source"),
        ref=text("ref"),
        url=text("url"),
        branch=text("branch"),
        commit=text("commit"),
    )


def parse_events(values: Sequence[object], problems: list[str]) -> tuple[Event, ...]:
    events = tuple(parse_event(value, f"{number} 行目", problems) for number, value in enumerate(values, 1))
    if not events or events[0].kind != STARTED:
        problems.append(f"最初の出来事は {STARTED} にする")
    return events


def last(events: Sequence[Event], kind: str) -> Event | None:
    return next((event for event in reversed(events) if event.kind == kind), None)


def count(events: Sequence[Event], kind: str) -> int:
    return sum(1 for event in events if event.kind == kind)


def since_last_build(events: Sequence[Event]) -> tuple[Event, ...]:
    """最後の実装より後の出来事。実装がまだ無ければ全部。"""
    index = max((i for i, event in enumerate(events) if event.kind == BUILT), default=-1)
    return tuple(events[index + 1 :])


def verified_tree(events: Sequence[Event]) -> str:
    """実装の後の検査が最後に通った tree。無ければ空。"""
    passed = [event for event in events if event.kind == VERIFIED and event.mode == CHECK and event.passed]
    return passed[-1].tree if passed else ""


def _is_reset(event: Event) -> bool:
    """H2 の数え直しの区切り。計画と、人が続けるか直すかを決めたとき。"""
    return event.kind == PLANNED or (event.kind == DECIDED and event.choice in (policy.CONTINUE, policy.CHANGES))


def progress(events: Sequence[Event]) -> policy.Progress:
    """最後の区切りからの、検査の失敗・Important の残ったレビュー・止まった理由（H2 の判定に使う）。"""
    start = max((i for i, event in enumerate(events) if _is_reset(event)), default=-1)
    recent = events[start + 1 :]
    failed = 0
    for event in recent:
        if event.kind == VERIFIED and event.mode != BASELINE:
            failed = 0 if event.passed else failed + 1
    rounds = sum(1 for event in recent if event.kind == REVIEWED and event.important > 0)
    build = last(recent, BUILT)
    return policy.Progress(failed, rounds, build.reasons if build else ())


def _build_start(memory: _Memory) -> Next:
    if memory.repro and not memory.reproduced:
        return Next(BUILD, reason=REPRO, why="不具合の修正では、先に再現のテストだけを書く")
    return Next(BUILD, reason=FIRST, why="計画どおりに実装する")


def _on_planned(event: Event, _memory: _Memory) -> tuple[Next, _Memory]:
    memory = _Memory(repro=event.repro)
    if event.reasons:
        return Next(DECIDE, gate=policy.H1, why="計画が H1 の条件に当たる"), memory
    return _build_start(memory), memory


def _on_decided(event: Event, memory: _Memory) -> tuple[Next, _Memory]:
    if event.choice == policy.ABORT:
        return Next(STOPPED, why="人が止めた"), memory
    if event.choice == policy.REPLAN:
        return Next(PLAN, why="人が計画のやり直しを選んだ"), memory
    if event.choice == policy.PROCEED:
        return _build_start(memory), memory
    if event.choice == policy.APPROVE:
        return Next(COMMIT, why="人が承認した"), memory
    return Next(BUILD, reason=HUMAN, why="人の回答を実装に反映する"), memory


def _on_baseline(event: Event, memory: _Memory) -> tuple[Next, _Memory]:
    if event.passed:
        return Next(PLAN, why="作業の前の検査が通った"), memory
    why = "作業の前から検査が落ちる。プロファイルの検査コマンドを直し、setup からやり直す"
    return Next(STOPPED, why=why), memory


def _on_repro(event: Event, memory: _Memory) -> tuple[Next, _Memory]:
    if event.passed:
        reproduced = dataclasses.replace(memory, reproduced=True)
        return _build_start(reproduced), reproduced
    return Next(BUILD, reason=REPRO, why="再現のテストが落ちなかった"), memory


def _on_verified(event: Event, memory: _Memory) -> tuple[Next, _Memory]:
    if event.mode == BASELINE:
        return _on_baseline(event, memory)
    if event.mode == REPRO:
        return _on_repro(event, memory)
    if not event.passed:
        return Next(BUILD, reason=FAILED, why="検査が落ちた"), memory
    if memory.risked:
        return Next(REVIEW, why="検査が通った"), memory
    return Next(RISK, why="検査が通った"), memory


def _on_reviewed(event: Event, memory: _Memory) -> tuple[Next, _Memory]:
    if event.important > 0:
        return Next(BUILD, reason=FINDINGS, why="レビューに Important が残った"), memory
    return Next(HANDOFF, why="レビューに Important が無い"), memory


def _on_risked(_event: Event, memory: _Memory) -> tuple[Next, _Memory]:
    return Next(REVIEW, why="リスクの段が決まった"), dataclasses.replace(memory, risked=True)


TRANSITIONS: dict[str, Callable[[Event, _Memory], tuple[Next, _Memory]]] = {
    STARTED: lambda _event, memory: (Next(VERIFY, mode=BASELINE, why="作業の前に検査が通るかを確かめる"), memory),
    PLANNED: _on_planned,
    DECIDED: _on_decided,
    BUILT: lambda event, memory: (Next(VERIFY, mode=REPRO if event.reason == REPRO else CHECK, why="実装した"), memory),
    VERIFIED: _on_verified,
    ESCALATED: lambda _event, memory: (Next(DECIDE, gate=policy.H2, why="H2 の条件に当たった"), memory),
    RISKED: _on_risked,
    REVIEWED: _on_reviewed,
    HANDED_OFF: lambda _event, memory: (Next(DECIDE, gate=policy.H3, why="報告書ができた"), memory),
    COMMITTED: lambda _event, memory: (Next(DONE, why="コミットした"), memory),
}


def _number(current: Next, events: Sequence[Event]) -> int:
    counted = {PLAN: PLANNED, BUILD: BUILT, VERIFY: VERIFIED, RISK: RISKED, REVIEW: REVIEWED, HANDOFF: HANDED_OFF}
    if current.step in counted:
        return count(events, counted[current.step]) + 1
    shown = {policy.H1: PLANNED, policy.H2: ESCALATED, policy.H3: HANDED_OFF}
    if current.step == DECIDE:
        return count(events, shown[current.gate])
    return 0


def _is_stale(current: Next, tree: str, events: Sequence[Event]) -> bool:
    """検査の後に作業ツリーが変わったか（GATE-04）。読み取りだけの役の途中は require_same_tree が見る（GATE-07）。"""
    if current.step in (RISK, REVIEW):
        return not current.prompted and tree != verified_tree(events)
    if current.step == HANDOFF or (current.step == DECIDE and current.gate == policy.H3):
        return tree != verified_tree(events)
    return False


def _is_unapproved(current: Next, tree: str, events: Sequence[Event]) -> bool:
    """承認の後に作業ツリーが変わったか（GATE-05）。承認は1つの tree だけに効く。"""
    approval = last(events, DECIDED)
    return current.step == COMMIT and (approval is None or approval.tree != tree)


def next_step(events: Sequence[Event], tree: str) -> Next:
    """記録と今の tree から次の段を求める。各段の入口は context.begin でこれと突き合わせる（GATE-03）。"""
    if not events or events[0].kind != STARTED:
        raise StageError(f"実行の記録が {STARTED} で始まっていません")
    current, memory, entered = Next(STOPPED), _Memory(), 0
    for index, event in enumerate(events):
        if event.kind in TRANSITIONS:
            current, memory = TRANSITIONS[event.kind](event, memory)
            entered = index
    asked = [event for event in events[entered + 1 :] if event.kind == PROMPTED]
    if asked:
        current = dataclasses.replace(current, prompted=asked[-1].role, prompted_tree=asked[-1].tree)
    if _is_stale(current, tree, events):
        current = Next(VERIFY, mode=CHECK, why="検査の後に作業ツリーが変わった")
    elif _is_unapproved(current, tree, events):
        current = Next(VERIFY, mode=CHECK, why="承認の後に作業ツリーが変わった")
    return dataclasses.replace(current, number=_number(current, events))
