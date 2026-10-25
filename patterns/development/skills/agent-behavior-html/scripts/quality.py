"""Dependency-free whitespace/JSON formatting, AST structure and JavaScript syntax checks."""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import shlex
import subprocess
import sys
import tabnanny
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = Path(".claude/skills/agent-behavior-html")
sys.path.insert(0, str(ROOT / SKILL / "scripts"))
from event_model import SOURCE_EVENTS
ALLOWED_IMPORTS = frozenset((
    "argparse", "ast", "collections", "concurrent", "datetime", "fcntl", "hashlib", "hmac",
    "importlib", "io", "json", "os", "pathlib", "re", "shlex", "shutil", "stat", "subprocess",
    "sys", "tabnanny", "tempfile", "time", "tokenize", "typing", "unittest", "uuid", "event_model",
))
REQUIRED = (
    SKILL / "SKILL.md", SKILL / "scripts/event_model.py", SKILL / "scripts/record.py",
    SKILL / "scripts/analyze.py", SKILL / "scripts/install.py", SKILL / "assets/dashboard.html",
    Path("tests/test_observer.py"), Path("scripts/demo.py"), Path("Makefile"),
    Path(".claude/settings.json"), Path(".codex/hooks.json"),
)
REQUIRED_TESTS = frozenset((
    "test_metadata_only", "test_cli_fail_open", "test_input_validation", "test_append_and_sessions",
    "test_concurrent_append", "test_pairing", "test_timezone", "test_html_injection",
    "test_install_preserves_and_is_idempotent", "test_unknown_outcomes", "test_explicit_paths",
    "test_operation_details", "test_declared_purpose_correlation", "test_intent_cli_and_context",
    "test_legacy_log_compatibility",
    "test_install_in_place", "test_project_hook_configuration",
))
IGNORED_PARTS = frozenset((".git", ".foundation", ".agent-observer", ".agent-logs", "reports", "__pycache__"))


def handwritten(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in IGNORED_PARTS or part.startswith(".env") for part in relative.parts):
        return False
    if relative.as_posix() == "docs/design/enforcement-matrix.md":
        return False
    if relative.parts[0] == "examples":
        return False
    return path.suffix in (".py", ".cjs", ".json", ".md", ".html", ".yaml") or path.name == "Makefile"


def canonical(text: str, path: Path) -> str:
    if path.suffix == ".json":
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2) + "\n"
    return "\n".join(line.rstrip() for line in text.splitlines()).rstrip("\n") + "\n"


def check_python(path: Path, text: str) -> list:
    errors = []
    relative = path.relative_to(ROOT)
    try:
        tree = ast.parse(text, feature_version=(3, 9))
        tabnanny.process_tokens(tokenize.generate_tokens(io.StringIO(text).readline))
    except SyntaxError:
        return ["TOOL-04 CODE-01 " + str(relative) + ": Python 3.9 incompatible syntax"]
    except (tabnanny.NannyNag, tokenize.TokenError) as exc:
        return ["CODE-01 " + str(relative) + ": " + type(exc).__name__]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for module in modules:
                if module == "__future__":
                    continue
                test_import = relative.parts[0] == "tests" and module in ("analyze", "install", "record")
                if module.split(".")[0] not in ALLOWED_IMPORTS and not test_import:
                    errors.append("DEP-01 " + str(relative) + ": external or cross-entrypoint import " + module)
                if relative.name == "event_model.py" and module == "event_model":
                    errors.append("DEP-01 event_model cannot import itself")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not re.fullmatch(r"[a-z_][a-z0-9_]*", node.name) and node.name not in ("setUp", "tearDown"):
                errors.append("NAM-01 " + str(relative) + ": " + node.name)
            args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            public_args = [arg for arg in args if arg.arg not in ("self", "cls")]
            if node.returns is None or any(arg.annotation is None for arg in public_args):
                errors.append("CODE-01 " + str(relative) + ": annotate " + node.name)
            if node.end_lineno - node.lineno + 1 > 160 or len(public_args) > 8:
                errors.append("CODE-01 " + str(relative) + ": function too large " + node.name)
    return errors


def check_hook_wiring() -> list:
    errors = []
    for source, filename in (("claude", ".claude/settings.json"), ("codex", ".codex/hooks.json")):
        path = ROOT / filename
        if not path.is_file():
            continue
        config = json.loads(path.read_text(encoding="utf-8"))
        for event in SOURCE_EVENTS[source]:
            commands = [handler.get("command", "") for group in config.get("hooks", {}).get(event, [])
                        if group.get("matcher", "") in ("", "*") for handler in group.get("hooks", [])]
            found = False
            for command in commands:
                try:
                    args = shlex.split(command)
                    script = next(value for value in args if value.endswith("/agent-behavior-html/scripts/record.py"))
                    logs = args[args.index("--log-dir") + 1]
                    found |= (Path(script).is_absolute() and Path(script).is_file()
                              and args[args.index("--source") + 1] == source and Path(logs).is_absolute()
                              and Path(logs).name == ".agent-logs"
                              and ("--context" in args) == (event in ("UserPromptSubmit", "SubagentStart")))
                except (ValueError, TypeError, IndexError, StopIteration):
                    continue
            if not found:
                errors.append("TOOL-03 observer hook not connected: " + filename + " / " + event)
    return errors


def check_structure() -> list:
    errors = ["STR-01 missing " + str(path) for path in REQUIRED if not (ROOT / path).is_file()]
    errors.extend(check_hook_wiring())
    for name in ("impl", "review", "agent-behavior-html"):
        link = ROOT / ".agents/skills" / name
        if not link.is_symlink() or link.resolve() != (ROOT / ".claude/skills" / name).resolve():
            errors.append("STR-01 Codex skill link " + name)
    for path in (ROOT / SKILL / "scripts").glob("*.py"):
        if path.name not in ("event_model.py", "record.py", "analyze.py", "install.py"):
            errors.append("STR-01 unregistered runtime file " + path.name)
    test_path = ROOT / "tests/test_observer.py"
    if test_path.is_file():
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
        names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        for name in sorted(REQUIRED_TESTS - names):
            errors.append("TEST-01 missing contract " + name)
    template_path = ROOT / SKILL / "assets/dashboard.html"
    if template_path.is_file():
        text = template_path.read_text(encoding="utf-8")
        if ".innerHTML" in text or "fetch(" in text or re.search(r"<(?:script|link)[^>]+(?:src|href)=", text):
            errors.append("OPS-04 external resources or HTML data injection")
        if text.count("__REPORT_DATA__") != 1:
            errors.append("OPS-04 data placeholder count")
        scripts = re.findall(r"<script>(.*?)</script>", text, re.S)
        for script in scripts:
            result = subprocess.run(["node", "--check", "-"], input=script, text=True, capture_output=True)
            if result.returncode:
                errors.append("CODE-01 JavaScript syntax: " + result.stderr[:500])
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()
    paths = [args.file.resolve()] if args.file else sorted(ROOT.rglob("*"))
    errors = []
    for path in paths:
        if not path.is_file() or path.is_symlink() or not handwritten(path):
            continue
        relative = path.relative_to(ROOT)
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            formatted = canonical(text, path)
        except (ValueError, UnicodeError):
            errors.append("TOOL-02 " + str(relative) + ": invalid text/JSON")
            continue
        if raw != formatted.encode("utf-8"):
            if args.fix:
                path.write_bytes(formatted.encode("utf-8"))
                text = formatted
            else:
                errors.append("TOOL-02 " + str(relative) + ": run make fix")
        if path.suffix == ".py":
            errors.extend(check_python(path, text))
    if not args.file:
        errors.extend(check_structure())
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print("quality: formatting, AST, boundaries and JavaScript OK")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
