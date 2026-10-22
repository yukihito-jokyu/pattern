#!/usr/bin/env python3
"""autoflow の補助 CLI の入口。配布先では `python3 .autoflow/autoflow.py <サブコマンド>` で呼ぶ。"""

import sys
from pathlib import Path

from autoflow_kit.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], Path(__file__).resolve().parent.parent))
