#!/usr/bin/env python3
"""orch-forge の補助 CLI の入口。配布先では `python3 .forge/forge.py <サブコマンド>` で呼ぶ。"""

import sys
from pathlib import Path

from forge_kit.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], Path(__file__).resolve().parent.parent))
