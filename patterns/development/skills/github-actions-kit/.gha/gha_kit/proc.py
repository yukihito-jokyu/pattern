"""外部コマンドを起動する唯一の場所（KIT-02）。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from gha_kit.errors import ToolError


@dataclass(frozen=True)
class Result:
    code: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str], Path, "Path | None"], Result]


def run(args: Sequence[str], cwd: Path, extra_path: Path | None = None, timeout: int = 300) -> Result:
    """コマンドを1回実行する。extra_path は PATH の先頭に足す（actionlint に shellcheck を見つけさせるため）。"""
    env = dict(os.environ)
    if extra_path is not None:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
    try:
        done = subprocess.run(
            list(args), cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        raise ToolError(f"{args[0]} が見つからない") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{args[0]} が {timeout} 秒で終わらなかった") from exc
    return Result(done.returncode, done.stdout, done.stderr)
