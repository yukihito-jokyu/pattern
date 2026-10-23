#!/usr/bin/env bash
# ZIP単体で検査依存を準備し、正常動作と違反検出・導入保護を確認する。
set -eu
cd "$(dirname "$0")"

python3 --version
git --version
make --version
verification_tmp=$(mktemp -d)
trap 'rm -rf "$verification_tmp"' EXIT
python3 -m venv "$verification_tmp/venv"
"$verification_tmp/venv/bin/python" -m pip install --disable-pip-version-check 'uv==0.11.14'
export PATH="$verification_tmp/venv/bin:$PATH"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$verification_tmp/uv-cache}"
export UV_TOOL_DIR="${UV_TOOL_DIR:-$verification_tmp/uv-tools}"
export UV_TOOL_BIN_DIR="${UV_TOOL_BIN_DIR:-$verification_tmp/uv-bin}"
export PYTHONDONTWRITEBYTECODE=1
uv --version
make check
python3 .foundation/bin/violation_probe.py --root . --only STR-04-a,STATE-03-a,TOOL-03-a
python3 - <<'PYINSTALL'
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

source = Path.cwd()

def snapshot(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()
    }

with tempfile.TemporaryDirectory(prefix="skill-tune-install-") as work:
    repo = Path(work) / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text("existing-entry\n", encoding="utf-8")
    subprocess.run([sys.executable, "install.py", str(repo)], check=True)
    before = snapshot(repo)
    duplicate = subprocess.run(
        [sys.executable, "install.py", str(repo)], capture_output=True, text=True
    )
    assert duplicate.returncode == 1, duplicate
    assert "既にあるファイル" in duplicate.stderr, duplicate.stderr
    assert snapshot(repo) == before, "重複導入が既存ファイルを変更した"
    assert (repo / ".gitignore").read_text(encoding="utf-8") == "existing-entry\n.tune/work/\n"
    for tree, target in ((".tune", ".tune"), ("claude", ".claude")):
        for path in (source / "kit" / tree).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                assert (repo / target / path.relative_to(source / "kit" / tree)).read_bytes() == path.read_bytes()
    help_result = subprocess.run(
        [sys.executable, ".tune/tune.py", "--help"], cwd=repo,
        capture_output=True, text=True, check=True
    )
    assert "check-plan" in help_result.stdout, help_result.stdout
    status = subprocess.run(
        [sys.executable, ".tune/tune.py", "status", "--target", "sample"],
        cwd=repo, capture_output=True, text=True, check=True
    )
    assert "段階: 計画が無い" in status.stdout, status.stdout
print("導入検証: 新規コピー・重複導入時の無変更・導入先CLI起動に成功")
PYINSTALL
echo 'ZIP検証: 全検査・代表的な違反3件の検出・導入検証に成功'
