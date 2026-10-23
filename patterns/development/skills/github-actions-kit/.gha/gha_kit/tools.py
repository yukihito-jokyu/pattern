"""外部の検査ツール（yamllint、actionlint と shellcheck、shellcheck、zizmor）を呼び、指摘を Finding にそろえる。

ツールは `.gha/gha.py` のスクリプト依存として同じ環境に入るので、実行中の Python と同じ bin から探す。
指摘には、ツールの規則名に対応するルールIDを付ける（対応は rulemap.py）。
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from gha_kit import layout, rulemap
from gha_kit.errors import ToolError
from gha_kit.findings import Finding
from gha_kit.proc import Runner

ZIZMOR_UNREADABLE = re.compile(r"failed to load file://(?P<path>\S+) as ")
YAMLLINT_LINE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+): \[(?P<level>\w+)\] (?P<message>.*?)(?: \((?P<rule>[\w-]+)\))?$"
)


def bin_dir() -> Path:
    return Path(sys.executable).parent


def executable(name: str) -> str:
    """同じ環境の bin の中のパス。無ければ起動の時点で proc.run が ToolError にする。"""
    return str(bin_dir() / name)


def yamllint(root: Path, files: Sequence[str], run: Runner) -> list[Finding]:
    if not files:
        return []
    args = [sys.executable, "-m", "yamllint", "-c", layout.YAMLLINT_CONFIG, "-f", "parsable", "--strict", *files]
    result = run(args, root, None)
    if result.code not in (0, 1, 2):
        raise ToolError(f"yamllint が異常終了した（{result.code}）: {result.stderr.strip()}")
    findings = []
    for line in result.stdout.splitlines():
        match = YAMLLINT_LINE.match(line)
        if match:
            rule = match["rule"] or "syntax"
            findings.append(_finding("yamllint", rule, match["path"], int(match["line"]), match["message"]))
    return findings


def actionlint(root: Path, files: Sequence[str], run: Runner) -> list[Finding]:
    if not files:
        return []
    args = [
        executable("actionlint"),
        "-config-file",
        layout.ACTIONLINT_CONFIG,
        "-shellcheck",
        executable("shellcheck"),
        "-format",
        "{{json .}}",
        "-no-color",
        *files,
    ]
    result = run(args, root, bin_dir())
    if result.code not in (0, 1):
        raise ToolError(f"actionlint が異常終了した（{result.code}）: {result.stderr.strip()}")
    records = json.loads(result.stdout or "[]")
    return [
        _finding("actionlint", str(item["kind"]), str(item["filepath"]), int(item["line"]), str(item["message"]))
        for item in records
    ]


def shellcheck(root: Path, files: Sequence[str], run: Runner) -> list[Finding]:
    """`.github/scripts/` のシェルスクリプトを検査する（ワークフローの run は actionlint が shellcheck に渡す）。"""
    scripts = [rel for rel in files if rel.endswith(".sh")]
    if not scripts:
        return []
    result = run([executable("shellcheck"), "--format", "json1", *scripts], root, None)
    if result.code not in (0, 1):
        raise ToolError(f"shellcheck が異常終了した（{result.code}）: {result.stderr.strip()}")
    comments = json.loads(result.stdout or "{}").get("comments", [])
    return [
        _finding("shellcheck", f"SC{item['code']}", str(item["file"]), int(item["line"]), str(item["message"]))
        for item in comments
    ]


def zizmor(root: Path, files: Sequence[str], run: Runner, online: bool = False) -> list[Finding]:
    """読めないファイル（書きかけのジョブなど）は指摘1件にして外し、残りのファイルで回し直す。"""
    network = [] if online else ["--offline"]
    args = [executable("zizmor"), *network, "--no-progress", "--config", layout.ZIZMOR_CONFIG, "--format", "json"]
    remaining = list(files)
    findings: list[Finding] = []
    while remaining:
        result = run([*args, *remaining], root, None)
        unreadable = ZIZMOR_UNREADABLE.search(result.stderr) if result.code == 1 else None
        if unreadable and unreadable["path"] in remaining:
            remaining.remove(unreadable["path"])
            message = "zizmor がワークフローとして読めない。actionlint の指摘を先に直す"
            findings.append(_finding("zizmor", "unreadable", unreadable["path"], 1, message))
            continue
        if result.code not in (0, 11, 12, 13, 14):
            raise ToolError(f"zizmor が異常終了した（{result.code}）: {result.stderr.strip()}")
        return findings + _zizmor_findings(result.stdout)
    return findings


def _zizmor_findings(stdout: str) -> list[Finding]:
    findings = []
    for item in json.loads(stdout or "[]"):
        if item.get("ignored"):
            continue
        location = next(
            (loc for loc in item["locations"] if loc["symbolic"]["kind"] == "Primary"), item["locations"][0]
        )
        path = location["symbolic"]["key"]["Local"]["verbatim_path"]
        line = int(location["concrete"]["location"]["start_point"]["row"]) + 1
        message = f"{item['desc']}: {location['symbolic'].get('annotation', '')}".rstrip(": ")
        findings.append(_finding("zizmor", str(item["ident"]), str(path), line, message))
    return findings


def _finding(tool: str, kind: str, path: str, line: int, message: str) -> Finding:
    rule = rulemap.rule_for(tool, kind, message)
    return Finding(Path(path).as_posix().removeprefix("./"), line, rule, f"[{tool}:{kind}] {message}")
