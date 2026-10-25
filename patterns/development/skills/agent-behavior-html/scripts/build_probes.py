"""Generate targeted implementation mutations for the foundation violation probes."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ".claude/skills/agent-behavior-html/scripts/"
TEST_COMMAND = "python3 -B -m unittest discover -s tests -v"
QUALITY_COMMAND = "python3 scripts/quality.py"


def create_probe(rule: str, path: str, content: str, level: str = "structure",
                 command: str = QUALITY_COMMAND, mode: str = "create") -> dict:
    return {"id": rule + "-a", "rule": rule, "level": level,
            "description": "Violation of " + rule, "command": command,
            "files": [{"path": path, "mode": mode, "content": content}], "expect": rule}


def mutation(rule: str, path: str, before: str, after: str) -> dict:
    original = (ROOT / path).read_text(encoding="utf-8")
    if before not in original:
        raise ValueError(rule + " mutation target changed")
    return create_probe(rule, path, original.replace(before, after, 1), "test", TEST_COMMAND, "replace")


def main() -> int:
    probes = [
        create_probe("STR-01", RUNTIME + "extra.py", "VALUE = 1\n"),
        create_probe("DEP-01", "scripts/probe_dependency.py", "import requests\n"),
        create_probe("NAM-01", "scripts/probe_name.py", "def CamelCase() -> int:\n    return 1\n"),
        create_probe("CODE-01", "scripts/probe_code.py", "def missing_annotation():\n    return 1\n"),
        mutation("ERR-01", RUNTIME + "record.py", "    return 0\n\n\nif __name__", "    return 1\n\n\nif __name__"),
        mutation("ERR-02", RUNTIME + "event_model.py", "MAX_INPUT_BYTES = 8 * 1024 * 1024", "MAX_INPUT_BYTES = 16 * 1024 * 1024"),
        mutation("STATE-01", RUNTIME + "record.py", "os.O_CREAT | os.O_APPEND | os.O_WRONLY", "os.O_CREAT | os.O_TRUNC | os.O_WRONLY"),
        mutation("ASYNC-01", RUNTIME + "analyze.py",
                 'groups[(event["source"], event["session_id"], event["tool_use_id"])].append(event)',
                 'groups[("claude", event["session_id"], event["tool_use_id"])].append(event)'),
        mutation("OPS-02", RUNTIME + "install.py",
                 '"--source", source, "--log-dir", project / ".agent-logs",',
                 '"--source", source, "--log-dir", Path(".agent-logs"),'),
        mutation("OPS-03", RUNTIME + "event_model.py",
                 "if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:", "if False:"),
        mutation("OPS-04", RUNTIME + "event_model.py", r'"<", "\\u003c"', '"<", "<"'),
        mutation("OPS-05", RUNTIME + "record.py", "    return 0\n\n\nif __name__",
                 '    print("observer: saved")\n    return 0\n\n\nif __name__'),
        mutation("OPS-06", RUNTIME + "event_model.py", '    return "completed", None', '    return "success", None'),
        mutation("OPS-07", RUNTIME + "analyze.py",
                 '("source", "session_id", "turn_id", "agent_id", "tool_name", "input_fingerprint"))',
                 '("source", "session_id", "turn_id", "tool_name", "input_fingerprint"))'),
        create_probe("TOOL-01", "scripts/probe_suppression.py", "# " + "noqa\nVALUE = 1\n",
                     command="python3 .foundation/bin/guard.py --root ."),
        create_probe("TOOL-02", "scripts/probe_format.py", "VALUE = 1   \n", "format"),
        mutation("TOOL-03", RUNTIME + "install.py", "    result = json.loads(json.dumps(config))",
                 '    result = json.loads(json.dumps(config))\n    result["permissions"] = {}'),
        create_probe("TOOL-04", "scripts/probe_runtime.py", "match 1:\n    case 1:\n        pass\n"),
    ]
    original = (ROOT / (RUNTIME + "event_model.py")).read_text(encoding="utf-8")
    content = original.replace('"input_fingerprint", "input_bytes",',
                               '"input_fingerprint", "input_bytes", "tool_input",', 1).replace(
        "    validate_event(result)", '    result["tool_input"] = payload.get("tool_input")\n    validate_event(result)', 1)
    probes.append(create_probe("OPS-01", RUNTIME + "event_model.py", content, "test", TEST_COMMAND, "replace"))
    original = (ROOT / "tests/test_observer.py").read_text(encoding="utf-8")
    probes.append(create_probe("TEST-01", "tests/test_observer.py", original.replace(
        "def test_metadata_only(", "def metadata_only(", 1), "structure", QUALITY_COMMAND, "replace"))
    disconnected = create_probe("TOOL-03", ".codex/hooks.json", '{"hooks": {}}\n',
                                "test", TEST_COMMAND, "replace")
    disconnected["id"] = "TOOL-03-b"
    probes.append(disconnected)
    path = ROOT / ".foundation/probes.json"
    path.write_text(json.dumps({"probes": sorted(probes, key=lambda probe: probe["id"])},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Generated " + str(len(probes)) + " violation probes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
