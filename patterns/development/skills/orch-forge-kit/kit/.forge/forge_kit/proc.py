"""外部コマンド（git、charter の検査コマンド、claude -p）と並行と一時ディレクトリを扱う。

外部コマンドはここだけから呼ぶ。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

from forge_kit.errors import CommandError

GIT_IDENTITY = (
    "-c",
    "user.name=orch-forge",
    "-c",
    "user.email=orch-forge@localhost",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
)
BASELINE_TAG = "orch-forge-baseline"
COPIES_DIR = "orch-forge"
TAIL_LINES = 30
TIMEOUT_EXIT = 124
HASH_CHARS = 8

Item = TypeVar("Item")
Outcome = TypeVar("Outcome")


@dataclass(frozen=True)
class Result:
    code: int
    output: str

    @property
    def tail(self) -> str:
        return "\n".join(self.output.rstrip().splitlines()[-TAIL_LINES:])


@dataclass(frozen=True)
class Launched:
    """実行役の起動の結果。stdout は stream-json の全文。"""

    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str


Launcher = Callable[[Sequence[str], Path, int], Launched]


def copies_root(root: Path) -> Path:
    """評価用のコピーを置く、リポジトリの外の場所（ADR 0003）。

    同じ名前の別のリポジトリと混ざらないように、パスのハッシュを付ける。
    """
    resolved = root.resolve()
    suffix = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:HASH_CHARS]
    return Path(tempfile.gettempdir()) / COPIES_DIR / f"{resolved.name}-{suffix}"


def _git(directory: Path, args: Sequence[str]) -> str:
    if shutil.which("git") is None:
        raise CommandError("git が見つかりません。評価用のコピーの差分を取るために git が要ります")
    result = subprocess.run(["git", *GIT_IDENTITY, *args], cwd=directory, capture_output=True, check=False)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise CommandError(f"git {' '.join(args)} が失敗しました（{directory}）: {message}")
    return result.stdout.decode("utf-8", "replace")


def git_baseline(directory: Path) -> None:
    """コピーを新しい git リポジトリにして、基準のコミットにタグを付ける。実行役がコミットしても基準は動かない。"""
    _git(directory, ["init", "-q"])
    _git(directory, ["add", "-A"])
    _git(directory, ["commit", "-q", "--allow-empty", "-m", "orch-forge baseline"])
    _git(directory, ["tag", BASELINE_TAG])


def git_changed(directory: Path) -> tuple[str, ...]:
    """基準のコミットから変わったファイル（.gitignore を反映。コミット済み・未コミット・未追跡のすべて）。"""
    _git(directory, ["add", "-A"])
    names = _git(directory, ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE_TAG])
    return tuple(sorted(name for name in names.split("\0") if name))


def git_patch(directory: Path) -> str:
    """未追跡のファイルも含めた、基準のコミットからの差分。"""
    _git(directory, ["add", "-A"])
    return _git(directory, ["diff", "--cached", "--no-color", "--no-ext-diff", "--no-renames", BASELINE_TAG])


def shell(command: str, directory: Path, timeout_sec: int) -> Result:
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
        return Result(TIMEOUT_EXIT, f"[timeout] {timeout_sec} 秒で打ち切りました")
    return Result(completed.returncode, (completed.stdout or "") + (completed.stderr or ""))


def shell_many(command: str, directories: Sequence[Path], timeout_sec: int, parallel: int) -> list[Result]:
    """同じコマンドを複数のディレクトリで並行に回し、ディレクトリの順に結果を返す。"""
    with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
        return list(pool.map(lambda directory: shell(command, directory, timeout_sec), directories))


def launch(args: Sequence[str], directory: Path, timeout_sec: int) -> Launched:
    """実行役（claude -p）を起動して終わりを待つ。時間の上限を超えたら、サブエージェントも含めて止める。"""
    try:
        child = subprocess.Popen(
            list(args),
            cwd=directory,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise CommandError(f"{args[0]} が見つかりません。Claude Code の CLI を入れてください") from exc
    with child:
        try:
            stdout, stderr = child.communicate(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
            return Launched(TIMEOUT_EXIT, True, stdout or "", stderr or "")
    return Launched(child.returncode, False, stdout or "", stderr or "")


def launch_many(items: Sequence[Item], parallel: int, worker: Callable[[Item], Outcome]) -> list[Outcome]:
    """items を worker で並行に処理し、items の順に結果を返す。worker は終わったものから結果を書く。"""
    with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
        return list(pool.map(worker, items))
