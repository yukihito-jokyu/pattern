"""Plan or install project-local Claude/Codex observation hooks without replacing other hooks."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from event_model import SOURCE_EVENTS

SKILL_NAME = "agent-behavior-html"
SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATHS = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json"}
DISCOVERY_PATHS = {"claude": ".claude/skills", "codex": ".agents/skills"}


def read_config(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("hooks", {}), dict):
        raise ValueError("TOOL-03 config and hooks must be objects")
    for groups in value.get("hooks", {}).values():
        if not isinstance(groups, list):
            raise ValueError("TOOL-03 event groups must be arrays")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError("TOOL-03 invalid hook group")
            if any(not isinstance(handler, dict) for handler in group["hooks"]):
                raise ValueError("TOOL-03 invalid hook handler")
    return value


def merge_hooks(config: dict, source: str, command: str) -> dict:
    result = json.loads(json.dumps(config))
    hooks = result.setdefault("hooks", {})
    for event in SOURCE_EVENTS[source]:
        event_command = command + " --context" if event in ("UserPromptSubmit", "SubagentStart") else command
        groups = hooks.setdefault(event, [])
        present = any(
            group.get("matcher", "") in ("", "*")
            and any(handler.get("command") == event_command for handler in group.get("hooks", []))
            for group in groups
        )
        if not present:
            groups.append({"hooks": [{"type": "command", "command": event_command, "timeout": 3}]})
    return result


def package_files(root: Path) -> dict:
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}


def refuse_symlink_parents(project: Path, path: Path) -> None:
    current = path
    while current != project:
        if current.is_symlink():
            raise ValueError("TOOL-03 symlink config path refused")
        current = current.parent


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".observer-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(project: Path, providers: list, apply: bool = False, in_place: bool = False) -> list:
    project = project.resolve()
    if not project.is_dir():
        raise ValueError("TOOL-03 project directory must exist")
    if os.name != "posix":
        raise ValueError("TOOL-04 local macOS/Linux required")
    bundle = SKILL_ROOT.resolve() if in_place else project / ".agent-observer" / SKILL_NAME
    if in_place and (project / ".claude/skills" / SKILL_NAME).resolve() != SKILL_ROOT.resolve():
        raise ValueError("TOOL-03 in-place mode requires this source project")
    refuse_symlink_parents(project, bundle)
    expected = package_files(SKILL_ROOT)
    if bundle.exists() and package_files(bundle) != expected:
        raise ValueError("TOOL-03 installed skill differs; preserve it before upgrading")
    operations = []
    for source in dict.fromkeys(providers):
        if source not in SOURCE_EVENTS:
            raise ValueError("TOOL-03 unknown provider")
        config_path = project / CONFIG_PATHS[source]
        refuse_symlink_parents(project, config_path)
        discovery = project / DISCOVERY_PATHS[source] / SKILL_NAME
        refuse_symlink_parents(project, discovery.parent)
        if discovery.is_symlink():
            if discovery.resolve() != bundle:
                raise ValueError("TOOL-03 skill link already belongs to another installation")
        elif discovery.exists() and not (in_place and discovery.resolve() == bundle.resolve()):
            raise ValueError("TOOL-03 existing skill will not be overwritten")
        command = " ".join(shlex.quote(str(value)) for value in (
            Path(sys.executable).resolve(), bundle / "scripts/record.py",
            "--source", source, "--log-dir", project / ".agent-logs",
        ))
        current = read_config(config_path)
        merged = merge_hooks(current, source, command)
        operations.append((source, config_path, discovery, current, merged))
    ignore_path = project / ".gitignore"
    refuse_symlink_parents(project, ignore_path)
    ignore = ignore_path.read_text(encoding="utf-8") if ignore_path.exists() else ""
    updated_ignore = ignore.rstrip("\n") + "\n" if ignore else ""
    for entry in ("/.agent-logs/", "/.agent-observer/", "/reports/agent-behavior.html", "/reports/agent-behavior.json"):
        if entry not in ignore.splitlines():
            updated_ignore += entry + "\n"
    changes = [str(path.relative_to(project)) for _, path, _, current, merged in operations
               if current != merged]
    changes += [str(discovery.relative_to(project)) for _, _, discovery, _, _ in operations
                if not (discovery.exists() or discovery.is_symlink())]
    if not bundle.exists():
        changes.append(str(bundle.relative_to(project)))
    if ignore != updated_ignore:
        changes.append(".gitignore")
    if not apply:
        return changes
    # All path conflicts and JSON shapes are checked before the first write.
    backup_dir = project / ".agent-observer/backups" / uuid.uuid4().hex
    originals = {}
    written = []
    new_links = []
    new_bundle = not bundle.exists()
    try:
        if new_bundle:
            bundle.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copytree(SKILL_ROOT, bundle, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        writes = [(path, (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode())
                  for _, path, _, current, merged in operations if current != merged]
        if updated_ignore != ignore:
            writes.append((ignore_path, updated_ignore.encode("utf-8")))
        for path, data in writes:
            original = path.read_bytes() if path.exists() else None
            originals[path] = original
            if original is not None:
                atomic_write(backup_dir / path.relative_to(project), original)
            atomic_write(path, data)
            written.append(path)
        for _, _, discovery, _, _ in operations:
            if not (discovery.exists() or discovery.is_symlink()):
                discovery.parent.mkdir(parents=True, exist_ok=True)
                discovery.symlink_to(os.path.relpath(bundle, discovery.parent), target_is_directory=True)
                new_links.append(discovery)
    except Exception:
        for discovery in new_links:
            discovery.unlink()
        for path in reversed(written):
            original = originals[path]
            if original is None:
                path.unlink()
            else:
                atomic_write(path, original)
        if new_bundle and bundle.exists():
            shutil.rmtree(bundle)
        raise
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--providers", nargs="+", choices=tuple(SOURCE_EVENTS), default=list(SOURCE_EVENTS))
    parser.add_argument("--apply", action="store_true", help="Apply the displayed project-local changes")
    parser.add_argument("--in-place", action="store_true", help="Wire this source project directly to its existing skill")
    args = parser.parse_args()
    try:
        changes = install(args.project, args.providers, args.apply, args.in_place)
    except (OSError, ValueError, TypeError):
        print("observer: install failed; check paths, existing skill and hook JSON", file=sys.stderr)
        return 1
    print(("Applied" if args.apply else "Plan (use --apply)") + ": " + str(args.project.resolve()))
    for path in changes:
        print("  " + path)
    if not changes:
        print("  No changes")
    print("Restart the agent. In Codex, review and trust these hooks with /hooks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
