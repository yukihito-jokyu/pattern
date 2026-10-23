"""gha の CLI。指摘は `<ルールID> <パス>:<行> <説明>` の形で出す。

終了コードは 0（指摘なし）、1（指摘あり）、2（使い方・道具の誤り）。
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from gha_kit import checks, gitref, intent, pins, proc, ratchet, targets, yamlnode
from gha_kit.errors import ToolError, UsageError

USAGE = """\
使い方:
  gha check [--ratchet <版>] [--online] [<パス> ...]   検査する（--ratchet は基準の版より指摘が増えたかだけを見る）
  gha pin [--verify] [owner/repo[/path][@vX.Y.Z] ...]   アクションの参照を SHA に固定する・検証する
  gha intent <パス> [--compare-ref <版> [--from <古いパス>]]  ワークフローの棚卸し（作り直しの前後の突き合わせ）
"""


def main(argv: Sequence[str], root: Path | None = None, runner: proc.Runner = proc.run) -> int:
    """root と runner はテストで差し替える。既定は今のディレクトリと実際のコマンドの起動。"""
    parser = argparse.ArgumentParser(prog="gha", description=USAGE, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--ratchet", metavar="REF")
    check.add_argument("--online", action="store_true")
    check.add_argument("paths", nargs="*")
    pin = sub.add_parser("pin")
    pin.add_argument("--verify", action="store_true")
    pin.add_argument("specs", nargs="*")
    inventory = sub.add_parser("intent")
    inventory.add_argument("path")
    inventory.add_argument("--compare-ref", metavar="REF")
    inventory.add_argument("--from", dest="old_path", metavar="PATH")
    args = parser.parse_args(argv)
    root = root or Path.cwd()
    try:
        if args.command == "check":
            return run_check(root, args.paths, args.ratchet, args.online, runner)
        if args.command == "pin":
            return run_pin(root, args.specs, args.verify)
        return run_intent(root, args.path, args.compare_ref, args.old_path)
    except (UsageError, ToolError, ValueError, LookupError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2


def run_check(root: Path, paths: Sequence[str], ref: str | None, online: bool, runner: proc.Runner) -> int:
    if ref is None:
        findings = checks.run(root, paths, online, runner)
        for finding in findings:
            print(finding.render())
        print(f"gha check: 指摘 {len(findings)} 件")
        return 1 if findings else 0
    increases = ratchet.compare(root, ref, paths, runner)
    for increase in increases:
        print(f"# {increase.path} の {increase.rule} が {increase.before} 件から {increase.after} 件に増えた")
        for finding in increase.findings:
            print(finding.render())
    print(f"gha check --ratchet {ref}: 増えた組 {len(increases)} 件")
    return 1 if increases else 0


def list_tags(repo: str) -> str:
    result = proc.run(["git", "ls-remote", "--tags", f"https://github.com/{repo}"], Path.cwd())
    if result.code != 0:
        raise ToolError(f"{repo} のタグを取得できない: {result.stderr.strip()}")
    return result.stdout


def run_pin(root: Path, specs: Sequence[str], verify: bool) -> int:
    if not verify:
        if not specs:
            raise UsageError("固定するアクションを owner/repo の形で指定する")
        for spec in specs:
            print(f"uses: {pins.resolve(spec, list_tags).uses()}")
        return 0
    files = list(specs) or list(targets.discover(root).yaml_files())
    mismatches = pins.verify({rel: (root / rel).read_text(encoding="utf-8").splitlines() for rel in files}, list_tags)
    for mismatch in mismatches:
        print(f"DEP-06 {mismatch.file}:{mismatch.line} {mismatch.spec}: {mismatch.message}")
    print(f"gha pin --verify: 不一致 {len(mismatches)} 件")
    return 1 if mismatches else 0


def run_intent(root: Path, path: str, ref: str | None, old_path: str | None = None) -> int:
    """old_path を渡すと、版 ref の old_path と今の path を突き合わせる（作り直しでファイル名が変わったとき）。"""
    current = yamlnode.load(root, path)
    if ref is None:
        print(intent.render(current), end="")
        return 0
    source = old_path or path
    text = gitref.show(root, ref, source)
    if text is None:
        raise UsageError(f"版 {ref} に {source} が無い")
    with tempfile.TemporaryDirectory(prefix="gha-intent-") as tmp:
        (Path(tmp) / "old.yml").write_text(text, encoding="utf-8")
        old = yamlnode.load(Path(tmp), "old.yml")
    missing = intent.compare(old, current)
    print(
        f"# {ref} の {source} にあって、今の {path} に無い事実",
        "",
        "| 種類 | 事実 | 扱い（埋める） |",
        "|---|---|---|",
        sep="\n",
    )
    for kind, fact in missing:
        print(f"| {kind} | `{fact}` | |")
    print(f"\ngha intent --compare-ref {ref}: 無くなった事実 {len(missing)} 件")
    return 0
