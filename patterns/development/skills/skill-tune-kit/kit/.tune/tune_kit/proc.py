"""外部コマンド（git と、検査の command）を実行する。外部コマンドはこのモジュールだけから呼ぶ。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tune_kit.errors import CommandError

GIT_IDENTITY = (
    "-c",
    "user.name=skill-tune",
    "-c",
    "user.email=skill-tune@localhost",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
)
BASELINE_TAG = "skill-tune-baseline"
TAIL_LINES = 30
TIMEOUT_EXIT = 124


@dataclass(frozen=True)
class CommandResult:
    code: int
    output: str

    @property
    def tail(self) -> str:
        return "\n".join(self.output.rstrip().splitlines()[-TAIL_LINES:])


def _run_git(directory: Path, args: Sequence[str]) -> str:
    try:
        result = subprocess.run(["git", *GIT_IDENTITY, *args], cwd=directory, capture_output=True, check=False)
    except OSError as exc:
        raise CommandError(
            f"git を起動できません（{exc}）。実行役が変えたファイルを調べるために git が要ります"
        ) from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise CommandError(f"git {' '.join(args)} が失敗しました（{directory}）: {message}")
    return result.stdout.decode("utf-8", "replace")


def run_git_baseline(directory: Path) -> None:
    """sandbox を新しい git リポジトリにして、基準のコミットにタグを付ける。実行役がコミットしても基準は動かない。"""
    _run_git(directory, ["init", "-q"])
    _run_git(directory, ["add", "-A"])
    _run_git(directory, ["commit", "-q", "--allow-empty", "-m", "skill-tune baseline"])
    _run_git(directory, ["tag", BASELINE_TAG])


def run_git_changed(directory: Path) -> tuple[str, ...]:
    """基準のコミットから変わったファイル（コミット済み・未コミット・未追跡のすべて）。"""
    _run_git(directory, ["add", "-A"])
    names = _run_git(directory, ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE_TAG])
    return tuple(sorted(name for name in names.split("\0") if name))


def run_git_diff(directory: Path) -> str:
    """未追跡のファイルも含めた、基準のコミットからの差分。"""
    _run_git(directory, ["add", "-A"])
    return _run_git(directory, ["diff", "--cached", "--no-color", "--no-ext-diff", "--no-renames", BASELINE_TAG])


def run_command(command: str, directory: Path, timeout_sec: int) -> CommandResult:
    """シェルのコマンドを directory で実行する。検査の command は承認済みの計画にあるものだけを渡す（OPS-04）。"""
    environment = dict(os.environ)
    environment.setdefault("CI", "1")
    try:
        completed = subprocess.run(
            command,
            cwd=directory,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(TIMEOUT_EXIT, f"[timeout] {timeout_sec} 秒で打ち切りました")
    except OSError as exc:
        return CommandResult(1, f"コマンドを起動できません: {exc}")
    return CommandResult(completed.returncode, (completed.stdout or "") + (completed.stderr or ""))
