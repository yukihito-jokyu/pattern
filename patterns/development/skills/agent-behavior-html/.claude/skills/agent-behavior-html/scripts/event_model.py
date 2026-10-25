"""Versioned operation, declared purpose and bounded result contract."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

SCHEMA_VERSION = 2
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_LOG_LINE_BYTES = 16384
MAX_LOG_BYTES = 64 * 1024 * 1024
MAX_EVENTS = 100000
LOCK_TIMEOUT_SEC = 0.5
COMMON_EVENTS = (
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PermissionRequest", "SubagentStart", "SubagentStop", "PreCompact", "Stop", "SessionEnd",
)
SOURCE_EVENTS = {
    "claude": COMMON_EVENTS + ("PostToolUseFailure", "Notification", "PostCompact"),
    "codex": COMMON_EVENTS + ("PostCompact", "Interrupt"),
}
TOOL_EVENTS = frozenset(("PreToolUse", "PostToolUse", "PostToolUseFailure"))
EVENT_FIELDS = frozenset((
    "schema_version", "event_id", "observed_at", "source", "event", "session_id",
    "turn_id", "agent_id", "tool_use_id", "tool_name", "status", "exit_code",
    "input_fingerprint", "input_bytes",
))
DETAIL_LIMITS = {"action": 160, "target": 2048, "purpose": 1024, "expected": 512, "result_summary": 2048}
DETAIL_FIELDS = frozenset(DETAIL_LIMITS) | {"purpose_source"}
PURPOSE_SOURCES = frozenset(("missing", "tool_description", "agent_intent"))
INTENT_EVENT = "ActionIntent"
INTENT_MAX_AGE_SEC = 300
STATUSES = frozenset(("observed", "started", "completed", "success", "error"))
ID_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,200}\Z")
FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def bounded_text(value: Any, limit: int) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value.strip())
    text = re.sub(r"(?i)(authorization\s*[:=]\s*)(?:Bearer\s+|Basic\s+)?[^\s\"']+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)((?:--)?(?:api[_-]?key|token|password|passwd|secret|access[_-]?key|credential)"
                  r"\s*(?:[:=]\s*|\s+))(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)", r"\1[REDACTED]", text)
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|AKIA[A-Z0-9]{16})\b", "[REDACTED]", text)
    raw = text.encode("utf-8")
    return text if len(raw) <= limit else raw[:limit - 3].decode("utf-8", "ignore") + "…"


def operation_details(payload: dict) -> dict:
    name, event = payload.get("tool_name", ""), payload.get("hook_event_name")
    data = payload.get("tool_input")
    data = data if isinstance(data, dict) else {}
    actions = {"Bash": "コマンドを実行", "Read": "ファイルを読む", "Write": "ファイルを書く",
               "Edit": "ファイルを編集", "apply_patch": "パッチを適用", "Grep": "内容を検索",
               "Glob": "ファイルを探す", "WebFetch": "ページを取得", "WebSearch": "Webを検索"}
    target = next((data[key] for key in ("file_path", "path", "command", "cmd", "url", "pattern", "query")
                   if isinstance(data.get(key), str)), None)
    if name == "apply_patch" and target:
        target = "\n".join(line for line in target.splitlines()
                           if line.startswith(("*** Add File:", "*** Update File:", "*** Delete File:")))
    declared = event == INTENT_EVENT
    purpose = payload.get("purpose") if declared else data.get("description")
    details = {"action": actions.get(name, "ツールを実行") if name else None,
               "target": target, "purpose": purpose,
               "purpose_source": "agent_intent" if declared else "tool_description" if purpose else "missing",
               "expected": payload.get("expected") if declared else None, "result_summary": None}
    if event in ("PostToolUse", "PostToolUseFailure"):
        status, exit_code = outcome(event, payload.get("tool_response"))
        summary = {"success": "明示成功", "error": "明示失敗", "completed": "完了を観測（成否不明）"}[status]
        if exit_code is not None:
            summary += " · exit_code=" + str(exit_code)
        response = payload.get("tool_response")
        if name == "Bash" and isinstance(response, dict):
            snippets = [response[key] for key in ("stderr", "stdout", "output")
                        if isinstance(response.get(key), str) and response[key].strip()]
            if snippets:
                summary += "\n" + "\n".join(snippets)
        elif name == "Bash" and isinstance(response, str) and response.strip():
            summary += "\n" + response
        if event == "PostToolUseFailure" and isinstance(payload.get("error"), str):
            summary += "\n" + payload["error"]
        details["result_summary"] = summary
    for key, limit in DETAIL_LIMITS.items():
        details[key] = bounded_text(details[key], limit)
    if not details["purpose"]:
        details["purpose_source"] = "missing"
    return details


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("OPS-03 UTC timestamp required")
    return parsed


def safe_id(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("ERR-02 identifier must be a string")
    if ID_PATTERN.fullmatch(value):
        return value
    return "hashed:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def outcome(event: str, response: Any) -> tuple[str, Optional[int]]:
    if event == "PreToolUse":
        return "started", None
    if event == "PostToolUseFailure":
        return "error", None
    if event != "PostToolUse":
        return "observed", None
    if isinstance(response, dict):
        if response.get("isError") is True or response.get("is_error") is True:
            return "error", None
        exit_code = response.get("exit_code")
        if type(exit_code) is int:
            return ("success" if exit_code == 0 else "error"), exit_code
    return "completed", None


def normalize(payload: dict, source: str, key: bytes, observed_at: Optional[str] = None) -> dict:
    if not isinstance(payload, dict) or source not in SOURCE_EVENTS:
        raise ValueError("ERR-02 object and known source required")
    event = payload.get("hook_event_name")
    if event not in SOURCE_EVENTS[source] and event != INTENT_EVENT:
        raise ValueError("OPS-06 unsupported event")
    session_id = safe_id(payload.get("session_id"))
    if not session_id:
        raise ValueError("ERR-02 session_id required")
    status, exit_code = outcome(event, payload.get("tool_response"))
    tool_name = safe_id(payload.get("tool_name")) if event in TOOL_EVENTS or event == INTENT_EVENT else None
    tool_use_id = safe_id(payload.get("tool_use_id")) if event in TOOL_EVENTS else None
    if (event in TOOL_EVENTS or event == INTENT_EVENT) and not tool_name:
        raise ValueError("ERR-02 tool_name required")
    fingerprint, input_bytes = None, None
    if (event in TOOL_EVENTS or event == INTENT_EVENT) and "tool_input" in payload:
        tool_input = payload["tool_input"]
        if isinstance(tool_input, dict):
            tool_input = {name: value for name, value in tool_input.items() if name != "description"}
        canonical = json.dumps(tool_input, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":"), allow_nan=False).encode("utf-8")
        fingerprint = hmac.new(key, source.encode() + b"\0" + tool_name.encode() + b"\0" + canonical,
                               hashlib.sha256).hexdigest()
        input_bytes = len(canonical)
    result = {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "observed_at": observed_at or utc_now(),
        "source": source,
        "event": event,
        "session_id": session_id,
        "turn_id": safe_id(payload.get("turn_id")),
        "agent_id": safe_id(payload.get("agent_id")),
        "tool_use_id": tool_use_id,
        "tool_name": tool_name,
        "status": status,
        "exit_code": exit_code,
        "input_fingerprint": fingerprint,
        "input_bytes": input_bytes,
    }
    result.update(operation_details(payload) if event in TOOL_EVENTS or event == INTENT_EVENT else
                  {**{name: None for name in DETAIL_LIMITS}, "purpose_source": "missing"})
    if event == INTENT_EVENT and (not result["purpose"] or not result["input_fingerprint"]):
        raise ValueError("ERR-02 intent requires purpose and exact tool_input")
    validate_event(result)
    return result


def validate_event(event: dict) -> None:
    if not isinstance(event, dict):
        raise ValueError("ERR-02 event object required")
    version = event.get("schema_version")
    if type(version) is not int or version not in (1, 2):
        raise ValueError("ERR-02 unsupported schema_version")
    if set(event) != (EVENT_FIELDS if version == 1 else EVENT_FIELDS | DETAIL_FIELDS):
        raise ValueError("ERR-02 closed event fields required")
    source = event["source"]
    if not isinstance(source, str) or source not in SOURCE_EVENTS:
        raise ValueError("ERR-02 unknown source")
    accepted = SOURCE_EVENTS[source] + ((INTENT_EVENT,) if version == 2 else ())
    if event["event"] not in accepted or event["status"] not in STATUSES:
        raise ValueError("ERR-02 unknown event or status")
    for name in ("event_id", "session_id", "turn_id", "agent_id", "tool_use_id", "tool_name"):
        value = event[name]
        if value is None and name not in ("event_id", "session_id"):
            continue
        if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
            raise ValueError("ERR-02 invalid identifier")
    if not isinstance(event["observed_at"], str):
        raise ValueError("OPS-03 invalid timestamp")
    parse_time(event["observed_at"])
    for name in ("exit_code", "input_bytes"):
        value = event[name]
        if value is not None and type(value) is not int:
            raise ValueError("ERR-02 integer or null required")
    if event["input_bytes"] is not None and not 0 <= event["input_bytes"] <= MAX_INPUT_BYTES:
        raise ValueError("ERR-02 invalid input_bytes")
    fingerprint = event["input_fingerprint"]
    if fingerprint is not None and (not isinstance(fingerprint, str)
                                    or not FINGERPRINT_PATTERN.fullmatch(fingerprint)):
        raise ValueError("ERR-02 invalid fingerprint")
    name, status, exit_code = event["event"], event["status"], event["exit_code"]
    allowed = {"PreToolUse": {"started"}, "PostToolUse": {"completed", "success", "error"},
               "PostToolUseFailure": {"error"}}
    if status not in allowed.get(name, {"observed"}):
        raise ValueError("ERR-02 inconsistent status")
    if name in TOOL_EVENTS and event["tool_name"] is None:
        raise ValueError("ERR-02 missing tool_name")
    if exit_code is not None and (name != "PostToolUse"
                                  or status != ("success" if exit_code == 0 else "error")):
        raise ValueError("ERR-02 inconsistent exit_code")
    if version == 2:
        for field, limit in DETAIL_LIMITS.items():
            value = event[field]
            if value is not None and (not isinstance(value, str) or len(value.encode("utf-8")) > limit):
                raise ValueError("ERR-02 invalid detail field")
        if event["purpose_source"] not in PURPOSE_SOURCES:
            raise ValueError("ERR-02 invalid purpose source")
        if bool(event["purpose"]) != (event["purpose_source"] != "missing"):
            raise ValueError("ERR-02 inconsistent declared purpose")
        if name == INTENT_EVENT and (not event["purpose"] or not event["input_fingerprint"] or not event["tool_name"]):
            raise ValueError("ERR-02 incomplete intent")
        if name == INTENT_EVENT and (event["purpose_source"] != "agent_intent" or event["tool_use_id"] is not None):
            raise ValueError("ERR-02 inconsistent intent declaration")


def script_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace(
        "&", "\\u0026").replace("<", "\\u003c").replace(
        ">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
