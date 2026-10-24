#!/usr/bin/env bash
# ZIP展開先だけで検査環境を準備し、既存検査・代表違反・導入を確認する。
set -euo pipefail
cd "$(dirname "$0")"
kit_root="$PWD"
verify_tmp="$(mktemp -d "${TMPDIR:-/tmp}/skill-harness2-kit-verify.XXXXXX")"
trap 'rm -rf "$verify_tmp"' EXIT

python3 -m venv "$verify_tmp/tools"
"$verify_tmp/tools/bin/python" -m pip install --disable-pip-version-check --no-cache-dir 'uv==0.13.4'
export PATH="$verify_tmp/tools/bin:$PATH"
export UV_CACHE_DIR="$verify_tmp/uv-cache"
export UV_PYTHON_INSTALL_DIR="$verify_tmp/python"
export RUFF_CACHE_DIR="$verify_tmp/ruff-cache"
export MYPY_CACHE_DIR="$verify_tmp/mypy-cache"
export PYTHONDONTWRITEBYTECODE=1
uv venv --python 3.12 "$verify_tmp/runtime"
export PATH="$verify_tmp/runtime/bin:$PATH"
export UV_PYTHON="$verify_tmp/runtime/bin/python"
uv --version
python3 -c 'import sys; assert sys.version_info[:2] == (3, 12); print(sys.version)'
uvx ruff@0.17.2 --version
uvx mypy@1.20.2 --version
# 上の準備が失敗したら、set -e により検査へ進まない。
make check
python3 .foundation/bin/violation_probe.py --root . --only STR-01-a,STATE-04-a,OPS-05-a,TOOL-03-a --timeout 180

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
subprocess.run([sys.executable, str(kit / "install.py"), str(target)], check=True)

def content(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}

for source, installed in module.PLACES:
    if (module.KIT / source).is_dir():
        assert content(module.KIT / source) == content(target / installed), str(source)
    else:
        assert (module.KIT / source).read_bytes() == (target / installed).read_bytes(), str(source)
assert (target / ".claude/skills/skill-harness2/references/third-party-notices.md").is_file()
result = subprocess.run([sys.executable, ".h2/h2.py", "status", "sample"],
                        cwd=target, check=True, capture_output=True, text=True)
print(result.stdout, end="")
assert "準備" in result.stdout
print("導入先: 全配布ファイルの内容一致・帰属資料の収録・準備表示を確認")
PYINSTALL
printf '%s\n' 'ZIP単体検証: 成功（実Claudeの呼び出しと改善効果は未確認）'
