#!/usr/bin/env python3
"""抑止コメント（lint 無効化、型無視、テストの skip など）の混入を検出する。

manifest の guard を読む:
  include      : 検査するファイルの glob（既定: 全ファイル）
  exclude      : 除外する glob（既定で基盤自身の文書と道具 .foundation/、.claude/、docs/design/、
                 ルートの AGENTS.md・CLAUDE.md・README.md を除外する。ルールの悪い例に抑止記法が載るため）
  suppressions : 禁止する正規表現の一覧。要素は文字列か {"pattern": 正規表現, "rule": ルールID}
  allow        : 例外 [{"path": glob, "pattern": 正規表現, "reason": 理由}]。理由の無い例外は認めない
  rule         : suppressions の要素に rule が無いときにエラーに出すルールID（既定: GUARD）

1行ずつ照合するため、複数行にまたがる緩和（YAML で次の行に書く設定など）は検出できない。
それは構造検査で縛る。

使い方:
  python3 guard.py [--root <基盤>]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

DEFAULT_EXCLUDE = [".foundation/**", ".claude/**", "docs/design/**", "AGENTS.md", "CLAUDE.md", "README.md"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root")
    args = parser.parse_args()

    root = _lib.resolve_root(args.root)
    manifest = _lib.load_manifest(root)
    guard = manifest.get("guard", {})
    include = guard.get("include") or ["**"]
    exclude = DEFAULT_EXCLUDE + guard.get("exclude", [])
    default_rule = guard.get("rule") or "GUARD"
    patterns = []
    for item in guard.get("suppressions", []):
        raw = item.get("pattern", "") if isinstance(item, dict) else item
        rule = (item.get("rule") if isinstance(item, dict) else None) or default_rule
        try:
            patterns.append((raw, re.compile(raw), rule))
        except re.error as exc:
            _lib.fail(f"guard.suppressions の {raw!r} が正規表現として不正です: {exc}")
    allow = []
    for entry in guard.get("allow", []):
        if not entry.get("reason"):
            _lib.fail(f"guard.allow の {entry} に reason がありません。例外には理由を書いてください")
        allow.append((entry.get("path", ""), re.compile(entry.get("pattern", ".*"))))
    if not patterns:
        print("guard.suppressions が空です。使うツールの抑止記法を manifest に書いてください")
        return 1

    skip, link = _lib.copy_settings(manifest)
    violations = []
    for rel in _lib.iter_files(root, skip, link):
        if not _lib.matches_any(rel, include) or _lib.matches_any(rel, exclude):
            continue
        text = _lib.read_text(root / rel)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for raw, pattern, rule in patterns:
                if not pattern.search(line):
                    continue
                if any(_lib.glob_to_regex(path).match(rel) and allowed.search(line) for path, allowed in allow):
                    continue
                violations.append(f"{rule} {rel}:{lineno} 抑止・回避の記述 /{raw}/ は禁止です: {line.strip()[:120]}")

    for violation in violations:
        print(violation)
    print(f"guard: 違反 {len(violations)} 件")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
