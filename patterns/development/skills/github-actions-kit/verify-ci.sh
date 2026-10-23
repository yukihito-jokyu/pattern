#!/usr/bin/env bash
# ZIP展開先で準備し、キット全体と配布先の動作を一時ディレクトリで確認する。
set -euo pipefail
cd "$(dirname "$0")"
kit_root="$PWD"
verify_tmp="$(mktemp -d "${TMPDIR:-/tmp}/github-actions-kit-verify.XXXXXX")"
trap 'rm -rf "$verify_tmp"' EXIT

# 元キットの収束記録に合わせたuvを隔離し、ホストのuvを変更しない。
python3 -m venv "$verify_tmp/tools"
"$verify_tmp/tools/bin/python" -m pip install --disable-pip-version-check --no-cache-dir 'uv==0.13.4'
export PATH="$verify_tmp/tools/bin:$PATH"
export UV_PYTHON=3.12
uv --version
uv sync --locked
uv run --locked python -c 'import sys; assert sys.version_info[:2] == (3, 12); print(sys.version)'
# PEP 723の依存も先に準備する。準備に失敗したら検証へ進まない。
uv sync --locked --script .gha/gha.py
make check
python3 .foundation/bin/violation_probe.py --root . --only STR-02-a,OPS-06-a,TOOL-03-b --timeout 180

# install.pyを実際に起動し、コピー先の内容とcheckの結果を検証する。
python3 - "$kit_root" "$verify_tmp/target" <<'PYINSTALL'
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

kit, target = map(Path, sys.argv[1:])
target.mkdir()
spec = importlib.util.spec_from_file_location("kit_install", kit / "install.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def run_install(*extra):
    subprocess.run([sys.executable, str(kit / "install.py"), str(target), *extra], check=True)

def content(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}

run_install("--dry-run")
assert not list(target.iterdir()), "dry-runが配布先を変更した"
run_install()
for rel in module.REPLACED_DIRS:
    assert content(kit / rel) == content(target / rel), rel
for rel in (*module.REPLACED_FILES, *module.KEPT_FILES):
    assert (kit / rel).read_bytes() == (target / rel).read_bytes(), rel

kept = {}
for rel in module.KEPT_FILES:
    path = target / rel
    path.write_bytes(path.read_bytes() + b"\n# existing configuration\n")
    kept[rel] = path.read_bytes()
for rel in module.REPLACED_DIRS:
    (target / rel / "obsolete.txt").write_text("old implementation")
for rel in module.REPLACED_FILES:
    (target / rel).write_text("old implementation")
unrelated = target / "KEEP.txt"
unrelated.write_text("unrelated file")
before = content(target)
run_install("--dry-run")
assert before == content(target), "再導入dry-runが配布先を変更した"
run_install()
for rel in module.REPLACED_DIRS:
    assert content(kit / rel) == content(target / rel), rel
for rel in module.REPLACED_FILES:
    assert (kit / rel).read_bytes() == (target / rel).read_bytes(), rel
for rel, original in kept.items():
    assert (target / rel).read_bytes() == original, rel
assert unrelated.read_text() == "unrelated file"
result = subprocess.run(["uv", "run", "--locked", "--script", ".gha/gha.py", "check"],
                        cwd=target, check=True, capture_output=True, text=True)
print(result.stdout, end="")
assert "gha check: 指摘 0 件" in result.stdout
print("install: dry-run・新規導入・既存設定保持・古い実装置換・無関係ファイル保持を確認")
PYINSTALL
printf '%s\n' 'ZIP単体検証: 全確認成功（GitHub上では未実行、Claude Code実対話は未確認）'
