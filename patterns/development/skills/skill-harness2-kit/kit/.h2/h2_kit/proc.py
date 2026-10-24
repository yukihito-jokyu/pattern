"""外部コマンド（claude、事後の検査）を動かす。subprocess と環境変数はこのモジュールだけ（DEP-04、OPS-02）。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from h2_kit.errors import CommandError


@dataclass(frozen=True)
class Completed:
    """終わったコマンドの結果。時間切れも結果として返し、途中までの出力を残す。"""

    code: int
    stdout: str
    stderr: str
    timed_out: bool


def run_command(argv: Sequence[str], cwd: Path, stdin: str, timeout_sec: int) -> Completed:
    """コマンドを動かす。起動できなければ CommandError を投げる。"""
    try:
        done = subprocess.run(
            list(argv),
            cwd=cwd,
            input=stdin,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            env=dict(os.environ),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return Completed(-1, _build_text(exc.stdout), _build_text(exc.stderr), timed_out=True)
    except OSError as exc:
        raise CommandError(f"{argv[0]} を起動できません: {exc.strerror or exc}") from exc
    return Completed(done.returncode, done.stdout, done.stderr, timed_out=False)


def _build_text(data: bytes | str | None) -> str:
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data
