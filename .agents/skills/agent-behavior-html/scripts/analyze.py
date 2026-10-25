"""Build an offline HTML report from v1 metadata and v2 operation/purpose logs."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from event_model import (
    INTENT_EVENT, INTENT_MAX_AGE_SEC, MAX_EVENTS, MAX_LOG_BYTES, MAX_LOG_LINE_BYTES, TOOL_EVENTS,
    parse_time, script_json, validate_event,
)

TEMPLATE = Path(__file__).resolve().parent.parent / "assets/dashboard.html"
MAX_DIAGNOSTICS = 100


def input_files(paths: list) -> list:
    files = set()
    for path in paths:
        if any(part.startswith(".env") for part in path.parts):
            raise ValueError("ERR-02 environment files are not log inputs")
        if path.is_symlink():
            raise ValueError("ERR-02 symlink input refused")
        candidates = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
        for candidate in candidates:
            if any(part.startswith(".env") for part in candidate.parts):
                raise ValueError("ERR-02 environment files are not log inputs")
            if candidate.is_symlink() or candidate.suffix != ".jsonl" or not candidate.is_file():
                raise ValueError("ERR-02 regular JSONL input required")
            files.add(candidate.resolve())
    if not files:
        raise ValueError("ERR-02 no JSONL files found")
    result = sorted(files)
    if sum(path.stat().st_size for path in result) > MAX_LOG_BYTES:
        raise ValueError("ERR-02 total log size exceeds 64 MiB")
    return result


def load_events(paths: list) -> tuple[list, dict, dict]:
    events, locations, diagnostics = [], {}, []
    invalid_lines, duplicate_events, blank_lines = 0, 0, 0
    files = input_files(paths)
    total_bytes = 0
    for file_index, path in enumerate(files, 1):
        with path.open("rb") as stream:
            line_number = 0
            while True:
                raw = stream.readline(MAX_LOG_LINE_BYTES + 1)
                if not raw:
                    break
                line_number += 1
                total_bytes += len(raw)
                oversized = len(raw) > MAX_LOG_LINE_BYTES
                if oversized:
                    while raw and not raw.endswith(b"\n"):
                        raw = stream.readline(MAX_LOG_LINE_BYTES + 1)
                        total_bytes += len(raw)
                if total_bytes > MAX_LOG_BYTES:
                    raise ValueError("ERR-02 growing input exceeds 64 MiB")
                location = {"file": str(file_index) + ":" + path.name, "line": line_number}
                if not oversized and not raw.strip():
                    blank_lines += 1
                    continue
                try:
                    if oversized:
                        raise ValueError("ERR-02 oversized log line")
                    event = json.loads(raw)
                    validate_event(event)
                except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
                    invalid_lines += 1
                    if len(diagnostics) < MAX_DIAGNOSTICS:
                        diagnostics.append(dict(location, problem="invalid event"))
                    continue
                event_id = event["event_id"]
                if event_id in locations:
                    duplicate_events += 1
                    continue
                if len(events) >= MAX_EVENTS:
                    raise ValueError("ERR-02 event limit exceeded")
                locations[event_id] = location
                events.append(event)
    events.sort(key=lambda event: (parse_time(event["observed_at"]), event["event_id"]))
    quality = {"files": len(files), "invalid_lines": invalid_lines,
               "duplicate_events": duplicate_events, "blank_lines": blank_lines,
               "diagnostics": diagnostics,
               "file_index": {str(i): path.name for i, path in enumerate(files, 1)}}
    return events, locations, quality


def build_calls(events: list) -> tuple[list, int]:
    groups = defaultdict(list)
    uncorrelated = 0
    for event in events:
        if event["event"] not in TOOL_EVENTS:
            continue
        if not event["tool_use_id"]:
            uncorrelated += 1
            continue
        groups[(event["source"], event["session_id"], event["tool_use_id"])].append(event)
    calls = []
    for (source, session_id, tool_use_id), group in sorted(groups.items()):
        starts = [event for event in group if event["event"] == "PreToolUse"]
        ends = [event for event in group if event["event"] != "PreToolUse"]
        first = starts[0] if starts else ends[0]
        last = ends[0] if ends else first
        duration_ms = None
        if len(starts) > 1 or len(ends) > 1 or len({event["tool_name"] for event in group}) > 1:
            pair_state, status = "ambiguous", "unknown"
        elif not starts:
            pair_state, status = "missing_start", last["status"]
        elif not ends:
            pair_state, status = "missing_end", "started"
        else:
            delta = (parse_time(last["observed_at"]) - parse_time(first["observed_at"])).total_seconds()
            pair_state, status = ("matched" if delta >= 0 else "clock_reversed"), last["status"]
            if delta >= 0:
                duration_ms = round(delta * 1000, 3)
        calls.append({
            "source": source, "session_id": session_id, "tool_use_id": tool_use_id,
            "tool_name": first["tool_name"], "agent_id": first["agent_id"],
            "started_at": starts[0]["observed_at"] if starts else None,
            "ended_at": ends[0]["observed_at"] if ends else None,
            "status": status, "pair_state": pair_state, "duration_ms": duration_ms,
            "input_fingerprint": first["input_fingerprint"],
            "action": first.get("action"), "target": first.get("target"),
            "purpose": first.get("purpose") if pair_state != "ambiguous" else None,
            "purpose_source": first.get("purpose_source", "missing") if pair_state != "ambiguous" else "ambiguous",
            "expected": None, "purpose_evidence": [],
            "result_summary": last.get("result_summary") if ends and pair_state != "ambiguous" else None,
            "evidence": [event["event_id"] for event in group],
        })
    calls.sort(key=lambda call: (parse_time(call["started_at"] or call["ended_at"]), call["tool_use_id"]))
    return calls, uncorrelated


def intent_key(event: dict) -> tuple:
    return tuple(event.get(key) for key in
                 ("source", "session_id", "turn_id", "agent_id", "tool_name", "input_fingerprint"))


def attach_purposes(events: list, calls: list) -> int:
    pending = defaultdict(list)
    by_call = {(call["source"], call["session_id"], call["tool_use_id"]): call for call in calls}
    linked = set()
    for event in sorted(events, key=lambda item: (parse_time(item["observed_at"]), item["event_id"])):
        if event["event"] == INTENT_EVENT:
            pending[intent_key(event)].append(event)
            continue
        if event["event"] != "PreToolUse" or not event["tool_use_id"]:
            continue
        call = by_call[(event["source"], event["session_id"], event["tool_use_id"])]
        candidates = pending.pop(intent_key(event), [])
        candidates = [item for item in candidates if 0 < (parse_time(event["observed_at"])
                      - parse_time(item["observed_at"])).total_seconds() <= INTENT_MAX_AGE_SEC]
        if call["pair_state"] == "ambiguous":
            continue
        if len(candidates) == 1:
            intent = candidates[0]
            call.update(purpose=intent["purpose"], purpose_source="agent_intent", expected=intent["expected"],
                        purpose_evidence=[intent["event_id"]])
            linked.add(intent["event_id"])
        elif len(candidates) > 1:
            call.update(purpose=None, purpose_source="ambiguous", expected=None,
                        purpose_evidence=[item["event_id"] for item in candidates])
    return sum(event["event"] == INTENT_EVENT for event in events) - len(linked)


def call_metrics(calls: list) -> dict:
    statuses = Counter(call["status"] for call in calls)
    durations = sorted(call["duration_ms"] for call in calls if call["duration_ms"] is not None)
    known = statuses["success"] + statuses["error"]
    completed = known + statuses["completed"]
    purposes = sum(bool(call.get("purpose")) for call in calls)
    return {
        "calls": len(calls), "success": statuses["success"], "errors": statuses["error"],
        "completed_unknown": statuses["completed"], "pending": statuses["started"],
        "ambiguous": statuses["unknown"], "known_outcomes": known,
        "outcome_coverage": round(known / completed, 4) if completed else None,
        "error_rate": round(statuses["error"] / known, 4) if known else None,
        "matched": sum(call["pair_state"] == "matched" for call in calls),
        "missing_start": sum(call["pair_state"] == "missing_start" for call in calls),
        "missing_end": sum(call["pair_state"] == "missing_end" for call in calls),
        "clock_reversed": sum(call["pair_state"] == "clock_reversed" for call in calls),
        "timed_calls": len(durations), "total_duration_ms": round(sum(durations), 3),
        "p50_duration_ms": durations[(len(durations) - 1) // 2] if durations else None,
        "max_duration_ms": max(durations) if durations else None,
        "purposes_recorded": purposes,
        "purposes_missing": sum(not call.get("purpose") and call.get("purpose_source") != "ambiguous" for call in calls),
        "purposes_ambiguous": sum(call.get("purpose_source") == "ambiguous" for call in calls),
        "purpose_coverage": round(purposes / len(calls), 4) if calls else None,
    }


def summarize(events: list, locations: dict, quality: dict) -> dict:
    calls, uncorrelated = build_calls(events)
    unlinked_intents = attach_purposes(events, calls)
    sessions = []
    groups = defaultdict(list)
    for event in events:
        groups[(event["source"], event["session_id"])].append(event)
    for (source, session_id), group in sorted(groups.items()):
        sessions.append({"source": source, "session_id": session_id, "events": len(group),
                         "first_at": group[0]["observed_at"], "last_at": group[-1]["observed_at"],
                         "has_start": any(event["event"] == "SessionStart" for event in group),
                         "has_end": any(event["event"] == "SessionEnd" for event in group)})
    by_tool = []
    tool_groups = defaultdict(list)
    for call in calls:
        tool_groups[(call["source"], call["tool_name"])].append(call)
    for (source, tool_name), subset in sorted(tool_groups.items()):
        by_tool.append(dict(call_metrics(subset), source=source, tool_name=tool_name))
    repeated = defaultdict(list)
    for call in calls:
        if call["started_at"] and call["input_fingerprint"] and call["pair_state"] != "ambiguous":
            key = (call["source"], call["session_id"], call["tool_name"], call["input_fingerprint"])
            repeated[key].append(call)
    repeats = []
    for (source, session_id, tool_name, fingerprint), group in sorted(repeated.items()):
        if len(group) > 1:
            repeats.append({"source": source, "session_id": session_id, "tool_name": tool_name,
                            "input_fingerprint": fingerprint, "count": len(group),
                            "errors": sum(call["status"] == "error" for call in group),
                            "evidence": [eid for call in group for eid in call["evidence"]]})
    metrics = dict(call_metrics(calls), events=len(events), sessions=len(sessions),
                   unlinked_intents=unlinked_intents,
                   uncorrelated_tool_events=uncorrelated,
                   repeated_extra_calls=sum(group["count"] - 1 for group in repeats))
    return {"report_version": 2, "metrics": metrics, "sessions": sessions, "by_tool": by_tool,
            "repeats": repeats, "calls": calls, "events": events, "locations": locations,
            "quality": quality}


def write_report(report: dict, output: Path, summary_path: Path) -> None:
    if output.resolve() == summary_path.resolve():
        raise ValueError("OPS-04 HTML and JSON paths must differ")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__REPORT_DATA__") != 1:
        raise ValueError("OPS-04 template requires one data placeholder")
    documents = [(output, template.replace("__REPORT_DATA__", script_json(report))),
                 (summary_path, json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")]
    for path, content in documents:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".observer-report-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="*", default=[Path(".agent-logs")])
    parser.add_argument("--output", type=Path, default=Path("reports/agent-behavior.html"))
    parser.add_argument("--summary", type=Path, help="Defaults to the HTML path with a .json suffix")
    parser.add_argument("--synthetic", action="store_true", help="Label this report as a synthetic demonstration")
    args = parser.parse_args()
    summary_path = args.summary or args.output.with_suffix(".json")
    try:
        files = input_files(args.inputs)
        if args.output.resolve() in files or summary_path.resolve() in files:
            raise ValueError("STATE-01 outputs cannot overwrite input logs")
        events, locations, quality = load_events(args.inputs)
        if not events:
            raise ValueError("ERR-02 no valid events")
        report = summarize(events, locations, quality)
        report["synthetic"] = args.synthetic
        write_report(report, args.output, summary_path)
    except (OSError, ValueError, TypeError):
        print("observer: analysis failed; use valid v1/v2 JSONL within the documented limits", file=sys.stderr)
        return 1
    print("HTML: " + str(args.output.resolve()))
    print("JSON: " + str(summary_path.resolve()))
    print("Events: " + str(len(events)) + "; invalid: " + str(quality["invalid_lines"])
          + "; duplicates: " + str(quality["duplicate_events"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
