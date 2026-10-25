#!/usr/bin/env bash
set -euo pipefail

pattern_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
verification_root="$(mktemp -d)"
trap 'rm -rf -- "$verification_root"' EXIT
export PYTHONDONTWRITEBYTECODE=1

# Preserve the shipped source; reconnect only the disposable verification copy.
python3 - "$pattern_root" "$verification_root/project" <<'PY'
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

source, project = (Path(value).resolve() for value in sys.argv[1:])
shutil.copytree(source, project, symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".agent-logs", "reports"))
for provider, relative in (("claude", ".claude/settings.json"), ("codex", ".codex/hooks.json")):
    path = project / relative
    config = json.loads(path.read_text(encoding="utf-8"))
    for event, groups in config.get("hooks", {}).items():
        retained = []
        for group in groups:
            handlers = []
            for handler in group["hooks"]:
                args = shlex.split(handler.get("command", ""))
                recorder = any(arg.endswith("/agent-behavior-html/scripts/record.py") for arg in args)
                if not recorder:
                    handlers.append(handler)
            if handlers or not group["hooks"]:
                retained.append({**group, "hooks": handlers})
        config["hooks"][event] = retained
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(project / ".claude/skills/agent-behavior-html/scripts/install.py"),
                "--project", str(project), "--in-place", "--apply"], check=True)
for name in ("impl", "review"):
    link = project / ".agents/skills" / name
    target = project / ".claude/skills" / name
    link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
print("Prepared an isolated copy; shipped files and user settings are unchanged.", flush=True)
PY

cd -- "$verification_root/project"
make check
make demo
make probes
python3 .foundation/bin/rules_check.py --root . --final
