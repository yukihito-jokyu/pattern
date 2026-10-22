#!/usr/bin/env python3
"""同じ.autoflow内の実行基盤を使う、Codex用CLIの入口。"""

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    engine = Path(__file__).resolve().parent
    if "--allow" in argv:
        print("エラー: --allow はClaude Code専用です。Codexの実行権限は現在の環境で確認してください。", file=sys.stderr)
        return 2
    if not (engine / "autoflow_kit/cli.py").is_file():
        print("エラー: .autoflow/autoflow_kitがありません。配置を確認してください。", file=sys.stderr)
        return 1
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(engine))
    from autoflow_kit.cli import main as run

    return run(argv, root)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
