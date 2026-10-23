#!/usr/bin/env python3
"""skill-tune の補助 CLI の入口。配布先では `python3 .tune/tune.py <サブコマンド>` で呼ぶ。"""

from __future__ import annotations

import sys
from pathlib import Path

from tune_kit import cli

if __name__ == "__main__":
    sys.exit(cli.main(sys.argv[1:], Path(__file__).resolve().parent.parent))
