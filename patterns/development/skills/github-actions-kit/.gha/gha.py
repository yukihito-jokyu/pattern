# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "actionlint-py==1.7.12.25",
#   "pyyaml==6.0.3",
#   "shellcheck-py==0.11.0.1",
#   "yamllint==1.38.0",
#   "zizmor==1.31.1",
# ]
# ///
"""gha の入口。`uv run --locked --script .gha/gha.py <サブコマンド>` で起動する。

依存の版は上の宣言と gha.py.lock で固定する。
"""

import sys

from gha_kit.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
