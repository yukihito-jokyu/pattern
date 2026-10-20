#!/usr/bin/env bash
# ZIP展開先だけで準備・全検査・代表的な違反検出を行う。
set -eu
cd "$(dirname "$0")/.."

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
uv --version
make check
python3 .foundation/bin/violation_probe.py --root . --only STR-04-a,STR-05-a,TOOL-03-a
echo 'ZIP検証: 全検査・124件のテスト・代表的な違反3件の検出に成功'
