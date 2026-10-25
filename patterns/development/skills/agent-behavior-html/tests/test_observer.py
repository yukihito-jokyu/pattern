"""Executable contracts for metadata collection, correlation and portable installation."""

from __future__ import annotations

import fcntl
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / ".claude/skills/agent-behavior-html/scripts"
sys.path.insert(0, str(SCRIPTS))
import analyze
import event_model
import install
import record


def payload(event: str = "PreToolUse", session: str = "session-1", tool_id: str = "call-1") -> dict:
    return {"hook_event_name": event, "session_id": session, "tool_name": "Bash",
            "tool_use_id": tool_id, "tool_input": {"command": "make check"}}


def event(event_name: str = "PreToolUse", seconds: int = 0, source: str = "claude",
          session: str = "session-1", tool_id: str = "call-1", response: object = None) -> dict:
    data = payload(event_name, session, tool_id)
    if response is not None:
        data["tool_response"] = response
    return event_model.normalize(data, source, b"test-key", "2026-10-23T00:00:" + str(seconds).zfill(2) + "Z")


def run_record(log_dir: Path, raw: bytes, source: str = "claude") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "record.py"), "--source", source,
                           "--log-dir", str(log_dir)], input=raw, capture_output=True, timeout=5)


class TestObserver(unittest.TestCase):
    def test_metadata_only(self) -> None:
        secret = "fixture-secret-do-not-save-87321"
        data = dict(payload(), prompt=secret, error=secret, cwd="/" + secret,
                    transcript_path="/" + secret, tool_response={"content": secret},
                    tool_input={"command": "npm test --token " + secret, "token": secret})
        observed = event_model.normalize(data, "claude", b"key")
        text = json.dumps(observed)
        self.assertNotIn(secret, text, "OPS-01 raw content leaked")
        self.assertNotIn("tool_input", observed, "OPS-01 tool input retained")
        self.assertNotIn("transcript_path", observed, "OPS-02 transcript retained")
        self.assertIsNotNone(observed["input_fingerprint"])
        self.assertIn("npm test", observed["target"])
        self.assertIn("[REDACTED]", observed["target"])
        changed = event_model.normalize(data, "claude", b"another-key")
        self.assertNotEqual(observed["input_fingerprint"], changed["input_fingerprint"])

    def test_cli_fail_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log_dir = Path(temporary) / "logs"
            for raw in (b"fixture-secret-invalid-json", b"[]", b"x" * (event_model.MAX_INPUT_BYTES + 1)):
                result = run_record(log_dir, raw)
                self.assertEqual(result.returncode, 0, "ERR-01 hook blocked the agent")
                self.assertEqual(result.stdout, b"", "OPS-05 hook stdout not empty")
                self.assertNotIn(b"fixture-secret", result.stderr, "OPS-01 leaked error input")
            log_dir.write_bytes(b"occupied")
            result = run_record(log_dir, json.dumps(payload()).encode())
            self.assertEqual(result.returncode, 0, "ERR-01 write failure blocked agent")
            self.assertIn(b"recording failed", result.stderr)

    def test_input_validation(self) -> None:
        self.assertEqual(event_model.MAX_INPUT_BYTES, 8 * 1024 * 1024, "ERR-02 input cap changed")
        valid = event()
        for field, value in (("schema_version", 3), ("schema_version", True), ("observed_at", "2026-10-23"),
                             ("status", "success"), ("input_bytes", -1), ("input_fingerprint", "raw-input")):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError, msg="ERR-02 invalid event accepted"):
                    event_model.validate_event(dict(valid, **{field: value}))
        with self.assertRaises(ValueError):
            event_model.validate_event(dict(valid, raw_payload="fixture"))
        with self.assertRaises(ValueError):
            event_model.normalize(payload(session=""), "claude", b"key")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.jsonl"
            path.write_bytes((json.dumps(valid) + "\n" + json.dumps(valid) + "\n{\n").encode()
                             + b"x" * (event_model.MAX_LOG_LINE_BYTES + 1) + b"\n")
            events, _, quality = analyze.load_events([path])
            self.assertEqual(len(events), 1, "ERR-02 deduplication failed")
            self.assertEqual(quality["duplicate_events"], 1)
            self.assertEqual(quality["invalid_lines"], 2)

    def test_append_and_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log_dir = Path(temporary) / "logs"
            first = record.append_event(payload(), "claude", log_dir)
            record.append_event(payload(), "claude", log_dir)
            second = record.append_event(payload(session="../../escape"), "claude", log_dir)
            third = record.append_event(payload(), "codex", log_dir)
            self.assertEqual(first.parent, log_dir, "STATE-01 escaped log directory")
            self.assertEqual(len(first.read_text().splitlines()), 2, "STATE-01 log overwritten")
            self.assertNotEqual(first, second, "STATE-01 sessions merged")
            self.assertNotEqual(first, third, "STATE-01 providers merged")
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            self.assertEqual((log_dir / ".fingerprint-key").stat().st_size, 32)

    def test_concurrent_append(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log_dir = Path(temporary) / "logs"
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = [pool.submit(run_record, log_dir, json.dumps(payload(tool_id="call-" + str(i))).encode())
                           for i in range(18)]
                for future in futures:
                    result = future.result()
                    self.assertEqual(result.stderr, b"", "ASYNC-01 concurrent event lost")
            events, _, quality = analyze.load_events([log_dir])
            self.assertEqual(len(events), 18, "ASYNC-01 lost or merged concurrent events")
            self.assertEqual(quality["invalid_lines"], 0, "ASYNC-01 torn JSONL line")
            with (log_dir / ".writer.lock").open("rb") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                result = run_record(log_dir, json.dumps(payload()).encode())
                self.assertEqual(result.returncode, 0)
                self.assertIn(b"recording failed", result.stderr)

    def test_pairing(self) -> None:
        events = [event("PostToolUse", 5, response={"exit_code": 0}), event(seconds=1),
                  event(source="codex", seconds=2), event(session="other", seconds=3),
                  event("PostToolUse", 0, tool_id="orphan", response={"exit_code": 1})]
        calls, uncorrelated = analyze.build_calls(events)
        self.assertEqual(len(calls), 4, "ASYNC-01 cross-session correlation")
        paired = next(call for call in calls if call["pair_state"] == "matched")
        self.assertEqual(paired["duration_ms"], 4000, "ASYNC-01 wrong duration")
        self.assertEqual(uncorrelated, 0)
        self.assertEqual(sum(call["pair_state"] == "missing_end" for call in calls), 2)
        ambiguous, _ = analyze.build_calls([event(), event(seconds=1), event("PostToolUse", 3)])
        self.assertEqual(ambiguous[0]["pair_state"], "ambiguous")
        self.assertIsNone(ambiguous[0]["duration_ms"])
        reversed_calls, _ = analyze.build_calls([event(seconds=2), event("PostToolUse", 1)])
        self.assertEqual(reversed_calls[0]["pair_state"], "clock_reversed")
        no_id = event()
        no_id["tool_use_id"] = None
        self.assertEqual(analyze.build_calls([no_id]), ([], 1), "ASYNC-01 guessed a missing ID")

    def test_timezone(self) -> None:
        self.assertEqual(event_model.parse_time("2026-10-23T00:00:00Z").utcoffset().total_seconds(), 0)
        with self.assertRaises(ValueError, msg="OPS-03 naive timestamp accepted"):
            event_model.parse_time("2026-10-23T00:00:00")
        with self.assertRaises(ValueError):
            event_model.parse_time("2026-10-23T09:00:00+09:00")
        calls, _ = analyze.build_calls([event(), event("PostToolUse", 0)])
        self.assertEqual(calls[0]["duration_ms"], 0, "OPS-03 equal timestamps are valid")

    def test_unknown_outcomes(self) -> None:
        unknown = event("PostToolUse", 2, response="No error; exit code is not structured")
        self.assertEqual(unknown["status"], "completed", "OPS-06 guessed failure from text")
        calls, _ = analyze.build_calls([event(), unknown])
        metrics = analyze.call_metrics(calls)
        self.assertIsNone(metrics["error_rate"], "OPS-06 unknown outcome entered denominator")
        self.assertEqual(metrics["completed_unknown"], 1)
        self.assertEqual(event("PostToolUse", response={"isError": True})["status"], "error")
        self.assertEqual(event("PostToolUse", response={"exit_code": 0})["status"], "success")
        self.assertNotIn("PostToolUseFailure", event_model.SOURCE_EVENTS["codex"], "OPS-06 invented Codex event")
        self.assertIn("PostToolUseFailure", event_model.SOURCE_EVENTS["claude"])

    def test_operation_details(self) -> None:
        data = dict(payload(), tool_input={"command": "npm test --token abc-secret-value",
                                          "description": "認証の不具合を再現する"})
        first = event_model.normalize(data, "claude", b"key")
        self.assertEqual(first["action"], "コマンドを実行")
        self.assertEqual(first["purpose"], "認証の不具合を再現する")
        self.assertEqual(first["purpose_source"], "tool_description")
        self.assertNotIn("abc-secret-value", first["target"], "OPS-01 credential leaked")
        data["tool_input"]["description"] = "修正後の状態を確認する"
        second = event_model.normalize(data, "claude", b"key")
        self.assertEqual(first["input_fingerprint"], second["input_fingerprint"])
        data.update(hook_event_name="PostToolUse", tool_response={"exit_code": 1,
                    "stdout": "test failed", "stderr": "Authorization: Bearer abc-secret-value"})
        end = event_model.normalize(data, "claude", b"key")
        self.assertEqual(end["status"], "error")
        self.assertIn("test failed", end["result_summary"])
        self.assertNotIn("abc-secret-value", end["result_summary"])
        data["tool_response"] = "exit code 1: failed; token=abc-secret-value"
        textual = event_model.normalize(data, "codex", b"key")
        self.assertEqual(textual["status"], "completed", "OPS-06 guessed outcome from output text")
        self.assertIn("exit code 1", textual["result_summary"])
        self.assertNotIn("abc-secret-value", textual["result_summary"])
        data.update(tool_name="Read", tool_input={"file_path": "src/auth.ts"},
                    tool_response={"content": "private-file-body", "stdout": "private-file-body"})
        read = event_model.normalize(data, "codex", b"key")
        self.assertEqual(read["target"], "src/auth.ts")
        self.assertNotIn("private-file-body", json.dumps(read), "OPS-01 file body retained")
        for text in ("日本語" * 3000, "</script><img src=x onerror=alert(1)>"):
            data["tool_input"] = {"command": text, "description": text}
            normalized = event_model.normalize(data, "claude", b"key")
            event_model.validate_event(normalized)
            self.assertLessEqual(len(normalized["purpose"].encode()), event_model.DETAIL_LIMITS["purpose"])
            self.assertLessEqual(len((json.dumps(normalized, ensure_ascii=False) + "\n").encode()),
                                 event_model.MAX_LOG_LINE_BYTES)

    def test_declared_purpose_correlation(self) -> None:
        data = dict(payload(), hook_event_name="ActionIntent", purpose="不具合を再現する",
                    expected="問題のあるテストが失敗する")
        intent = event_model.normalize(data, "claude", b"test-key", "2026-10-22T23:59:59Z")
        report = analyze.summarize([intent, event(), event("PostToolUse", 2)], {}, {})
        call = report["calls"][0]
        self.assertEqual(call["purpose"], "不具合を再現する")
        self.assertEqual(call["expected"], "問題のあるテストが失敗する")
        self.assertEqual(call["purpose_evidence"], [intent["event_id"]])
        self.assertEqual(report["metrics"]["unlinked_intents"], 0)
        repeated = analyze.summarize([intent, event(), event(tool_id="second", seconds=1)], {}, {})
        self.assertEqual(sum(bool(call["purpose"]) for call in repeated["calls"]), 1,
                         "ASYNC-01 one intent reused for multiple actions")
        for changed in ({"source": "codex"}, {"session_id": "other"}, {"agent_id": "worker"},
                        {"turn_id": "other-turn"}, {"input_fingerprint": "a" * 64},
                        {"observed_at": "2026-10-22T23:50:00Z"}, {"observed_at": "2026-10-23T00:00:01Z"}):
            with self.subTest(changed=changed):
                report = analyze.summarize([dict(intent, **changed), event()], {}, {})
                self.assertIsNone(report["calls"][0]["purpose"], "OPS-07 guessed purpose association")
                self.assertEqual(report["metrics"]["unlinked_intents"], 1)
        other = dict(intent, event_id="intent-2", purpose="別の理由")
        ambiguous = analyze.summarize([intent, other, event()], {}, {})
        self.assertIsNone(ambiguous["calls"][0]["purpose"])
        self.assertEqual(ambiguous["calls"][0]["purpose_source"], "ambiguous")
        self.assertEqual(ambiguous["metrics"]["purposes_ambiguous"], 1)

    def test_intent_cli_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            logs = Path(temporary) / "logs"
            command = [sys.executable, str(SCRIPTS / "record.py"), "--source", "codex", "--log-dir", str(logs)]
            data = dict(payload(), purpose="認証の処理を確認する", expected="条件が分かる")
            result = subprocess.run(command + ["--intent"], input=json.dumps(data).encode(),
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"")
            self.assertEqual(result.stderr, b"")
            events, _, _ = analyze.load_events([logs])
            self.assertEqual(events[0]["event"], "ActionIntent")
            prompt = dict(payload("UserPromptSubmit"), turn_id="turn-1", prompt="private-prompt-body")
            result = subprocess.run(command + ["--context"], input=json.dumps(prompt).encode(),
                                    capture_output=True, timeout=5)
            context = json.loads(result.stdout)["hookSpecificOutput"]
            self.assertEqual(context["hookEventName"], "UserPromptSubmit")
            self.assertIn("--intent", context["additionalContext"])
            self.assertIn("turn-1", context["additionalContext"])
            self.assertNotIn("private-prompt-body", context["additionalContext"])
            self.assertNotIn("private-prompt-body", "".join(path.read_text() for path in logs.glob("*.jsonl")))
            missing = subprocess.run(command + ["--intent"], input=json.dumps(payload()).encode(),
                                     capture_output=True, timeout=5)
            self.assertEqual(missing.returncode, 0)
            self.assertIn(b"recording failed", missing.stderr)

    def test_legacy_log_compatibility(self) -> None:
        legacy = {name: value for name, value in event().items() if name in event_model.EVENT_FIELDS}
        legacy["schema_version"] = 1
        event_model.validate_event(legacy)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mixed.jsonl"
            path.write_text(json.dumps(legacy) + "\n" + json.dumps(event("PostToolUse", 2)) + "\n")
            events, locations, quality = analyze.load_events([path])
            self.assertEqual(quality["invalid_lines"], 0)
            report = analyze.summarize(events, locations, quality)
            self.assertEqual(report["calls"][0]["duration_ms"], 2000)
            self.assertIsNone(report["calls"][0]["purpose"])
            self.assertEqual(report["metrics"]["purposes_missing"], 1)

    def test_html_injection(self) -> None:
        injected = "</script><img src=x onerror=alert(1)>&\u2028"
        valid = event()
        report = analyze.summarize([valid], {valid["event_id"]: {"file": injected, "line": 1}},
                                   {"files": 1, "invalid_lines": 0, "duplicate_events": 0})
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.html"
            summary = output.with_suffix(".json")
            analyze.write_report(report, output, summary)
            text = output.read_text()
            self.assertNotIn(injected, text, "OPS-04 script injection")
            self.assertIn("\\u003c/script\\u003e", text, "OPS-04 unsafe JSON embedding")
            self.assertNotIn(".innerHTML", text, "OPS-04 unsafe data sink")
            self.assertNotIn("fetch(", text)
            self.assertEqual(json.loads(summary.read_text()), report)
            with self.assertRaises(ValueError):
                analyze.write_report(report, output, output)

    def test_install_preserves_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "space ' $x project"
            project.mkdir()
            settings = project / ".claude/settings.json"
            settings.parent.mkdir()
            existing = {"permissions": {"allow": ["Read"]}, "hooks": {"Stop": [
                {"hooks": [{"type": "command", "command": "echo fixture"}]}]}}
            settings.write_text(json.dumps(existing))
            original = settings.read_bytes()
            before = set(project.rglob("*"))
            install.install(project, ["claude", "codex"])
            self.assertEqual(set(project.rglob("*")), before, "TOOL-03 dry run changed project")
            install.install(project, ["claude", "codex"], apply=True)
            first = settings.read_bytes()
            merged = json.loads(first)
            self.assertEqual(merged["permissions"], existing["permissions"], "TOOL-03 settings destroyed")
            self.assertEqual(merged["hooks"]["Stop"][0], existing["hooks"]["Stop"][0])
            self.assertEqual(set(merged["hooks"]), set(event_model.SOURCE_EVENTS["claude"]))
            handler = merged["hooks"]["PreToolUse"][-1]["hooks"][0]
            self.assertEqual(handler["timeout"], 3)
            elsewhere = project / "subdir"
            elsewhere.mkdir()
            result = subprocess.run(handler["command"], shell=True, cwd=elsewhere,
                                    input=json.dumps(payload()).encode(), capture_output=True, timeout=5)
            self.assertEqual(result.stderr, b"", "OPS-02 hook depends on cwd or unsafe quoting")
            self.assertTrue(list((project / ".agent-logs").glob("*.jsonl")), "OPS-02 wrong log path")
            self.assertEqual(install.install(project, ["claude", "codex"], apply=True), [], "TOOL-03 not idempotent")
            self.assertEqual(settings.read_bytes(), first, "TOOL-03 duplicate hooks")
            backups = list((project / ".agent-observer/backups").glob("*/.claude/settings.json"))
            self.assertEqual(backups[0].read_bytes(), original)
            for source, directory in install.DISCOVERY_PATHS.items():
                self.assertTrue((project / directory / install.SKILL_NAME / "SKILL.md").is_file(), source)
            codex = json.loads((project / ".codex/hooks.json").read_text())
            self.assertEqual(set(codex["hooks"]), set(event_model.SOURCE_EVENTS["codex"]))

    def test_install_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "source project"
            skill = project / ".claude/skills/agent-behavior-html"
            shutil.copytree(SCRIPTS.parent, skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            settings = project / ".claude/settings.json"
            original = {"hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": [
                {"type": "command", "command": "echo preserved"}]}]}}
            settings.write_text(json.dumps(original))
            with patch.object(install, "SKILL_ROOT", skill):
                before = set(project.rglob("*"))
                install.install(project, ["claude", "codex"], in_place=True)
                self.assertEqual(set(project.rglob("*")), before, "TOOL-03 dry run wrote files")
                install.install(project, ["claude", "codex"], apply=True, in_place=True)
                self.assertTrue(skill.is_dir())
                self.assertFalse(skill.is_symlink(), "TOOL-03 source skill replaced")
                self.assertFalse((project / ".agent-observer/agent-behavior-html").exists())
                self.assertEqual(json.loads(settings.read_text())["hooks"]["PreToolUse"][0],
                                 original["hooks"]["PreToolUse"][0])
                self.assertEqual(install.install(project, ["claude", "codex"], apply=True, in_place=True), [])
                elsewhere = project / "nested"
                elsewhere.mkdir()
                for source in ("claude", "codex"):
                    config = json.loads((project / install.CONFIG_PATHS[source]).read_text())
                    for event_name in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
                        handler = config["hooks"][event_name][-1]["hooks"][0]
                        data = payload(event_name, tool_id=source)
                        data["tool_input"]["description"] = "接続確認のために実行する"
                        if event_name == "PostToolUse":
                            data["tool_response"] = {"exit_code": 0, "stdout": "wiring fixture"}
                        result = subprocess.run(handler["command"], shell=True, cwd=elsewhere,
                                                input=json.dumps(data).encode(), capture_output=True, timeout=5)
                        self.assertEqual(result.returncode, 0)
                        self.assertEqual(result.stderr, b"", "TOOL-03 configured hook failed")
                        if event_name == "UserPromptSubmit":
                            self.assertIn("additionalContext", json.loads(result.stdout)["hookSpecificOutput"])
                events, locations, quality = analyze.load_events([project / ".agent-logs"])
                report = analyze.summarize(events, locations, quality)
                self.assertEqual(report["metrics"]["calls"], 2)
                self.assertEqual(report["metrics"]["purposes_recorded"], 2)
                self.assertEqual(report["metrics"]["success"], 2)
                with self.assertRaises(ValueError):
                    install.install(elsewhere, ["claude"], apply=True, in_place=True)

    def test_project_hook_configuration(self) -> None:
        for source, filename in install.CONFIG_PATHS.items():
            path = ROOT / filename
            self.assertTrue(path.is_file(), "TOOL-03 project hook configuration missing")
            config = json.loads(path.read_text())
            for event_name in event_model.SOURCE_EVENTS[source]:
                commands = [handler.get("command", "") for group in config.get("hooks", {}).get(event_name, [])
                            if group.get("matcher", "") in ("", "*") for handler in group.get("hooks", [])]
                matches = [shlex.split(command) for command in commands if "/agent-behavior-html/scripts/record.py" in command]
                self.assertEqual(len(matches), 1, "TOOL-03 observer hook missing or duplicated: " + source + "/" + event_name)
                args = matches[0]
                self.assertEqual(args[args.index("--source") + 1], source)
                self.assertEqual("--context" in args, event_name in ("UserPromptSubmit", "SubagentStart"))

    def test_explicit_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            data = event()
            path = project / "input.jsonl"
            path.write_text(json.dumps(data) + "\n")
            output = project / "chosen/report.html"
            result = subprocess.run([sys.executable, str(SCRIPTS / "analyze.py"), str(path), "--output", str(output)],
                                    cwd="/", capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, "OPS-02 explicit paths ignored")
            self.assertTrue(output.exists())
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPTS / "analyze.py"), str(path), "--output", str(path)],
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1, "STATE-01 analyzer overwrote source log")
            self.assertEqual(path.read_bytes(), before)
            result = subprocess.run([sys.executable, str(SCRIPTS / "analyze.py"), str(project / "missing.jsonl")],
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1, "ERR-01 analyzer hid invalid input")

    def test_install_preflight_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            settings = project / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text('{"permissions": {}}')
            original = settings.read_bytes()
            bad = project / ".codex/hooks.json"
            bad.parent.mkdir()
            bad.write_text("[]")
            with self.assertRaises(ValueError):
                install.install(project, ["claude", "codex"], apply=True)
            self.assertEqual(settings.read_bytes(), original)
            self.assertFalse((project / ".agent-observer").exists())
            bad.unlink()
            real_write = install.atomic_write

            def fail_codex(path: Path, content: bytes) -> None:
                if path == bad.resolve():
                    raise OSError("fixture failure")
                real_write(path, content)

            with patch.object(install, "atomic_write", side_effect=fail_codex):
                with self.assertRaises(OSError):
                    install.install(project, ["claude", "codex"], apply=True)
            self.assertEqual(settings.read_bytes(), original, "TOOL-03 failed rollback")
            self.assertFalse((project / ".agent-observer/agent-behavior-html").exists())

    def test_repeats_and_evidence(self) -> None:
        events = [event(tool_id="one"), event("PostToolUse", 2, tool_id="one", response={"exit_code": 1}),
                  event(seconds=3, tool_id="two"), event("PostToolUse", 4, tool_id="two", response={"exit_code": 0}),
                  event(source="codex", tool_id="three")]
        locations = {item["event_id"]: {"file": "fixture", "line": i + 1} for i, item in enumerate(events)}
        report = analyze.summarize(events, locations, {})
        self.assertEqual(len(report["repeats"]), 1)
        self.assertEqual(report["metrics"]["repeated_extra_calls"], 1)
        self.assertEqual(report["metrics"]["error_rate"], 0.5)
        self.assertEqual(report["metrics"]["sessions"], 2)
        self.assertTrue(all(eid in locations for call in report["calls"] for eid in call["evidence"]))


if __name__ == "__main__":
    unittest.main()
