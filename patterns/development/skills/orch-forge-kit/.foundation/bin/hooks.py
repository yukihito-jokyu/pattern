#!/usr/bin/env python3
"""Claude Code の hooks の本体。.claude/settings.json から呼ばれ、標準入力で hook の JSON を受け取る。

  pre-edit : manifest の status が ready のとき、編集の対象が protected に当たれば、ユーザーに確認を求める
             （permissionDecision: ask）
  post-edit: manifest の hooks.post_edit のうち glob に合う項目のコマンドを実行し、失敗すれば
             出力をエージェントに返す（終了コード2）

使い方（手で試すとき）:
  echo '{"tool_input": {"file_path": "/abs/path/src/a.ts"}}' | python3 hooks.py post-edit
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def read_event() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def target_of(event: dict) -> tuple[Path, str] | None:
    tool_input = event.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")
    if not raw:
        return None
    base = Path(event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    path = (base / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    root = _lib.find_root(path.parent if not path.exists() else path)
    if root is None:
        project = os.environ.get("CLAUDE_PROJECT_DIR")
        root = _lib.find_root(Path(project)) if project else None
    if root is None:
        return None
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return None
    return root, rel


def pre_edit(event: dict) -> int:
    found = target_of(event)
    if found is None:
        return 0
    root, rel = found
    manifest = _lib.load_manifest(root)
    if manifest.get("status") != "ready":
        return 0  # 基盤を作っている間（status: building）は、作者自身が保護ファイルを編集するので確認しない
    pattern = _lib.matches_any(rel, manifest.get("protected", []))
    if pattern is None:
        return 0
    reason = (f"{rel} は保護ファイル（manifest の protected: {pattern}）です。検査を通すために設定やルールを変えることは"
              "禁止されています。ユーザーが明示的にルールの変更を指示した場合だけ承認してください。"
              "手順は AGENTS.md の「ルールを変えたいとき」にあります。")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


def post_edit(event: dict) -> int:
    found = target_of(event)
    if found is None:
        return 0
    root, rel = found
    if not (root / rel).exists():
        return 0
    manifest = _lib.load_manifest(root)
    failures = []
    for entry in manifest.get("hooks", {}).get("post_edit", []):
        if not _lib.glob_to_regex(entry.get("glob", "")).match(rel):
            continue
        command = entry.get("command", "").replace("{file}", shlex.quote(rel))
        code, output = _lib.run_shell(command, root, int(entry.get("timeout", 100)))
        if code != 0:
            failures.append(f"$ {command}\n{_lib.tail(output, 30)}")
    if failures:
        print(f"{rel} の編集後の検査で指摘があります。ルールID・lint のルール名を docs/design/rules.md と "
              "docs/design/enforcement-matrix.md で引いて、コードを直してください（設定や抑止コメントで黙らせない）。\n\n"
              + "\n\n".join(failures), file=sys.stderr)
        return 2
    return 0


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("pre-edit", "post-edit"):
        print(__doc__, file=sys.stderr)
        return 1
    event = read_event()
    return pre_edit(event) if sys.argv[1] == "pre-edit" else post_edit(event)


if __name__ == "__main__":
    sys.exit(main())
