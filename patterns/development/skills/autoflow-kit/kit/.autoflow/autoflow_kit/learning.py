"""学ぶ段（metrics、incident、learn）。全実行の記録から人の介入とガードレールを数え、見逃しの材料を並べる。

記事の「人の時間を最小にし、差し戻しとインシデントをガードレールにする」「見逃しは発生源を直す」に当たる。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from autoflow_kit import contracts, fsops, policy, render, trail, workspace
from autoflow_kit.errors import KitError, StageError
from autoflow_kit.layout import Layout

TOP = 10


def _outcome(events: Sequence[trail.Event]) -> str:
    if trail.last(events, trail.COMMITTED) is not None:
        return "コミット"
    if any(event.kind == trail.DECIDED and event.choice == policy.ABORT for event in events):
        return "中止"
    if any(event.kind == trail.VERIFIED and event.mode == trail.BASELINE and not event.passed for event in events):
        return "停止"
    return "途中"


def _loaded(where: Layout) -> tuple[list[tuple[str, tuple[trail.Event, ...]]], list[str]]:
    """読める実行の記録と、読めなかった実行の警告の行。"""
    found, warnings = [], []
    for run_id in workspace.runs(where):
        try:
            found.append((run_id, workspace.load_trail(where, run_id)))
        except KitError as exc:
            warnings.append(f"WARN 実行 {run_id} の記録を読めないので飛ばす: {exc.message.splitlines()[0]}")
    return found, warnings


def _row(run_id: str, events: Sequence[trail.Event]) -> list[str]:
    decisions = [event for event in events if event.kind == trail.DECIDED]
    first_h3 = next((event for event in decisions if event.gate == policy.H3), None)
    return [
        run_id,
        _outcome(events),
        render.number(len(decisions)),
        first_h3.choice if first_h3 is not None else render.MISSING,
        render.number(trail.count(events, trail.REVIEWED)),
        render.number(trail.count(events, trail.ESCALATED)),
        render.number(trail.count(events, trail.INCIDENT)),
    ]


def metrics(where: Layout) -> str:
    runs, warnings = _loaded(where)
    all_events = [event for _run_id, events in runs for event in events]
    decisions = [event for event in all_events if event.kind == trail.DECIDED]
    firsts = [
        next((e for e in events if e.kind == trail.DECIDED and e.gate == policy.H3), None) for _id, events in runs
    ]
    judged = [event for event in firsts if event is not None]
    approved = sum(1 for event in judged if event.choice == policy.APPROVE)
    by_gate = Counter(event.gate for event in decisions)
    summary = [
        ["実行", render.number(len(runs))],
        ["コミットした実行", render.number(sum(1 for _id, events in runs if _outcome(events) == "コミット"))],
        ["人の決定（全関所）", render.number(len(decisions))],
        *[[f"人の決定（{gate.id}）", render.number(by_gate[gate.id])] for gate in policy.GATES if gate.id != policy.H0],
        ["最初の H3 で承認された割合", render.percent(approved, len(judged))],
        [
            "差し戻し（H3 の changes）",
            render.number(sum(1 for e in decisions if e.gate == policy.H3 and e.choice == policy.CHANGES)),
        ],
        ["中止", render.number(sum(1 for e in decisions if e.choice == policy.ABORT))],
        ["インシデント", render.number(sum(1 for e in all_events if e.kind == trail.INCIDENT))],
    ]
    headers = ["実行", "結果", "人の決定", "最初の H3", "レビューのラウンド", policy.H2, "インシデント"]
    return "\n".join(
        [
            "# 指標",
            "",
            render.table(["指標", "値"], summary),
            "",
            "## 実行ごと",
            "",
            render.table(headers, [_row(run_id, events) for run_id, events in runs]),
            *warnings,
        ]
    )


def incident(where: Layout, run_id: str, text: str, now: str) -> str:
    events = workspace.load_trail(where, run_id)
    done = trail.last(events, trail.COMMITTED)
    if done is None:
        raise StageError(f"実行 {run_id} はコミットしていません。インシデントはコミットした実行にだけ記録する")
    if not text.strip():
        raise StageError("--text に、後で見つかった問題を書く")
    fsops.append_line(where.trail_path(run_id), trail.encode(trail.incident(text, done.tree, now)))
    return f"記録した: 実行 {run_id} のインシデント"


def _findings(where: Layout, runs: Sequence[tuple[str, Sequence[trail.Event]]]) -> list[tuple[str, str, str]]:
    """(実行, バグの種類, 指摘の1行)。Pre-existing は除く。"""
    found = []
    for run_id, events in runs:
        for number in range(1, trail.count(events, trail.REVIEWED) + 1):
            for item in workspace.load_result(where, run_id, number).kept:
                if item.tag != policy.PRE_EXISTING:
                    found.append((run_id, item.finding.bug_class, f"{item.finding.title}（{item.finding.file}）"))
    return found


def _declined(where: Layout, runs: Sequence[tuple[str, Sequence[trail.Event]]]) -> list[str]:
    return [
        f"{run_id} {resolution.finding_id}: {resolution.reason}"
        for run_id, events in runs
        for attempt in range(1, trail.count(events, trail.BUILT) + 1)
        for resolution in workspace.load_report(where, run_id, attempt).resolutions
        if resolution.status == contracts.DECLINED
    ]


def learn(where: Layout) -> str:
    runs, warnings = _loaded(where)
    findings = _findings(where, runs)
    classes = Counter(bug_class for _run, bug_class, _line in findings)
    class_rows = [
        [bug_class, render.number(total), "; ".join(line for _r, c, line in findings if c == bug_class)[:200]]
        for bug_class, total in classes.most_common(TOP)
    ]
    requests = [
        f"{run_id} {event.gate} {event.choice}: {event.answer}"
        for run_id, events in runs
        for event in events
        if event.kind == trail.DECIDED and event.choice in (policy.CHANGES, policy.CONTINUE, policy.REPLAN)
    ]
    stuck = Counter(
        reason for _id, events in runs for event in events if event.kind == trail.ESCALATED for reason in event.reasons
    )
    incidents = [
        f"{run_id}: {event.text}" for run_id, events in runs for event in events if event.kind == trail.INCIDENT
    ]
    return "\n".join(
        [
            "# 学ぶための材料",
            "",
            "## 繰り返したバグの種類",
            "",
            render.table(["バグの種類", "件数", "例"], class_rows),
            "",
            "## 退けた指摘",
            "",
            render.bullets(_declined(where, runs)),
            "",
            "## 人の直してほしいこと（H1・H2・H3 の回答）",
            "",
            render.bullets(requests),
            "",
            "## H2 に当たった条件",
            "",
            render.table(
                ["条件", "回数"],
                [[policy.rule_text(rule), render.number(total)] for rule, total in stuck.most_common()],
            ),
            "",
            "## インシデント",
            "",
            render.bullets(incidents),
            *warnings,
        ]
    )
